---
description: 批量跑反向校验。扫一门课所有 T## tutorial，跟 _principles.md 对账，汇总 bug 报告。用法：/audit-tutorials CMEXXX
---

# /audit-tutorials

体检式扫整门课的 tutorial → _principles 反向校验。

## 用法

```
/audit-tutorials CME222
```

参数：课程代码（必需）。

## 执行步骤

1. **找课程文件夹**：
   ```bash
   ls -d 01_Projects/<CODE>_*/
   ```

2. **找所有 tutorial**：
   ```bash
   ls 01_Projects/<CODE>_*/T*.md
   ```
   若 0 个 tutorial → 报告"该课无 tutorial，无需 audit"，结束。

3. **检查 _principles.md 是否存在**：
   - 不存在 → 提示"先跑 distill-principles <CODE> 生成 _principles，再来 audit"，结束。
   - 存在 → 继续。

4. **逐个 tutorial 跑反向校验**：
   ```bash
   python ${CLAUDE_PLUGIN_ROOT}/shared/scripts/reverse_audit.py 01_Projects/<CODE>_*/T<NN>.md
   ```
   收集每个 tutorial 的：
   - 引用 (X.Y) 数量
   - 断裂引用数（_principles 没定义）
   - ⚠️ _principles 缺 标记数

5. **汇总报告**：
   ```markdown
   ## /audit-tutorials <CODE> 报告

   | Tutorial | 引用编号数 | 断裂 | ⚠️ 缺标记 | 总 bug |
   |---|---|---|---|---|
   | T01 | 5 | 0 | 3 | 3 |
   | T02 | 12 | 0 | 0 | 0 ✓ |
   | T03 | 18 | 0 | 7 | 7 |
   | ...

   ### 汇总
   - 总 bug 数：N
   - 涉及 _principles 漏抽：M 处
   - 建议补到 _principles：（列出最高频漏抽公式）

   ### 下一步
   - 跑 distill-principles <CODE> 重蒸馏 → 自动补这 N 处
   - 或人工审 _principles 决定补哪些
   ```

## 注意

- 这命令**只读不写** — 只是扫 + 报告，不动 tutorial 也不动 _principles
- 跑得快（每个 tutorial < 1 秒）
- 如果 tutorial 还没用 (X.Y) 编号引用（老 wikilink 风格）→ 报告"该 tutorial 还没升级到新规范，无引用可校验"
