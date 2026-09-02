#!/usr/bin/env python3
"""
mineru_extract.py — MinerU API 调用封装

用 OpenXLab MinerU API(https://mineru.net) 把 PDF 转成 markdown + images。
Token 从运行目录（vault 根）的 .env 读取(MINERU_API_TOKEN=...)。

用法:
    py ${CLAUDE_PLUGIN_ROOT}/shared/scripts/mineru_extract.py <pdf_path> <output_dir> [--model vlm|pipeline]

输出:
    <output_dir>/<pdf_stem>/full.md       # 主 markdown(图片用相对路径)
    <output_dir>/<pdf_stem>/images/*.jpg  # MinerU 抽出的图片
    <output_dir>/<pdf_stem>/layout.json   # 页面布局(可选,调试用)
"""

import argparse
import os
import sys
import time
import zipfile
from pathlib import Path

import requests

# ---- 常量 ----
API_BASE = "https://mineru.net/api/v4"
POLL_INTERVAL = 5         # 轮询间隔(秒)
POLL_TIMEOUT = 30 * 60    # 30 分钟超时
MAX_FILE_MB = 200         # MinerU 单文件大小限制


def load_env_token() -> str:
    """从 vault 根 .env 读 MINERU_API_TOKEN。
    .env 格式:MINERU_API_TOKEN=eyJ0eXBlIjoiSldUIiwi...
    简单解析,不依赖 python-dotenv 包。
    """
    # 按优先级找 .env：① 运行目录（skill 都是从 vault 根调本脚本）② 脚本旁边
    candidates = [Path.cwd() / ".env", Path(__file__).resolve().parent / ".env"]
    for env_path in candidates:
        if not env_path.exists():
            continue
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            if key.strip() == "MINERU_API_TOKEN":
                # 去掉可能的引号
                return value.strip().strip('"').strip("'")
    # 兜底:从环境变量
    token = os.environ.get("MINERU_API_TOKEN")
    if not token:
        raise RuntimeError(
            ".env 没有 MINERU_API_TOKEN,环境变量也没设。\n"
            "请在 vault 根目录创建 .env 文件,加一行:\n"
            "  MINERU_API_TOKEN=<your-jwt-from-mineru.net/apiManage/token>"
        )
    return token


