# ingest-tutorial — Workflow detail

SKILL.md 里压缩过的步骤,这里放完整规则。

---

## §Step 1.8 — 截取原题图

每题的「原题」用原版 PDF 截图，不抄文字层（文字层会丢表格、上下标、图片里的数字）。

1. 用 PyMuPDF 找题号位置：`page.get_text("words")` 里 x 很小（左边距内）、内容是纯数字的词就是题号；记下每个题号的 y0。
2. 每题裁切区域：上边 = 本题题号 y0 − 4pt；下边 = 下一题题号之前所有文字 / 图片（`get_image_info()`）/ 表格线（`get_drawings()`）的最大 y1 + 6pt；左右取正文边距（如 x 80–535）。最后一题以页面内容结尾为界。
3. `page.get_pixmap(clip=rect, dpi=200).save(...)`，存到 `_attachments/<tutorial stem>/images/T##_Q<n>_original.png`。
4. **逐张 Read 看图核对**（可拼成联系表一次看多张）：不能截进页眉/文档标题、上一题的尾行、"END OF TUTORIAL" 之类结尾标记；表格和子题不能被截断。有问题就调 clip 重截。
5. 一道题跨页时分别截两段，存 `_Q<n>_original_1.png`、`_2.png`，笔记里上下连着嵌入。

```python
import pymupdf
d = pymupdf.open(pdf)
for i, p in enumerate(d):
    nums = [(w[4], w[1]) for w in p.get_text("words") if w[0] < 100 and w[4].isdigit()]
    boxes = [(w[1], w[3]) for w in p.get_text("words")] \
          + [(im["bbox"][1], im["bbox"][3]) for im in p.get_image_info()] \
          + [(x["rect"].y0, x["rect"].y1) for x in p.get_drawings()]
    for k, (n, y0) in enumerate(nums):
        top = y0 - 4
        nxt = nums[k + 1][1] if k + 1 < len(nums) else p.rect.y1
        bot = max(b1 for b0, b1 in boxes if top - 1 <= b0 < nxt - 2)
        p.get_pixmap(clip=pymupdf.Rect(80, top, 535, bot + 6), dpi=200).save(f"{out}/T##_Q{n}_original.png")
```

题号识别规则（x 阈值、是否为 "Q1"/"1." 格式）随 PDF 排版调整；Word 转来的 tutorial 先导出 PDF 再截。纯文本输入（无 PDF/图片）跳过本步，「原题」用 `>` 引用块逐字抄。

---

## §Step 5 — 逐题解答（每题固定版式）

按 `${CLAUDE_PLUGIN_ROOT}/skills/ingest-tutorial/assets/tutorial.md` 结构。

### 版式硬规则

- 每题**只有一个 `## Problem N` 标题**。题内分段一律用 `**粗体标签**`，**不开 `###` 小标题**——Obsidian 里 `###` 字号太大，一题被切成好几块，读起来跳。
- 顺序固定：

| 顺序 | 标签 | 内容 |
|---|---|---|
| 1 | **中文翻译** | `>` 引用块，整题逐句翻译 |
| 2 | **原题** | 原 PDF 截图（Step 1.8）+ 一行斜体出处「原题截图：Tutorial PDF 第 N 页，第 n 题。」 |
| 3 | **关键公式** / **关键规则** / **关键概念** | 表格，按题型选标签（见下节） |
| 4 | **已知条件** / **题目要求** | 计算题列已知量；概念题列题目要求 |
| 5 | **分步解题** | `**第 1 步：…**` 逐步；最后一步验算 |
| 6 | `> [!success] 答案` | 最终答案，带单位，多问逐条 |
| 7 | `> [!warning]- 易错点` | 默认折叠，2–4 条 |
| 8 | `> [!note]- English Concise Answer` | 默认折叠，2–4 行 |

- 翻译放在原题**上面**，原题截图下面**直接**接关键公式和已知条件，然后进入分步解题——中间不插别的段落。

### 中文翻译

- 整题翻译，不跳过短题。题内表格也译成 Markdown 表格，表头写「中文（English）」。
- 术语首次出现写「中文（English term）」，如「指令占比（instruction mix）」；必要时在括号里加一句白话解释（如「逻辑密度（logic density，芯片单位面积上的逻辑门数量）」）。
- 数字、单位、下标、子题编号 a)/b) 保持原样；题面里的参考答案（如 `Ans: 7800 Pa`）也照翻保留。

### §关键内容标签：怎么选

| 题型 | 标签 | 表头 | 例子 |
|---|---|---|---|
| 计算题（代公式出数） | **关键公式** | 公式 \| 符号含义 \| 本题用途 | CPU 时间、Amdahl 加速比 |
| 按规则/算法操作的题 | **关键规则** | 规则 \| 含义 \| 本题用途 | 进制转换、补码编码/解码、溢出判断、页面置换、调度算法 |
| 概念/简答/论述题 | **关键概念** | 概念 \| 含义 \| 与本题的关系 | 功耗墙、内存墙、clock rate 定义 |
| 概念题但核心就是一个式子 | **关键公式**（可加 **关键概念** 并列） | 同上 | "简述 Amdahl 定律" |

