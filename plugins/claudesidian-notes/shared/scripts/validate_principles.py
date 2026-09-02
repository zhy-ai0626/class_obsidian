#!/usr/bin/env python3
"""_principles.md 自检 — Step 6 自动化

检查:
1. 公式编号 \\tag{X.Y} 连续无跳号
2. 跨节引用 (X.Y) 都对应已定义的公式
3. 文件长度 200-400 行
4. 没有 callout（教科书风格禁用）

用法:
    python scripts/validate_principles.py <path_to_principles.md>

例:
    python scripts/validate_principles.py 01_Projects/CME222_传质/_principles.md

退出码: 0 = 全通过, 1 = 有问题
"""
import re
import sys
from pathlib import Path


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("用法: python validate_principles.py <path_to_principles.md>")

    path = Path(sys.argv[1])
    if not path.exists():
        sys.exit(f"ERROR: 文件不存在 {path}")

    content = path.read_text(encoding="utf-8")
    errors: list[str] = []

    # 1. 提取所有 \tag{X.Y}
    tags = re.findall(r"\\tag\{(\d+\.\d+)\}", content)
    print(f"=== {path.name} ===\n")
    print(f"公式编号总数: {len(tags)}")
    if tags:
        print(f"编号范围: ({tags[0]}) → ({tags[-1]})\n")

    # 2. 检查编号连续性（按节内）
    by_section: dict[int, list[int]] = {}
    for tag in tags:
        sec_str, num_str = tag.split(".")
        by_section.setdefault(int(sec_str), []).append(int(num_str))

    print("=== 编号连续性 ===")
    for sec in sorted(by_section):
        nums = sorted(by_section[sec])
        expected = list(range(min(nums), max(nums) + 1))
        if nums != expected:
            errors.append(f"§{sec} 编号不连续: {nums}")
            print(f"  ❌ §{sec}: {nums}（应连续）")
        else:
            print(f"  ✓ §{sec}: {min(nums)}-{max(nums)}")
    print()

    # 3. 跨节引用检查
    refs = set(re.findall(r"\((\d+\.\d+)\)", content))
    defined = set(tags)
    broken = refs - defined
    print(f"=== 跨节引用 ({len(refs)} 处) ===")
    if broken:
        errors.append(f"引用了但没 \\tag 定义的编号: {sorted(broken)}")
        print(f"  ❌ 断裂引用: {sorted(broken)}")
    else:
        print("  ✓ 所有 (X.Y) 引用都对应已定义的公式")
    print()

    # 4. 文件长度
    line_count = len(content.splitlines())
    print(f"=== 文件长度 ===")
    print(f"  {line_count} 行")
    if line_count < 200:
        print("  ⚠️  低于 200 行，可能缺内容")
    elif line_count > 400:
        print("  ⚠️  超过 400 行，没'读薄'")
    else:
        print("  ✓ 在 200-400 行范围内")
    print()

    # 5. callout 检查（教科书风格禁用）
    callouts = re.findall(r"^>\s*\[!(\w+)\]", content, re.MULTILINE)
    print("=== Callout 检查（教科书风格禁用）===")
    if callouts:
        errors.append(f"含 callout: {set(callouts)}")
        print(f"  ❌ 发现 {len(callouts)} 个 callout: {set(callouts)}（应删除）")
    else:
        print("  ✓ 无 callout")
    print()

    # 总结
    if errors:
        print(f"=== 总结: {len(errors)} 处问题 ===")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    print("=== 总结: 全部通过 ✓ ===")


if __name__ == "__main__":
    main()
