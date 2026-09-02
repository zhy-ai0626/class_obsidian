# 经验教训 / Failure modes / 触发示例

## CME213 迭代历史（v1 → v4）

- **v1** 太啰嗦（callout 多、ASCII 图、"为什么"叙述）→ 评 7.5/10
- **v2** 教科书初版（删 callout）→ 7.0/10（删过头丢易错点）
- **v3** 加推导 sketch + 假设清单 → 9.0/10
- **v4** 加通量定义 + 拆步骤 + "常见错"6 处 + 物理意义 3 处 → 9.3/10

**最终模板就是 v4**（见 `template.md` + `style-guide.md`）。新课跑出来应该一步到位 ≥ 8.5。

## CME222 教训

第一次跑 CME222 只看 L12 revision，**没全文扫 L01-L11**，结果撞出 17 个 _principles bug（来自 T01-T04 反向校验）：

- 球/圆柱坐标单向扩散闭式（L05 有，蒸馏漏）
- Solution-Diffusion 致密膜（L04 提了一点，蒸馏漏）
- Wilke 调和完整公式（L03 有，蒸馏只给了 "提了一句"）
- Scheibel / Leffler-Cullinan / Tyn-Calus / Nernst（L04 有，全漏）
- Hindered diffusion + 因子（L04 有，漏）
- 混合扩散含 α 通用版（L04 有，漏）
- 准稳态显式时间公式（L05 有，漏）
- 单向扩散指数浓度分布（L05 有，漏）
- Hirschfelder 温度外推（L03 有，漏）
- Brokaw 极性修正完整公式（L03 有，漏）

**根因**：Step 1 只 Glob + 看 revision，没强制 Step 1.5 全文扫公式。已加到 SKILL 主流程。

## Failure modes

| 模式 | 触发 | 处理 |
|---|---|---|
| 没找到足够根本起点 | 课程概念性强（如材料）公式不多 | 用"基本原理"代替"守恒"（如材料的"晶体结构对称性""相图规则"） |
| 公式编号冲突 | 跨节引用编号写错 | Step 6 自检必跑 `grep -oP '\\tag\{[0-9.]+\}'` 检查序列 |
| Formula Sheet 显示孤立公式 | PPT 没讲但 Formula Sheet 列了（典型如 Damköhler）| 也收进推导树 — 标注 "Formula Sheet 单列" + 用对应原理派生 |
| lecture 笔记结构差异大 | 不同 lecture 用不同 wikilink 风格 | 统一在 _principles 里用 (X.Y) 编号，不依赖 lecture wikilink |
| 用户改了 _principles 不让重写 | 增量更新 | Read 旧文件，仅 Edit 需要改的 § 段；不 Write 重写 |
| **CME222-style 全文扫漏抽** | 偷懒只看 revision / 速查卡 | **必须 Step 1.5 全文 grep `$$ ... $$`**，每个 L## 都扫 |

## Example trigger flow

用户："蒸馏 CME222 传质"

→ Step 1: Glob L01-L09 + manifest.md
→ **Step 1.5: 逐节 Read L01-L09 + grep `$$` 列大清单**（关键！别偷懒）
→ Step 1.6: 读已有 T*.md 公式速查表 → 补到大清单
→ Step 2: 识别根本起点（Fick 1st/2nd、连续性方程、对流-扩散方程）
→ Step 3: 推导树（稳态 1D 扩散 / 非稳态 / 边界层 / 双膜模型...）
→ Step 4-5: Write `_principles.md` 教科书风格（按 `template.md` 结构 + `style-guide.md` 规则）
→ Step 6: 自检（编号序列 / 符号覆盖 / 行数 / 无 callout）
→ Step 7: 报告评分预期 8.5-9.5