- 只列本题真正用到的（一般 2–5 行）。符号含义写清单位。
- 表下一行写「来源：」：有 `<CODE>_principles.md` 时用 `[[<CODE>_principles#§X.Y 标题\|(X.Y)]]`；没有时 wikilink 到 lecture 的**具体知识块标题**（`[[L01_xxx#知识块 8 · …]]`），写完校验锚点存在。讲义没单列、由变形/推广得到的公式在这句里注明。
- 题意有歧义时，在关键公式表下面放一个 `> [!note]` 写明采用哪种理解、为什么。

### 已知条件 / 题目要求

- **计算题 → 已知条件**：表格列「量 | 题目给的 | 换算后」，在这里就把单位换成基本单位（400 MHz → $4\times10^8$ 周期/秒）。隐含条件也写进来（"同一 ISA、同一程序 ⇒ 指令数相同"；"上一题结果 $T_{old}=1.85$ s"）。比例类数据先检查和是否为 1。
- **概念题 → 题目要求**：写清题目问了几件事、答案要覆盖哪几点、哪些是课件内容、哪些属于延伸。

### 分步解题

- `**第 1 步：求……**` 开头点明这一步求什么，下面一两句"为什么这么做"，再给 LaTeX 计算。每步只做一件事。
- 有子题按 `**(a)**`、`**(b)**` 分块，块内再分步；概念题用 `**第 1 点：……**`。
- 能用表格展示逐项计算的（加权 CPI 各项贡献、多段 Amdahl 各段新时间）用表格。
- **最后一步做验算或合理性检查**：换一种算法复算、与上限/量级对比、代回检查。这取代旧规范里开头单独的"量级估算"段。
- 解出答案后可加一两句"这说明了什么"（如"指令多反而更快，因为多的是便宜指令"），不要长篇。
- 课件之外的补充标「延伸（非原资料内容）」。

### 答案 / 易错点 / English

- `> [!success] 答案`：只放结论，带单位；不重复推导。
- `> [!warning]- 易错点`：带 `-` 默认折叠；写学生最可能犯的具体错误（"直接算术平均得 3.75"），不写空话。
- `> [!note]- English Concise Answer`：带 `-` 默认折叠；计算题 = 关键公式 + 代入 + 结论，2–4 行；概念题写完整句子。

### 反例

- ❌ 用 `### ① 原题`、`### 解答` 等小标题分段（字号过大）。
- ❌ 原题只抄文字层，表格数字丢失或错位。
- ❌ 翻译放在原题下面，或原题与关键公式之间插入解题思路段。
- ❌ 概念题硬写「关键公式：无」——应改用 **关键概念** + **题目要求**。
- ❌ 答案在正文末尾写一次、答案框再写一次、又在 English 里展开一遍完整推导。

---

## §Step 7.6 — `_principles` 反向校验(新规范核心)

tutorial 写完后,自动跟 `<CODE>_principles.md` 对账:

1. **Read** `01_Projects/<CODE>_课名/<CODE>_principles.md`(若不存在 → 跳过本 Step,Step 8 报告里提示用户"先跑 `distill-principles` 生成 _principles")
2. **grep tutorial 文件**所有形如 `(X.Y)` 的公式编号引用(包括 Step 3 公式速查表的"_principles 编号"列、Step 5 各题的"用到公式"行、解答正文)
3. 对每个 (X.Y) 引用,**grep _principles** 验证 `\\tag\{X\.Y\}` 是否存在
4. **不存在的**编号 → 记到下面 bug 报告
5. **公式速查表里标 `⚠️ _principles 缺`** 的条目 → 也记到 bug 报告
6. **tutorial 用到但既不在 _principles 也没显式引用的公式**(罕见,需主线程判断)→ 记到 bug 报告

**自动写入 tutorial 末尾**(在 `## 知识盲区` 之后,`## Verification steps for you` 之前):

```markdown
## 给 `distill-principles` 的反馈(_principles bug 报告)

做本 tutorial 时发现 [[<CODE>_principles]] 缺/不一致以下内容,下次蒸馏要补:

| 缺漏 / 冲突 | 哪几题用到 | 建议补到 _principles |
|---|---|---|
| **<公式名>** $<\text{LaTeX}>$ | Q1 / Q2 | §<节号> 加 |
| ⚠️ **<公式 A 形式> vs _principles <公式 B 形式> 冲突** | Q3 | 校验哪个对 |
```

7. **chat 提示**用户:`发现 N 处 _principles bug,要不要现在跑 distill-principles 重蒸馏？`
