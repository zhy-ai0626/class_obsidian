"""PDF → Markdown 批量转换（MinerU API + 本地双模式，main + SI 配对）。

用法：
    python ${CLAUDE_PLUGIN_ROOT}/shared/scripts/mineru_convert.py                                 # 处理 papers_pdf/ 全部
    python ${CLAUDE_PLUGIN_ROOT}/shared/scripts/mineru_convert.py --paper-id YYYY-author-journal  # 单篇
    python ${CLAUDE_PLUGIN_ROOT}/shared/scripts/mineru_convert.py --pdf path/to/file_main.pdf     # 单文件
    python ${CLAUDE_PLUGIN_ROOT}/shared/scripts/mineru_convert.py --dry-run                       # 只列任务
    python ${CLAUDE_PLUGIN_ROOT}/shared/scripts/mineru_convert.py --force                         # 忽略已存在的 md

特性：
- 自动识别 *_main.pdf 和 *_si.pdf 配对
- main → papers/{paper_id}/main.md  + images/
- SI   → papers/{paper_id}/si.md    + images_si/
- 任务缓存到 cache/mineru/{paper_id}.json：含 batch_id、提交时间、状态
  续跑时直接拉结果，不重复提交，不重复扣配额
- 失败记录到 cache/mineru/{paper_id}_failed.json：含错误信息和 API 响应

环境变量：
    MINERU_MODE: api / local（默认 api）
    MINERU_API_KEY
    MINERU_API_URL  (默认 https://mineru.net/api/v4)

API 流程（基于 v4 文档，2026-04-30 重新核对）：
    POST /file-urls/batch         → batch_id + 预签名 URL
    PUT  presigned_url (raw PDF)  → 触发解析（OSS 直传，无 auth）
    GET  /extract-results/batch/{batch_id}  → 轮询，state in {pending,running,done,failed,
                                              waiting-file, converting}
    下载 result.full_zip_url      → zip 内含 full.md, content_list.json, layout.json,
                                     *_model.json, images/

错误码（来自官方文档）：
    A0202 = 无效 token
    A0211 = token 过期
    -60001 = 生成上传 URL 失败
    -60005 = 文件 > 200MB
    -60006 = 页数 > 600
    -60012 = 任务不存在
    -60018 = 当日 extract 任务额度耗尽

未实现（按用户决策推迟）：
    - 429 限流指数退避（单用户极少触发）
    - papers_pdf/{paper_id}_meta.json 合并到 meta.yaml（写作阶段再做）
"""
from __future__ import annotations
import os
import re
import sys
import io
import json
import time
import shutil
import zipfile
import argparse
import datetime as dt
from pathlib import Path
import requests
from dotenv import load_dotenv
from rich.console import Console
from rich.progress import (
    Progress, SpinnerColumn, TextColumn, TimeElapsedColumn, BarColumn,
)

# 引入 utils
sys.path.insert(0, str(Path(__file__).parent))
import utils  # noqa: F401 — UTF-8 reconfigure
from utils.paper_id import parse_pdf_filename
from utils.si_helpers import init_meta, save_meta, update_meta_status

# 按优先级找 .env：① 运行目录（skill 都是从 vault 根调本脚本）② 脚本旁边
load_dotenv(Path.cwd() / ".env")
load_dotenv(Path(__file__).resolve().parent / ".env")

console = Console()


# ============ 配置常量 ============
DEFAULT_API_URL = "https://mineru.net/api/v4"
DEFAULT_LANGUAGE = "ch"           # ch / en（中英混合用 ch）
DEFAULT_MODEL = "vlm"             # vlm 是最新的视觉模型，质量更好
POLL_INTERVAL_SEC = 10
POLL_MAX_MIN = 30                 # 单 PDF 最多等 30 分钟（SI 多图可能慢；大综述论文可能需要更久）
UPLOAD_TIMEOUT_SEC = 900          # 15 分钟（97MB 大综述 PDF 可能要更久）
DOWNLOAD_TIMEOUT_SEC = 300

# 断点续跑缓存放运行目录（vault 根）下，不放插件目录
CACHE_DIR = Path.cwd() / "cache" / "mineru"
TERMINAL_STATES = {"done", "failed"}