def mineru_extract(
    pdf_path: str,
    output_dir: str,
    token: str | None = None,
    model_version: str = "vlm",
    language: str = "ch",
) -> tuple[Path, Path]:
    """
    上传本地 PDF 到 MinerU API,等待解析,下载并解压结果。

    参数:
        pdf_path: 本地 PDF 文件路径
        output_dir: 输出根目录(会在下面建 <pdf_stem>/ 子目录)
        token: API token(默认从 .env 读)
        model_version: "vlm"(准确,慢,推荐) 或 "pipeline"(快)
        language: "ch" / "en" / "auto"

    返回:
        (markdown 文件路径, images 目录路径)
    """
    if token is None:
        token = load_env_token()

    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF 文件不存在: {pdf_path}")

    size_mb = pdf_path.stat().st_size / 1e6
    if size_mb > MAX_FILE_MB:
        raise ValueError(
            f"PDF 大小 {size_mb:.1f}MB,超过 MinerU 单文件 {MAX_FILE_MB}MB 限制。"
            f"可以用 pypdf 拆分大 PDF 后分别处理。"
        )

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    # ---- step 1: 申请 OSS 上传 URL ----
    print(f"[1/4] 申请 OSS 上传 URL...")
    resp = requests.post(
        f"{API_BASE}/file-urls/batch",
        json={
            "files": [{"name": pdf_path.name, "data_id": pdf_path.stem}],
            "model_version": model_version,
            "language": language,
            "enable_formula": True,
            "enable_table": True,
        },
        headers=headers,
        timeout=30,
    )
    resp.raise_for_status()
    payload = resp.json()
    if payload.get("code") != 0:
        raise RuntimeError(f"申请上传 URL 失败: {payload}")
    batch_id = payload["data"]["batch_id"]
    upload_url = payload["data"]["file_urls"][0]
    print(f"    batch_id = {batch_id}")

    # ---- step 2: PUT 文件到 OSS(关键:不能带 Authorization header)----
    print(f"[2/4] 上传 PDF ({size_mb:.1f} MB)...")
    with pdf_path.open("rb") as f:
        put_resp = requests.put(upload_url, data=f, timeout=300)
    put_resp.raise_for_status()
    print(f"    上传完成")

    # ---- step 3: 轮询任务状态 ----
    print(f"[3/4] 轮询解析进度(最长 {POLL_TIMEOUT // 60} 分钟)...")
    zip_url = None
    deadline = time.time() + POLL_TIMEOUT
    while time.time() < deadline:
        time.sleep(POLL_INTERVAL)
        r = requests.get(
            f"{API_BASE}/extract-results/batch/{batch_id}",
            headers=headers,
            timeout=30,
        )
        r.raise_for_status()
        data = r.json().get("data", {})
        results = data.get("extract_result", [])
        if not results:
            continue
        result = results[0]
        state = result.get("state")
        if state == "done":
            zip_url = result["full_zip_url"]
            print(f"    任务完成")
            break
        if state == "failed":
            raise RuntimeError(f"解析失败: {result.get('err_msg', '(无错误信息)')}")
        progress = result.get("extract_progress") or {}
        ep = progress.get("extracted_pages", "?")
        tp = progress.get("total_pages", "?")
        print(f"    [{state}] {ep}/{tp} 页")
    else:
        raise TimeoutError(f"超过 {POLL_TIMEOUT}s 任务仍未完成")

    # ---- step 4: 下载并解压 zip ----
    print(f"[4/4] 下载并解压结果...")
    # 用 pdf_stem 做后缀避免并行跑同目录多个 PDF 时 zip 互相覆盖
    zip_path = output_dir / f"_tmp_result_{pdf_path.stem}.zip"
    with requests.get(zip_url, stream=True, timeout=300) as r:
        r.raise_for_status()
        with zip_path.open("wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    extract_dir = output_dir / pdf_path.stem
    extract_dir.mkdir(exist_ok=True)
    with zipfile.ZipFile(zip_path) as z:
        z.extractall(extract_dir)
    zip_path.unlink()  # 清理临时 zip
    print(f"    解压到: {extract_dir}")

    # 找 markdown 文件
    md_path = extract_dir / "full.md"
    if not md_path.exists():
        # 兜底:找任何 .md 文件
        candidates = list(extract_dir.glob("*.md"))
        if candidates:
            md_path = candidates[0]
        else:
            raise RuntimeError(f"zip 解压后没找到 .md 文件: {extract_dir}")
    images_dir = extract_dir / "images"

    return md_path, images_dir


def main():
    parser = argparse.ArgumentParser(
        description="MinerU API: PDF -> markdown + images",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("pdf_path", help="本地 PDF 文件路径")
    parser.add_argument("output_dir", help="输出根目录(会建 <pdf_stem>/ 子目录)")
    parser.add_argument(
        "--model",
        choices=["vlm", "pipeline"],
        default="vlm",
        help="vlm=准确慢(默认,推荐化工 PDF) / pipeline=快",
    )
    parser.add_argument(
        "--lang",
        choices=["ch", "en", "auto"],
        default="ch",
        help="主要语言提示(默认 ch)",
    )
    args = parser.parse_args()

    try:
        md_path, images_dir = mineru_extract(
            pdf_path=args.pdf_path,
            output_dir=args.output_dir,
            model_version=args.model,
            language=args.lang,
        )
        n_images = len(list(images_dir.glob("*"))) if images_dir.exists() else 0
        print(f"\n=== 完成 ===")
        print(f"Markdown: {md_path}")
        print(f"Images:   {images_dir} ({n_images} 张)")
    except Exception as e:
        print(f"\n[ERROR] {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
