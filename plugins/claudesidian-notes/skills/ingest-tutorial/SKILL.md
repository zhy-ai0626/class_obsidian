---
name: ingest-tutorial
description: 解一份 tutorial/习题集/往年考卷,产出教学质量解答(公式速查引 _principles 编号 + 量级估算 + 一气呵成推导 + English Concise Answer + 知识盲区报告),写入 01_Projects/<CODE>_课名/T##.md。只要用户说"解这份 tutorial / 做这份习题 / 解 T05 / 做练习 / solve these problems / 把这份 past paper 做一遍",或附上习题 PDF/图片/含答案的 .doc,就用本 skill。不要用于:要提交计分的作业(拒绝代解,引导到复习概念/做相似题,正式作业走 chemeng-coursework)、lecture 材料(→ ingest-lecture)。模糊说"help with homework"时先问是练习还是要交的。
---

# Skill: ingest-tutorial

## Role

产出**教学质量的解答**,不只是答案。一份好的 tutorial 笔记做 4 件事:

1. 上来汇总公式 + 数据(公式速查 + 数据表)
2. 解释**为什么**这步这么做 + 量级估算反向校验(思路与估算)
3. 用 wikilink 引用涉及概念
4. 列知识盲区(用户该复习哪些)

这是学习工具,不是要提交的作业。

## Ethical boundary

本 skill 是**学习辅助**。如果用户说"这是要交的成绩作业",拒绝并改为:
- 复习涉及概念
- 解释方法但不解
- 做相似题

教材习题 / 过往考试 / 练习集都 OK——这些是学习用的。

## When to trigger

- "解这份 tutorial / 做这些练习 / solve these problems"
- "帮我做 T##"(tutorial 编号,不是 assignment)
- 附习题集 / 练习单 / 过往考试

模糊场景(先问):
- "Help with my homework" → 问"这是练习(我可以解)还是提交(我只能审)?"

## Inputs

- 习题集(文本 / 图片 / PDF)
- 课程代码 + tutorial 编号
- 可选:相关 lecture 编号、specific topics

## Outputs

- `01_Projects/<CODE>_课名/T##_topic_snake.md`
- 知识盲区报告(写在 tutorial 笔记里 + chat 输出)

## Dependencies

启动时读:
- `${CLAUDE_PLUGIN_ROOT}/skills/ingest-tutorial/assets/tutorial.md`(笔记模板)
- 相关 lecture 笔记:`01_Projects/<CODE>_课名/L##_*.md`(按 `week` 字段匹配)

## Workflow

### Step 1: 加载上下文

1. 识别课程 / tutorial 编号
2. 找出相关 lecture 笔记(按 `week` 匹配 `L##_*.md`),Read 加载

### Step 1.5: 归档原始材料

把 tutorial 原文(PDF / 习题图)集中复制到 `_attachments/source/` 一份:

```bash
mkdir -p "01_Projects/<CODE>_课名/_attachments/source/"
cp "<tutorial_path>" "01_Projects/<CODE>_课名/_attachments/source/"
```

- **保留原文件名**(不要改成 source.pdf)
- 纯文本输入跳过
- 已被 `.gitignore` 排除 `*.pdf` `*.pptx` `*.ppt`,**不会进 git**
- 和 lecture 共用同一个 `source/` 目录;不需要按 lecture/tutorial 分子目录

### Step 1.55: `.doc`/`.docx` → markdown(输入是 Word 文档时才做)

很多带答案的 tutorial 是老 `.doc`(OLE2 二进制)。转成 `full.md` 喂给后续步骤:

- **`.docx`**:直接 `pandoc "<f>.docx" -o "<stem>/full.md" --extract-media="<stem>" --wrap=none`
- **`.doc`**:先用 Word COM 转 `.docx`,再 pandoc。**逐个转、每份新开 Word 实例**——批量循环会卡死。踩坑细节 + 可靠脚本见 `references/lessons.md` §.doc 转 markdown
- 转出的中间 `.docx` 删掉(`source/` 只留原 `.doc`);正确选项在 md 里是 `[...]{.underline}` 或 `**加粗**`,Step 2 据此抽答案

### Step 1.6: 从 manifest 加载参考资料索引

Read `01_Projects/<CODE>_课名/manifest.md`(若存在),从 **References 段**拿到所有有 "MinerU 索引" 的资料路径:

- **解析方式**:References 表里每行,若 "MinerU 索引" 列是 `✅ <path>` → `<path>` 就是 grep-able 的 markdown
- 对每个 `<path>`,**Read 前 100 行**了解资料目录(表号 / 物质 / 单位 / type)
- **记住所有 (path, type) 对**,Step 4 按 type 优先级 grep(type=physprop 优先查物性;type=unitconv 优先查单位换算;type=textbook/handbook 兜底)

