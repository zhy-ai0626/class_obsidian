#!/usr/bin/env python3
"""全 lecture 扫公式 — Step 1.5 自动化（治 CME222-bug 关键脚本）

逐节 grep `$$ ... $$` 公式块 + 读 tutorial 公式速查表 → 输出大清单。
用 LLM 接着判断哪些进 _principles、哪些归到哪节。

用法:
    python scripts/extract_formulas.py <CODE>

例:
    python scripts/extract_formulas.py CME222

输出: 该课程所有 lecture 公式块 + tutorial 公式速查表（含出处 L## + 行号）
"""
import re
import sys
from pathlib import Path


def find_course_dir(code: str) -> Path:
    """根据课程代码找文件夹。"""
    projects = Path("01_Projects")
    matches = list(projects.glob(f"{code}_*"))
    if not matches:
        sys.exit(f"ERROR: 没找到 01_Projects/{code}_* 文件夹")
    return matches[0]


def extract_formulas(lecture_path: Path) -> list[tuple[int, str]]:
    """从 lecture md 提取所有 $$ ... $$ 公式块。
    返回 (起始行号, 公式 LaTeX) 列表。
    """
    lines = lecture_path.read_text(encoding="utf-8").splitlines()
    formulas = []
    in_block = False
    block_start = 0
    block_content: list[str] = []

    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped == "$$":
            if not in_block:
                in_block = True
                block_start = i
                block_content = []
            else:
                in_block = False
                formula = " ".join(block_content).strip()
                if formula:
                    formulas.append((block_start, formula))
        elif in_block:
            block_content.append(stripped)
        elif stripped.startswith("$$") and stripped.endswith("$$") and len(stripped) > 4:
            # 单行 $$ ... $$ 形式
            formulas.append((i, stripped.strip("$").strip()))

    return formulas


def extract_tutorial_formulas(tutorial_path: Path) -> str:
    """提取 tutorial 的 '## 本次公式速查' 段。"""
    content = tutorial_path.read_text(encoding="utf-8")
    match = re.search(r"## 本次公式速查\n(.*?)(?=\n## |\Z)", content, re.DOTALL)
    return match.group(1).strip() if match else "(无 '本次公式速查' 段)"


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("用法: python extract_formulas.py <CODE> (如 CME222)")

    code = sys.argv[1]
    course_dir = find_course_dir(code)

    print(f"=== {code} 全 lecture 公式清单 ===\n")
    for lecture in sorted(course_dir.glob("L*.md")):
        formulas = extract_formulas(lecture)
        print(f"## {lecture.name}  ({len(formulas)} 个公式块)\n")
        for line_no, latex in formulas:
            preview = latex[:120] + ("..." if len(latex) > 120 else "")
            print(f"  L{line_no}: {preview}")
        print()

    print(f"=== {code} Tutorial 公式速查表汇总 ===\n")
    for tutorial in sorted(course_dir.glob("T*.md")):
        print(f"## {tutorial.name}\n")
        print(extract_tutorial_formulas(tutorial))
        print()


if __name__ == "__main__":
    main()