# 解压后只保留这些；其他（MinerU 原始 JSON / 中间 PDF 副本等）删除以省盘
# 防止 152 篇规模下 ~2-3 GB 冗余占用
KEEP_FILES = {"main.md", "si.md", "meta.yaml"}
KEEP_DIRS = {"images", "images_si"}


# ============ 缓存读写 ============
def _cache_path(paper_id: str) -> Path:
    return CACHE_DIR / f"{paper_id}.json"


def _failed_cache_path(paper_id: str) -> Path:
    return CACHE_DIR / f"{paper_id}_failed.json"


def load_cache(paper_id: str) -> dict:
    """读取缓存，没有就返回空骨架。"""
    path = _cache_path(paper_id)
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            console.print(f"[yellow]⚠️ 缓存 {path.name} 损坏，忽略[/]")
    return {"paper_id": paper_id}


def save_cache(paper_id: str, cache: dict) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    _cache_path(paper_id).write_text(
        json.dumps(cache, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def write_failed_cache(
    paper_id: str, doc_type: str, stage: str, error: str, api_response=None
) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "paper_id": paper_id,
        "doc_type": doc_type,
        "stage": stage,
        "error": str(error),
        "api_response": api_response,
        "timestamp": dt.datetime.now().isoformat(timespec="seconds"),
    }
    # 累加：每次失败 append 到 list
    fpath = _failed_cache_path(paper_id)
    history = []
    if fpath.exists():
        try:
            history = json.loads(fpath.read_text(encoding="utf-8"))
            if not isinstance(history, list):
                history = [history]
        except json.JSONDecodeError:
            history = []
    history.append(payload)
    fpath.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")


def _now_iso() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


# ============ MinerU API 调用 ============
def _api_headers(api_key: str) -> dict:
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


def _request_with_retry(method: str, url: str, max_retries: int = 5, **kwargs):
    """requests 调用 + 指数退避重试 DNS/连接错误。

    重试场景: DNS 解析失败 / 连接断开 / 超时 / chunked 编码错。
    退避: 1, 2, 4, 8, 16, 30, 30 秒（封顶 30）。
    PUT 大文件时调用方应该传 bytes 而不是 file object，避免重试时流被消耗。
    """
    last_exc = None
    for attempt in range(max_retries):
        try:
            return requests.request(method, url, **kwargs)
        except (
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
            requests.exceptions.ChunkedEncodingError,
        ) as e:
            last_exc = e
            if attempt == max_retries - 1:
                break
            wait = min(2 ** attempt, 30)
            console.print(
                f"[yellow]⚠️ 网络抖动 ({type(e).__name__})，"
                f"{wait}s 后重试 [{attempt + 1}/{max_retries}][/]"
            )
            time.sleep(wait)
    raise last_exc


def _request_upload_urls(
    api_url: str,
    api_key: str,
    file_names: list[str],
) -> tuple[str, list[str]]:
    """POST /file-urls/batch → (batch_id, [presigned_url, ...])。"""
    payload = {
        "files": [
            {"name": name, "data_id": f"ionogel-{i}", "is_ocr": False}
            for i, name in enumerate(file_names)
        ],
        "enable_formula": True,
        "enable_table": True,
        "language": DEFAULT_LANGUAGE,
        "model_version": DEFAULT_MODEL,
    }
    resp = _request_with_retry(
        "POST",
        f"{api_url}/file-urls/batch",
        json=payload,
        headers=_api_headers(api_key),
        timeout=30,
    )
    resp.raise_for_status()
    body = resp.json()
    if body.get("code") != 0:
        raise RuntimeError(
            f"MinerU /file-urls/batch 返回错误：code={body.get('code')}, "
            f"msg={body.get('msg')}, trace_id={body.get('trace_id')}"
        )
    data = body["data"]
    return data["batch_id"], data["file_urls"]


def _put_pdf_to_oss(pdf_path: Path, presigned_url: str) -> None:
    """PUT 文件到 OSS 预签名 URL（不需要 Authorization 头）。

    传 bytes 而不是 file object —— 这样重试时 _request_with_retry 不需要重新打开文件。
    PDF 一般 < 5 MB，内存够用；MinerU 上限 200 MB 也不至于撑爆。
    """
    data = pdf_path.read_bytes()
    resp = _request_with_retry(
        "PUT", presigned_url, data=data, timeout=UPLOAD_TIMEOUT_SEC
    )
    resp.raise_for_status()


def _fetch_batch_result(api_url: str, api_key: str, batch_id: str) -> dict:
    """单次 GET /extract-results/batch/{batch_id}。返回 body['data']。"""
    endpoint = f"{api_url}/extract-results/batch/{batch_id}"
    headers = {"Authorization": f"Bearer {api_key}"}
    resp = _request_with_retry("GET", endpoint, headers=headers, timeout=30)
    resp.raise_for_status()
    body = resp.json()
    if body.get("code") != 0:
        raise RuntimeError(
            f"MinerU 拉结果失败：code={body.get('code')}, msg={body.get('msg')}"
        )
    return body.get("data", {}) or {}


def _poll_batch_with_progress(
    api_url: str,
    api_key: str,
    batch_id: str,
    file_label: str,
) -> list[dict]:
    """轮询直到 done/failed，用 rich.progress 显示进度。"""
    deadline = time.time() + POLL_MAX_MIN * 60

    columns = [
        SpinnerColumn(),
        TextColumn("[bold cyan]{task.description}[/]"),
        TextColumn("[magenta]{task.fields[state]}[/]"),
        BarColumn(),
        TextColumn("已等"),
        TimeElapsedColumn(),
    ]
    with Progress(*columns, console=console, transient=False) as progress:
        task_id = progress.add_task(file_label, total=1, state="提交中")
        while time.time() < deadline:
            data = _fetch_batch_result(api_url, api_key, batch_id)
            results = data.get("extract_result", []) or []
            if not results:
                progress.update(task_id, state="排队中")
                time.sleep(POLL_INTERVAL_SEC)
                continue
            r = results[0]
            state = r.get("state", "?")
            # 显示带页数进度（如果 API 提供）
            ep = r.get("extract_progress") or {}
            if ep.get("total_pages"):
                state_disp = f"{state} ({ep.get('extracted_pages', '?')}/{ep['total_pages']} 页)"
            else:
                state_disp = state
            progress.update(task_id, state=state_disp)
            if state in TERMINAL_STATES:
                progress.update(task_id, completed=1)
                return results
            time.sleep(POLL_INTERVAL_SEC)

    raise TimeoutError(
        f"MinerU 解析超时（>{POLL_MAX_MIN} 分钟），batch_id={batch_id}"
    )


def _download_zip_bytes(url: str) -> bytes:
    """下载 zip 到内存。"""
    resp = _request_with_retry(
        "GET", url, timeout=DOWNLOAD_TIMEOUT_SEC, stream=True
    )
    resp.raise_for_status()
    return resp.content


def _cleanup_paper_dir(paper_dir: Path, keep_raw: bool = False) -> list[Path]:
    """只删 MinerU 已知临时产物（blacklist 模式）。
    不在 blacklist 的文件/目录一律保留——避免误删用户文件、vision 中间产物等。

    Blacklist 文件名 pattern:
      - <doc_type>_layout.json / *_layout.json
      - <doc_type>_model.json / *_model.json
      - <doc_type>_origin.pdf / *_origin.pdf
      - <doc_type>_content_list*.json
      - <doc_type>_spans.json
      - full.md（_extract_zip 重命名前的临时文件）
    """
    if keep_raw:
        return []
    blacklist_suffixes = ["_layout.json", "_model.json", "_origin.pdf", "_spans.json"]
    blacklist_contains = ["_content_list"]
    blacklist_exact = {"full.md"}
    deleted: list[Path] = []
    for item in paper_dir.iterdir():
        if not item.is_file():
            continue
        name = item.name
        is_temp = (
            name in blacklist_exact
            or any(name.endswith(suf) for suf in blacklist_suffixes)
            or any(kw in name for kw in blacklist_contains)
        )
        if is_temp:
            deleted.append(item)
            try:
                item.unlink()
            except OSError:
                pass
    return deleted


def _extract_zip_to_paper_dir(
    zip_bytes: bytes,
    output_dir: Path,
    doc_type: str,
) -> Path:
    """解压 MinerU 返回的 zip 到 papers/{paper_id}/。

    main → main.md + images/
    si   → si.md   + images_si/
    其他文件按 doc_type 加前缀保留（main_content_list.json 等）

    Returns:
        生成的主 Markdown 路径
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    md_target_name = "main.md" if doc_type == "main" else "si.md"
    images_dir_name = "images" if doc_type == "main" else "images_si"
    md_target = output_dir / md_target_name

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        names = zf.namelist()
        # 剥可能的多余顶层目录
        common_prefix = ""
        first_parts = {n.split("/", 1)[0] for n in names if n}
        if len(first_parts) == 1:
            only = next(iter(first_parts))
            if only and only != "images":
                if any(n.startswith(only + "/") for n in names):
                    common_prefix = only + "/"

        for info in zf.infolist():
            if info.is_dir():
                continue
            relpath = info.filename
            if common_prefix and relpath.startswith(common_prefix):
                relpath = relpath[len(common_prefix):]
            if not relpath:
                continue

            if relpath == "full.md":
                target = md_target
            elif relpath.startswith("images/"):
                target = output_dir / images_dir_name / relpath[len("images/"):]
            elif relpath.endswith(".json"):
                target = output_dir / f"{doc_type}_{Path(relpath).name}"
            else:
                target = output_dir / f"{doc_type}_{Path(relpath).name}"

            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as src, target.open("wb") as dst:
                shutil.copyfileobj(src, dst)

    if not md_target.exists():
        raise FileNotFoundError(
            f"zip 中未找到 full.md，无法生成 {md_target_name}。"
            f" zip 内容：{names[:10]}{'...' if len(names) > 10 else ''}"
        )

    # MinerU 输出的 markdown 硬编码 images/HASH.jpg，但 SI 图被搬到 images_si/
    # 同步修正 si.md 里的引用路径
    if doc_type == "si":
        content = md_target.read_text(encoding="utf-8")
        new_content = content.replace("](images/", "](images_si/")
        if new_content != content:
            replaced = content.count("](images/")
            md_target.write_text(new_content, encoding="utf-8")
            console.print(f"[dim]   修正 si.md 中 {replaced} 处图片引用路径[/]")

    return md_target


# ============ 单 PDF 转换主入口（带缓存续跑）============
def convert_via_api(
    pdf_path: Path,
    output_dir: Path,
    doc_type: str,
    paper_id: str,
    *,
    force: bool = False,
    keep_raw: bool = False,
) -> Path:
    """使用 MinerU 云 API 转换单个 PDF，带缓存续跑能力。

    缓存逻辑：
        - 如果 cache 中已有 batch_id 且 state=done → 直接拉结果下载
        - 如果 cache 中已有 batch_id 但未 done → 直接续轮询，不重复提交
        - 否则全新提交流程
    """
    # 两个环境变量名都认：MINERU_API_TOKEN 优先，其次 MINERU_API_KEY
    api_key = (os.getenv("MINERU_API_TOKEN", "").strip()
               or os.getenv("MINERU_API_KEY", "").strip())
    if not api_key or api_key == "your_token_here":
        raise RuntimeError("MINERU_API_TOKEN / MINERU_API_KEY 未配置")
    api_url = os.getenv("MINERU_API_URL", DEFAULT_API_URL).rstrip("/")

    cache = load_cache(paper_id)
    section = cache.get(doc_type) or {}
    batch_id = section.get("batch_id")

    md_target_name = "main.md" if doc_type == "main" else "si.md"
    md_target = output_dir / md_target_name
    if md_target.exists() and not force:
        # 已存在，跳过（即使 cache 没记录）
        console.print(f"[dim]→ {md_target.name} 已存在，跳过（--force 强制重跑）[/]")
        section.setdefault("state", "done")
        section.setdefault("completed_at", _now_iso())
        cache[doc_type] = section
        save_cache(paper_id, cache)
        return md_target

    # === 续跑路径 ===
    if batch_id:
        console.print(f"[dim]→ {doc_type}: 缓存有 batch_id={batch_id[:8]}…，尝试续跑[/]")
        try:
            data = _fetch_batch_result(api_url, api_key, batch_id)
            results = data.get("extract_result", []) or []
            if results:
                r = results[0]
                state = r.get("state")
                if state == "done":
                    zip_url = r.get("full_zip_url")
                    if zip_url:
                        zip_bytes = _download_zip_bytes(zip_url)
                        md_path = _extract_zip_to_paper_dir(zip_bytes, output_dir, doc_type)
                        deleted = _cleanup_paper_dir(output_dir, keep_raw=keep_raw)
                        if deleted:
                            console.print(f"[dim]   清理 {len(deleted)} 个 MinerU 原始产物[/]")
                        section.update({
                            "state": "done",
                            "zip_url": zip_url,
                            "completed_at": r.get("extract_progress", {}).get("end_time") or _now_iso(),
                            "extracted_at": _now_iso(),
                        })
                        cache[doc_type] = section
                        save_cache(paper_id, cache)
                        return md_path
                elif state == "failed":
                    err = r.get("err_msg") or "(无错误信息)"
                    section.update({"state": "failed", "err_msg": err})
                    cache[doc_type] = section
                    save_cache(paper_id, cache)
                    raise RuntimeError(f"缓存 batch 已 failed：{err}")
                else:
                    # 检测 stale batch: waiting-file 超过 10 分钟说明 PDF 没传上去
                    # （上次 DNS 断时上传失败，但 mineru 端 batch 已创建，状态卡在 waiting-file）
                    # 这种情况不要傻等 15 分钟 POLL_MAX_MIN，直接重新提交
                    if state == "waiting-file":
                        submitted_at_str = section.get("submitted_at", "")
                        try:
                            submitted_at = dt.datetime.fromisoformat(submitted_at_str)
                            age_min = (dt.datetime.now() - submitted_at).total_seconds() / 60
                            if age_min > 10:
                                raise RuntimeError(
                                    f"batch waiting-file 已 {age_min:.0f} 分钟，PDF 上传失败，重新提交"
                                )
                        except (ValueError, TypeError):
                            pass  # 时间解析失败，落到下面续轮询
                    # 还在跑（或刚提交不久），继续轮询
                    console.print(f"[dim]   batch 仍在 {state}，续轮询中...[/]")
                    return _resume_polling_and_extract(
                        api_url, api_key, batch_id, paper_id, doc_type,
                        output_dir, pdf_path, cache, section, keep_raw=keep_raw,
                    )
        except (RuntimeError, requests.HTTPError) as e:
            # batch 可能已过期或被清理（尤其超过 24 小时），降级到全新提交
            console.print(f"[yellow]   续跑失败（{e}），改为全新提交[/]")

    # === 全新提交路径 ===
    file_name = pdf_path.name
    batch_id, file_urls = _request_upload_urls(api_url, api_key, [file_name])
    if len(file_urls) != 1:
        raise RuntimeError(f"预期 1 个上传 URL，实际 {len(file_urls)} 个")

    section = {
        "batch_id": batch_id,
        "submitted_at": _now_iso(),
        "state": "submitted",
        "pdf_path": str(pdf_path),
        "file_name": file_name,
    }
    cache[doc_type] = section
    save_cache(paper_id, cache)

    _put_pdf_to_oss(pdf_path, file_urls[0])
    section["state"] = "uploaded"
    save_cache(paper_id, cache)

    return _resume_polling_and_extract(
        api_url, api_key, batch_id, paper_id, doc_type,
        output_dir, pdf_path, cache, section, keep_raw=keep_raw,
    )


def _resume_polling_and_extract(
    api_url, api_key, batch_id, paper_id, doc_type,
    output_dir, pdf_path, cache, section, *, keep_raw: bool = False,
) -> Path:
    """轮询 + 下载 + 解压（已有 batch_id 之后的统一流程）。"""
    label = f"{paper_id} ({doc_type}) — {pdf_path.name[:40]}"
    results = _poll_batch_with_progress(api_url, api_key, batch_id, label)
    if not results:
        raise RuntimeError("MinerU 没返回任何 extract_result")
    r = results[0]
    state = r.get("state")
    if state != "done":
        err = r.get("err_msg") or r.get("msg") or "(无错误信息)"
        section.update({"state": state, "err_msg": err})
        cache[doc_type] = section
        save_cache(paper_id, cache)
        raise RuntimeError(f"MinerU 解析失败：state={state}, err={err}")
    zip_url = r.get("full_zip_url")
    if not zip_url:
        raise RuntimeError(f"MinerU 返回 done 但无 full_zip_url：{r}")
    zip_bytes = _download_zip_bytes(zip_url)
    md_path = _extract_zip_to_paper_dir(zip_bytes, output_dir, doc_type)
    deleted = _cleanup_paper_dir(output_dir, keep_raw=keep_raw)
    if deleted:
        console.print(f"[dim]   清理 {len(deleted)} 个 MinerU 原始产物[/]")
    section.update({
        "state": "done",
        "zip_url": zip_url,
        "completed_at": (r.get("extract_progress") or {}).get("end_time") or _now_iso(),
        "extracted_at": _now_iso(),
    })
    cache[doc_type] = section
    save_cache(paper_id, cache)
    return md_path


def convert_via_local(
    pdf_path: Path, output_dir: Path, doc_type: str, paper_id: str,
    *, force=False, keep_raw: bool = False,
) -> Path:
    raise NotImplementedError("本地 MinerU 调用待实现。")


# ============ CLI ============
def _collect_pdfs(args) -> list[Path]:
    """根据 CLI 参数收集要处理的 PDF 列表。"""
    if args.pdf:
        p = Path(args.pdf)
        if not p.exists():
            raise FileNotFoundError(f"--pdf 指定的文件不存在：{p}")
        return [p]
    input_path = Path(args.input)
    if input_path.is_file():
        return [input_path]
    if not input_path.exists():
        return []
    return list(input_path.glob("*.pdf"))


def _group_by_paper(pdfs: list[Path], paper_id_filter: str | None):
    """{paper_id: {'main': Path, 'si': Path}}。"""
    grouped: dict[str, dict[str, Path]] = {}
    for pdf in pdfs:
        try:
            pid, dtype = parse_pdf_filename(pdf.name)
        except ValueError as e:
            console.print(f"[yellow]⚠️ 跳过：{e}[/]")
            continue
        if paper_id_filter and pid != paper_id_filter:
            continue
        grouped.setdefault(pid, {})[dtype] = pdf
    return grouped


def _print_dry_run_plan(grouped, output_root, force):
    """dry-run 模式下打印将要处理的内容。"""
    console.print("\n[bold cyan]── DRY RUN：以下任务会被处理 ──[/]")
    if not grouped:
        console.print("[yellow]⚠️ 没有匹配的 PDF[/]")
        return
    total_tasks = 0
    skipped = 0
    for paper_id, files in grouped.items():
        paper_dir = output_root / paper_id
        console.print(f"\n📄 [bold]{paper_id}[/]")
        for doc_type in ("main", "si"):
            if doc_type not in files:
                console.print(f"   ├─ {doc_type:4}: [dim](无 PDF)[/]")
                continue
            pdf = files[doc_type]
            md_target = paper_dir / ("main.md" if doc_type == "main" else "si.md")
            size_mb = pdf.stat().st_size / 1024 / 1024
            if md_target.exists() and not force:
                console.print(
                    f"   ├─ {doc_type:4}: {pdf.name} ({size_mb:.1f} MB) "
                    f"[yellow]→ {md_target.name} 已存在，会跳过[/]"
                )
                skipped += 1
            else:
                console.print(
                    f"   ├─ {doc_type:4}: {pdf.name} ({size_mb:.1f} MB) "
                    f"[green]→ 会调用 MinerU API[/]"
                )
                total_tasks += 1
        # cache 状态
        cache = load_cache(paper_id)
        for doc_type in ("main", "si"):
            sec = cache.get(doc_type) or {}
            if sec.get("batch_id"):
                console.print(
                    f"   │  cache.{doc_type}: batch_id={sec['batch_id'][:8]}… "
                    f"state={sec.get('state', '?')} "
                    f"(可续跑，不重新扣配额)"
                )

    console.print(f"\n[bold]合计[/]：{total_tasks} 个 API 任务，{skipped} 个跳过")


def _run_paper_dir_mode(paper_dir: Path, convert_fn, args):
    """claudesidian 模式：输入 (YYYY) Title 文件夹，自动跑里面的 main.pdf / si.pdf。
    输出 main.md + si.md + images/ + images_si/ 到同文件夹。
    """
    if not paper_dir.is_dir():
        console.print(f"[red]❌ 文件夹不存在或不是目录: {paper_dir}[/]")
        sys.exit(1)

    main_pdf = paper_dir / "main.pdf"
    si_pdf = paper_dir / "si.pdf"
    has_main, has_si = main_pdf.exists(), si_pdf.exists()
    if not (has_main or has_si):
        console.print(f"[red]❌ {paper_dir.name} 里既没 main.pdf 也没 si.pdf[/]")
        sys.exit(1)

    folder_name = paper_dir.name
    # paper_id 用 sanitize 后的文件夹名（cache 文件名安全）
    paper_id = re.sub(r"[^\w\-]", "_", folder_name)[:80]

    console.print(f"\n[bold cyan]▶ {folder_name}[/]  (main={'✓' if has_main else '✗'}, "
                  f"si={'✓' if has_si else '✗'})")

    if not (paper_dir / "meta.yaml").exists():
        save_meta(paper_dir, init_meta(paper_dir, paper_id, has_main, has_si))

    if args.dry_run:
        for dt_label, pdf in [("main", main_pdf), ("si", si_pdf)]:
            if not pdf.exists(): continue
            target_md = paper_dir / f"{dt_label}.md"
            if target_md.exists() and not args.force:
                console.print(f"   {dt_label}: {pdf.name} → {target_md.name} [yellow]已存在，会跳过[/]")
            else:
                console.print(f"   {dt_label}: {pdf.name} [green]→ 会调 MinerU API[/]")
        return

    any_done = False
    for doc_type, pdf in [("main", main_pdf), ("si", si_pdf)]:
        if not pdf.exists(): continue
        t0 = time.time()
        try:
            convert_fn(pdf, paper_dir, doc_type, paper_id,
                       force=args.force, keep_raw=args.keep_mineru_raw)
            console.print(f"   [green]✅ {doc_type}：完成（{time.time()-t0:.1f}s）[/]")
            any_done = True
        except NotImplementedError as e:
            console.print(f"   [yellow]⏸  {doc_type}：转换器未实现（{e}）[/]")
        except Exception as e:
            console.print(f"   [red]❌ {doc_type}：失败（{time.time()-t0:.1f}s）— {e}[/]")
            write_failed_cache(paper_id, doc_type, "convert", str(e))

    # === 非 pdf SI（si.docx / si.xlsx / si.zip 等）自动 fallback 到 process_si.py ===
    non_pdf_si = [
        f for f in paper_dir.iterdir()
        if f.is_file() and f.stem == "si" and f.suffix.lower() not in (".pdf", ".md")
    ]
    si_md_exists = (paper_dir / "si.md").exists()
    if non_pdf_si and (not si_md_exists or args.force):
        console.print(f"[cyan]→ 检测到非 pdf SI（{non_pdf_si[0].name}），调用 process_si.py[/]")
        import subprocess
        cmd = [sys.executable, str(Path(__file__).parent / "process_si.py"), str(paper_dir)]
        if args.force:
            cmd.append("--force")
        result = subprocess.run(cmd)
        if result.returncode == 0:
            any_done = True
        else:
            console.print(f"[red]❌ process_si.py 失败（exit {result.returncode}）[/]")

    if any_done:
        update_meta_status(paper_dir, mineru_done=True)
        console.print(f"\n[bold green]完成[/]: {folder_name}")
    console.print(f"缓存目录：{CACHE_DIR}")


def main():
    parser = argparse.ArgumentParser(
        description=__doc__.split("\n")[0],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("input", nargs="?", default="papers_pdf/", help="PDF 目录或单文件（默认 papers_pdf/）")
    parser.add_argument("-o", "--output", default="papers/", help="输出目录（默认 papers/）")
    parser.add_argument("--paper-id", help="仅处理指定 paper_id 的 PDF")
    parser.add_argument("--pdf", help="单个 PDF 文件路径（绝对/相对）")
    parser.add_argument("--paper-dir", help="claudesidian 模式：指定 (YYYY) Title 文件夹，"
                                            "里面 main.pdf / si.pdf 自动检测，输出到同文件夹")
    parser.add_argument("--dry-run", action="store_true", help="只列出会处理的 PDF，不调 API")
    parser.add_argument("--force", action="store_true", help="忽略已有 main.md/si.md，强制重跑")
    parser.add_argument(
        "--keep-mineru-raw",
        action="store_true",
        help="保留 MinerU 原始产物（_layout.json / _model.json / _origin.pdf 等）。默认清理以省盘。",
    )
    parser.add_argument(
        "--mode",
        choices=["api", "local"],
        default=os.getenv("MINERU_MODE", "api"),
    )
    args = parser.parse_args()

    convert_fn = convert_via_api if args.mode == "api" else convert_via_local

    # === claudesidian 模式：--paper-dir 直接处理一个 (YYYY) Title 文件夹 ===
    if args.paper_dir:
        _run_paper_dir_mode(Path(args.paper_dir).resolve(), convert_fn, args)
        return

    output_root = Path(args.output)
    output_root.mkdir(parents=True, exist_ok=True)

    try:
        pdfs = _collect_pdfs(args)
    except FileNotFoundError as e:
        console.print(f"[red]❌ {e}[/]")
        sys.exit(1)

    grouped = _group_by_paper(pdfs, args.paper_id)
    if not grouped:
        console.print("[yellow]⚠️ 未找到符合命名规范的 PDF。请检查 papers_pdf/README.md。[/]")
        return

    if args.dry_run:
        _print_dry_run_plan(grouped, output_root, args.force)
        return

    # 真实执行
    success_count = 0
    fail_count = 0
    for paper_id, files in grouped.items():
        paper_dir = output_root / paper_id
        paper_dir.mkdir(exist_ok=True)

        has_main = "main" in files
        has_si = "si" in files

        # 初始化 meta（即使转换失败也能记录状态）
        if not (paper_dir / "meta.yaml").exists():
            meta = init_meta(paper_dir, paper_id, has_main, has_si)
            save_meta(paper_dir, meta)

        console.print(f"\n[bold cyan]▶ {paper_id}[/]  (main={'✓' if has_main else '✗'}, "
                      f"si={'✓' if has_si else '✗'})")

        any_done = False
        for doc_type in ("main", "si"):
            if doc_type not in files:
                continue
            pdf = files[doc_type]
            t0 = time.time()
            try:
                convert_fn(
                    pdf, paper_dir, doc_type, paper_id,
                    force=args.force, keep_raw=args.keep_mineru_raw,
                )
                elapsed = time.time() - t0
                console.print(f"   [green]✅ {doc_type}：完成（{elapsed:.1f}s）[/]")
                any_done = True
            except NotImplementedError as e:
                console.print(f"   [yellow]⏸  {doc_type}：转换器未实现（{e}）[/]")
                fail_count += 1
            except Exception as e:
                elapsed = time.time() - t0
                console.print(f"   [red]❌ {doc_type}：失败（{elapsed:.1f}s）— {e}[/]")
                write_failed_cache(paper_id, doc_type, "convert", str(e))
                fail_count += 1

        if any_done:
            update_meta_status(paper_dir, mineru_done=True)
            success_count += 1

    console.print(f"\n[bold]汇总[/]：成功 {success_count} 篇，失败/跳过 {fail_count} 个任务")
    console.print(f"缓存目录：{CACHE_DIR}")


if __name__ == "__main__":
    main()