**找不到 manifest.md 时**:
- 检查 `_attachments/source/` 下有没有典型参考资料文件名(`Appendix*.pdf` / `Table*.pdf` / `Handbook*.pdf` / `*物性*.pdf` 等)
- 有 → chat 提示用户:"发现 `<filename>` 是疑似参考资料但未处理,**建议先跑 MinerU + 建 manifest.md**,做 tutorial 时能自动查。要现在做吗?"——用户点头就按 `${CLAUDE_PLUGIN_ROOT}/shared/assets/manifest-example.md` 模板建
- 没有 → 跳过,Step 4 走原 fallback("请核实")

**注意**:
- 也 Read `references.md`(若存在)——人类视角的资料布局和用法说明,补充 manifest 的机读信息
- 只读 markdown,**不要为了找数据 vision 整本参考 PDF**——那是 grep 的事
- **绝不写死任何文件名 glob**(`Appendix*` 之类),完全用 manifest 声明的路径——不同教材命名风格不同

### Step 1.7: 加载 `_principles.md`(公式编号体系)

Read `01_Projects/<CODE>_课名/_principles.md`(若存在),拿到整门课的**公式编号体系** (1.1)→(N.X)。

后续 Step 3 / 5 引用公式时,**优先用 _principles 的 (X.Y) 编号**,而不是 wikilink 回 lecture(老规范)。

若 `_principles.md` 不存在:
- chat 提示用户:`这门课还没有 _principles.md,建议先跑 distill-principles 生成。本次 tutorial 按老规范用 wikilink 引 lecture。`
- 继续跑(降级到老规范),Step 7.6 跳过

### Step 2: 解析问题

把输入拆成编号问题。每题识别:
- 题目原文(verbatim)
- 子题(a / b / c ...)
- 已知 vs 待求
- 隐含假设

### Step 3: 公式速查表

从相关 lecture 的知识块里提取本 tutorial 要用的公式,填 `## 本次公式速查`:

| 公式 | 含义 | _principles 编号 |
|---|---|---|
| $J_A = -D_{AB} \frac{dc_A}{dz}$ | Fick 第一定律 | [[_principles#§1.2 Fick 第一定律\|(1.2)]] |
| $c_A = S\,p_A$ | Solution-Diffusion 致密膜 | ⚠️ _principles 缺 |

规则:
- 只列实际要用的(不超 ~10 个)
- **优先引 _principles 公式编号** (X.Y) — 用 `[[_principles#§X.Y 标题\|(X.Y)]]` 形式
- _principles 没有的公式 → 标 `⚠️ _principles 缺` 并记到 Step 7.6 bug 报告
- **不再用 wikilink 引 lecture**（lecture 是 _principles 上游，校验回 _principles 更高效）
- 例外：物理意义 / 推导图等 _principles 没有的内容,wikilink 回 lecture 看图

### Step 4: 数据表

填 `## 本次数据与常数`:

| 符号 | 名称 | 值 | 来源 |
|---|---|---|---|
| $D_{AB}$ | CO₂ 在空气中扩散系数 | $1.6 \times 10^{-5}$ m²/s (298K, 1atm) | 课本 Table 2.1 |

**数据可信度规则**(按优先级):

| 情况 | 处理 |
|---|---|
| 题目明确给出 | 直接用,标"题目给定" |
| 通用常数(R / g / Avogadro) | 直接用,无需标 |
| **物性数据 → 先按 type 优先级 grep Step 1.6 加载的所有 MinerU 索引** | 命中 → 给值 + 标"<资料名(从 manifest)> 表<X>,已抽可信" |
| 物性数据 → manifest 已声明索引但 grep 未命中(MinerU 表格识别失败) | 主线程 Read 对应页 vision 抽(先 grep 资料 full.md 里的表标题/物质名拿到临近页码,再 Read 原 PDF 对应页) + 标"vision 抽自 <资料名> p.NN,**请核实**" |
| 物性数据 → manifest 里没有索引、`source/` 也无对应 PDF | 凭训练数据估,标 `> [!warning] 请核实: 见 <课本> 对应附录`,**绝不省"请核实"** |

**绝不默默编造物性数据**。宁可留空让用户查,也不给可能错的值。
**有 manifest 索引时优先 grep**——这是减少 "请核实" 数量、提高答案可用性的关键。
**type 优先级**:physprop > textbook > handbook > unitconv (按题目需要选)。

### Step 5: 逐题解答(方案 B — 中文主线 + 英文摘要)

按 `${CLAUDE_PLUGIN_ROOT}/skills/ingest-tutorial/assets/tutorial.md` 结构,每题一条线性叙事:

- **> (原题)** verbatim + **中文翻译**(默认必带,短概念题可跳)
- **用到公式**:列 `_principles` 编号 (X.Y),不用 wikilink 引概念
- **解答**(中文,一气呵成):开头点明本质 → 量级估算内嵌 → 逐步推导(每步 motivation + 数学)→ 对照估算 → 结尾 `**最终答案**: ...(带单位)`,不开独立小节
- **English Concise Answer**(默认必带):100–200 词段落,可直接抄考卷,完整句子非 bullet
- **易错** + 可选 **变式**

→ 完整规则 + Good/Bad 对照见 `references/workflow-detail.md` §Step 5

### Step 6: 答案速查表

所有题解完后,填 `## 答案速查`:

| 题号 | 最终答案 | 涉及概念 |
|---|---|---|
| 1 | $P = 49.9$ kPa | [[状态方程]] |
| 2(a) | $J_A = 3.2 \times 10^{-4}$ mol/(m²·s) | [[Fick 第一定律]] |

### Step 7: 知识盲区报告

填 `## 知识盲区 / Gaps identified`:
- 题目要用但相关 lecture 笔记弱(或没有)的概念
- 题目隐含但用户可能没意识的:"Problem 2 第二部分默认你知道 Clausius-Clapeyron,虽然题目没点名"

### Step 7.5: 更新 manifest.md(若存在)

若 `01_Projects/<CODE>_课名/manifest.md` 存在:
1. 找 Tutorials 表中对应原 PDF 文件名的那行(按 `<Tutorial 文件名>` 列匹配)
2. 把"笔记"列从 `–` 改为 `✅ [[T##_topic_snake]]`
3. 若本次跑了 MinerU(罕见,见 Step 1.6 例外路径),把"MinerU 索引"列也改成 `✅ <path>`
4. 在文件末尾"修改记录"段追加一行:`YYYY-MM-DD: ingest-tutorial 更新 <Tutorial 文件名> 的笔记列`

若 manifest.md 不存在:**跳过**,不强制建。在 Step 8 报告里提示用户"考虑建 manifest.md 跟踪状态"。

⚠️ **不要**修改 manifest.md 其他行/段——只动你刚处理的那行。

### Step 7.6: `_principles` 反向校验(**新规范核心**)

tutorial 写完后,自动跟 `_principles.md` 对账:Read _principles → grep tutorial 里所有 (X.Y) 引用 → 逐一验证 _principles 里 `\tag{X.Y}` 是否存在 → 不存在的 + Step 3 标 `⚠️ _principles 缺` 的 → 汇总成 bug 报告写到 tutorial 末尾(`## 知识盲区` 之后),chat 提示用户要不要重蒸馏。

`_principles.md` 不存在则跳过本步,在 Step 8 报告里提示先跑 distill-principles。

→ 完整 7 步流程 + bug 报告模板见 `references/workflow-detail.md` §Step 7.6

### Step 8: 报告

```markdown
## Tutorial solved: <CODE> T##

**Problems**: N solved
**Covers**: [[concept-A]], [[concept-B]]
**公式速查**: N formulas from [[L##_...]]
**数据标记**: N values used, K marked "请核实"

**Gaps identified**:
1. [[concept-X]] — 相关 lecture 笔记弱
2. "Maxwell relations" — 没笔记,考虑 ingest 相关 lecture

**Verification steps for you**:
- 自己做 problem 1 对答案
- 物性数据查课本 appendix
```

## Rules

1. **不只给最终答案** — 必须展示推导步骤
2. **数值答案必须带单位**
3. **不伪造物理/化学数据** — 不确定用 `> [!warning] 请核实` 标记
4. **不声称"已验证"** — 结果是 proposed solution,等用户验
5. **详细计算前必须做量级估算** + 算完反向校验
6. **不给题目难度排序**("trivial" / "简单"等)

## Reference index

| 何时读 | 文件 |
|---|---|
| Step 5 写解答 / 不确定方案 B 结构怎么落地 | `references/workflow-detail.md` §Step 5 |
| Step 7.6 反向校验细节 / bug 报告模板 | `references/workflow-detail.md` §Step 7.6 |
| 想看完整 Good 范例(Problem 2 范德华) | `references/lessons.md` §Example |
| 遇到具体 failure(PDF 加密误报 / 数据缺单位等) | `references/lessons.md` §Failure modes |
