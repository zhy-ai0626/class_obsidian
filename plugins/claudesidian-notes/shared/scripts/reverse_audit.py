#!/usr/bin/env python3
"""tutorial → _principles 反向校验 — ingest-tutorial Step 7.6 自动化

扫一个 tutorial 笔记里的 (X.Y) 编号引用 + ⚠️ _principles 缺 标记，
跟同目录 _principles.md 对账，输出 bug 报告。

用法:
    python scripts/reverse_audit.py <path_to_tutorial.md>
    python scripts/reverse_audit.py <path_to_tutorial.md> <path_to_principles.md>

不指定 _principles.md 时自动找同目录的 _principles.md。

退出码: 0 = 全通过, 1 = 有 bug, 2 = _principles.md 不存在
"""
import re
import sys
from pathlib import Path


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit("用法: python reverse_audit.py <tutorial.md> [<_principles.md>]")

    tutorial = Path(sys.argv[1])
    if not tutorial.exists():
        sys.exit(f"ERROR: tutorial 不存在 {tutorial}")

    principles = Path(sys.argv[2]) if len(sys.argv) >= 3 else tutorial.parent / "_principles.md"

    if not principles.exists():
        print(f"⚠️  _principles.md 不存在 ({principles})")
        print("    建议先跑 distill-principles 生成")
        sys.exit(2)

    t_content = tutorial.read_text(encoding="utf-8")
    p_content = principles.read_text(encoding="utf-8")

    # 提取 _principles 所有定义编号
    defined = set(re.findall(r"\\tag\{(\d+\.\d+)\}", p_content))

    # 提取 tutorial 引用的编号
    refs = set(re.findall(r"\((\d+\.\d+)\)", t_content))

    # 提取 ⚠️ _principles 缺 标记
    missing_marks = re.findall(r"⚠️[^\n|]{0,80}_principles[^\n|]{0,40}缺[^\n|]{0,80}", t_content)

    print(f"=== {tutorial.name} → {principles.name} 反向校验 ===\n")
    print(f"Tutorial 引用编号: {sorted(refs) if refs else '(无)'}")
    print(f"_principles 定义编号: {len(defined)} 个\n")

    # 1. 引用断裂检查
    broken = refs - defined
    print("=== (X.Y) 引用对账 ===")
    if broken:
        print(f"  ❌ 引用了但 _principles 没定义: {sorted(broken)}")
    else:
        print("  ✓ 所有 (X.Y) 引用都对得上 _principles 定义")
    print()

    # 2. ⚠️ 标记汇总
    print(f"=== ⚠️ _principles 缺 标记 ({len(missing_marks)} 处）===")
    for mark in missing_marks:
        print(f"  - {mark.strip()}")
    print()

    # 总结
    total_bugs = len(broken) + len(missing_marks)
    if total_bugs:
        print(f"=== 总结: {total_bugs} 处需要修 ===")
        print(f"  → 重新跑 distill-principles 重蒸馏 {principles.parent.name}")
        sys.exit(1)

    print("=== 反向校验通过 ✓ ===")


if __name__ == "__main__":
    main()
