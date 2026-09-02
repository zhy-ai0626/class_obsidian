---
description: 扫所有 CME* 课程，批量跑 distill-principles 蒸馏所有还没 _principles.md 的课。期末复习前一键搞定。
---

# /distill-all

批量蒸馏所有 CME 课程的 `_principles.md`。

## 执行步骤

1. **扫课程列表**：
   ```bash
   ls -d 01_Projects/CME*/
   ```
   列出所有 `<CODE>_课名/` 文件夹。

2. **筛选**：对每门课
   - 检查 `01_Projects/<CODE>_*/L*.md` 是否存在（至少 1 节 lecture，否则没东西可蒸馏）
   - 检查 `01_Projects/<CODE>_*/_principles.md` 是否已存在
     - **存在** → 列入"已蒸馏"，问用户要不要重蒸馏（默认跳过）
     - **不存在** → 列入"待蒸馏"

3. **跟用户确认清单**：
   ```
   待蒸馏：CME223 / CME217 / CME113 / CME212 / CME211
   已蒸馏（跳过）：CME213 / CME222
   预期总时间：5 课 × 5-10 分钟 ≈ 30-50 分钟
   ```
   用户 OK 后继续。

4. **逐课跑 distill-principles**：对每门待蒸馏课
   - 调用 `distill-principles` skill，参数 = 课程代码 + 课名
   - 等完成 → 跑 `shared/scripts/validate_principles.py` 自检
   - 记录评分预期 / 行数 / 公式总数

5. **汇总报告**：
   ```
   ## /distill-all 完成

   | 课程 | 行数 | 公式数 | 根本起点 | 自检 |
   |---|---|---|---|---|
   | CME223 | 312 | 28 | 3 | ✓ |
   | CME217 | 298 | 35 | 3 | ✓ |
   | ...

   建议：
   - 用 /audit-tutorials 跑 X 个有 T## 的课验证覆盖率
   - 期末前 N 周建议人工 review 各 _principles 评 8.5+/10
   ```

## 注意

- **不并行跑 distill-principles**（每次 distill 要 Read 全 lecture + 写 _principles，并行容易抢资源）
- 中途用户 Ctrl-C → 已完成的课保留，未做的下次接着跑
- 失败的课记录 + 报告原因（lecture 笔记数过少 / lecture 内容跨域过大 / 公式提取异常）
