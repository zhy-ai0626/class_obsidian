"""SI 处理辅助函数。

提供读写 papers/{paper_id}/meta.yaml 的统一入口，
以及判断论文 SI 状态的快捷函数。
"""
from __future__ import annotations
from pathlib import Path
import yaml


def load_meta(paper_dir: Path) -> dict:
    """加载 papers/{paper_id}/meta.yaml。返回空 dict 表示文件不存在。"""
    meta_path = paper_dir / "meta.yaml"
    if not meta_path.exists():
        return {}
    return yaml.safe_load(meta_path.read_text(encoding="utf-8")) or {}


def save_meta(paper_dir: Path, meta: dict) -> None:
    """写回 meta.yaml（保留 unicode 字符）。"""
    meta_path = paper_dir / "meta.yaml"
    meta_path.write_text(
        yaml.dump(meta, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def has_si(paper_dir: Path) -> bool:
    """判断该论文是否已获取 SI。"""
    meta = load_meta(paper_dir)
    return bool(meta.get("si_status", {}).get("si_obtained", False))


def get_si_md_path(paper_dir: Path) -> Path | None:
    """返回 SI Markdown 路径，无则 None。"""
    si_path = paper_dir / "si.md"
    return si_path if si_path.exists() else None


def get_main_md_path(paper_dir: Path) -> Path | None:
    """返回正文 Markdown 路径，无则 None。"""
    main_path = paper_dir / "main.md"
    return main_path if main_path.exists() else None


def update_meta_status(paper_dir: Path, **kwargs) -> None:
    """更新 meta.yaml 中的 processing_status 字段。

    例：update_meta_status(p, mineru_done=True, obsidian_done=True)
    """
    meta = load_meta(paper_dir)
    meta.setdefault("processing_status", {}).update(kwargs)
    save_meta(paper_dir, meta)


def init_meta(
    paper_dir: Path,
    paper_id: str,
    has_main_pdf: bool,
    has_si_pdf: bool,
) -> dict:
    """初始化 meta.yaml 内容（不写盘，由调用者决定是否覆盖）。"""
    return {
        "paper_id": paper_id,
        "files": {
            "main_pdf": f"{paper_id}_main.pdf" if has_main_pdf else None,
            "main_md": "main.md" if has_main_pdf else None,
            "si_pdf": f"{paper_id}_si.pdf" if has_si_pdf else None,
            "si_md": "si.md" if has_si_pdf else None,
            "data_files": [],
        },
        "si_status": {
            "has_si": has_si_pdf,
            "si_obtained": has_si_pdf,
            "obtained_from": "publisher" if has_si_pdf else None,
            "obtained_date": None,
        },
        "processing_status": {
            "mineru_done": False,
            "obsidian_done": False,
            "extracted_main": False,
            "extracted_si": False,
            "validated": False,
        },
    }
