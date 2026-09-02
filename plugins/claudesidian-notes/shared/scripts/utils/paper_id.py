"""统一的 paper_id 生成函数。"""
import re
import yaml
import argparse
from pathlib import Path
from functools import lru_cache


@lru_cache(maxsize=1)
def _load_journal_abbrev() -> dict:
    """加载期刊缩写映射表（带缓存，只读一次）。

    返回 dict，key 已规范化为小写、单空格分隔。
    """
    abbrev_path = Path(__file__).parent / "journal_abbrev.yaml"
    if not abbrev_path.exists():
        return {}
    with abbrev_path.open(encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    return {
        re.sub(r'\s+', ' ', k.strip().lower()): v
        for k, v in raw.items()
    }


def _abbreviate_journal(journal: str) -> str:
    """期刊缩写：三层 fallback。

    1. 精确匹配 journal_abbrev.yaml 映射表
    2. 模糊匹配（去常见后缀如 "letters"）
    3. 启发式：取每个实词首字母（跳过 the/of/and/&）
    4. 兜底：前 6 个字母
    """
    if not journal:
        return "jr"

    abbrev_table = _load_journal_abbrev()
    normalized = re.sub(r'\s+', ' ', str(journal).strip().lower())

    # 1. 精确匹配
    if normalized in abbrev_table:
        return abbrev_table[normalized]

    # 2. 模糊匹配（去掉常见后缀）
    for suffix in [" letters", " journal", " international edition"]:
        if normalized.endswith(suffix):
            stripped = normalized[:-len(suffix)]
            if stripped in abbrev_table:
                return abbrev_table[stripped]

    # 3. 启发式：取每个实词首字母
    stopwords = {"the", "of", "and", "&", "for", "in", "on", "a", "an"}
    words = re.findall(r'[A-Za-z]+', journal)
    initials = [w[0].lower() for w in words if w.lower() not in stopwords]
    if 2 <= len(initials) <= 8:
        return ''.join(initials)

    # 4. 兜底：前 6 字母
    cleaned = re.sub(r'[^a-zA-Z]', '', journal).lower()
    return cleaned[:6] if cleaned else "jr"


def generate_paper_id(year, first_author, journal) -> str:
    """生成 paper_id，格式：YYYY-firstauthor-journal_short。

    示例：
        generate_paper_id(2024, "Zhang Wei", "Nature Communications")
            → "2024-zhang-natcom"
        generate_paper_id(2025, "Smith", "ACS Applied Materials & Interfaces")
            → "2025-smith-acsami"
    """
    year_str = str(int(year)) if year else "unknown"
    auth_raw = str(first_author).split(',')[0].split()[0] if first_author else "na"
    auth = re.sub(r'[^a-zA-Z]', '', auth_raw).lower()[:15]
    journ = _abbreviate_journal(journal)
    return f"{year_str}-{auth}-{journ}"


def parse_pdf_filename(filename: str) -> tuple[str, str]:
    """解析 PDF 文件名，返回 (paper_id, doc_type)。

    例：'2024-zhang-natcom_main.pdf' → ('2024-zhang-natcom', 'main')
    """
    stem = filename.replace(".pdf", "")
    if stem.endswith("_main"):
        return stem[:-5], "main"
    elif stem.endswith("_si"):
        return stem[:-3], "si"
    else:
        raise ValueError(f"PDF 文件名不规范：{filename}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int)
    parser.add_argument("--author")
    parser.add_argument("--journal")
    args = parser.parse_args()

    if args.year and args.author and args.journal:
        print(generate_paper_id(args.year, args.author, args.journal))
    else:
        # 自测
        tests = [
            (2025, "Smith", "ACS Applied Materials & Interfaces", "2025-smith-acsami"),
            (2024, "Zhang", "Nature Communications", "2024-zhang-natcom"),
            (2023, "Liu", "Advanced Materials", "2023-liu-advmat"),
            (2024, "Wang", "Some Unknown Journal That Is Long", None),  # 启发式
        ]
        for year, auth, journ, expected in tests:
            result = generate_paper_id(year, auth, journ)
            status = "✓" if (expected is None or result == expected) else "✗"
            print(f"  {status} ({year}, {auth!r}, {journ!r}) → {result}"
                  + (f" [期望 {expected}]" if expected and result != expected else ""))
