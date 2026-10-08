# ingest-tutorial — Lessons (Example + Failure modes)

跑 skill 前可选读;遇到具体 failure 模式时按表查。

---

## Example

范例取自 CST308 T01（2026-10 定稿版式）。公式来源列的引用格式以 SKILL.md Step 3/5 为准。

### Good A：计算题（关键公式 + 已知条件）

````markdown
## Problem 2

**中文翻译**

> 同一个**指令集架构（instruction set architecture, ISA）**有两种实现。计算机 A 的**时钟周期时间（clock cycle time）**为 250 ps，运行某程序时 CPI 为 2.0；计算机 B 的时钟周期时间为 500 ps，CPI 为 1.2。对这个程序而言，哪台计算机更快？快多少？

**原题**

![[_attachments/<stem>/images/T01_Q2_original.png]]

*原题截图：Tutorial PDF 第 1 页，第 2 题。*

**关键公式**

| 公式 | 符号含义 | 本题用途 |
|---|---|---|
| $T_{\mathrm{CPU}}=IC\times CPI\times t$ | $IC$：指令数；$t$：时钟周期时间（秒/周期） | 求两台机器的 CPU 时间 |
| $n=\dfrac{T_Y}{T_X}$ | X 比 Y 快 $n$ 倍 | 求快多少 |

来源：[[L01_xxx#知识块 8 · CPU 性能方程与加权 CPI]]。

**已知条件**

| 量 | 计算机 A | 计算机 B |
|---|---|---|
| 时钟周期时间 $t$ | 250 ps | 500 ps |
| CPI | 2.0 | 1.2 |
| 指令数 $IC$ | 同一 ISA、同一程序 ⇒ 相同，设为 $I$ | $I$ |

**分步解题**

**第 1 步：求每台机器的 CPU 时间**

给的是周期时间，所以用乘法形式：

$$
T_A=I\times2.0\times250\ \text{ps}=500I\ \text{ps},\qquad T_B=I\times1.2\times500\ \text{ps}=600I\ \text{ps}
$$

**第 2 步：求快多少**

$$
\frac{P_A}{P_B}=\frac{T_B}{T_A}=\frac{600I}{500I}=1.2
$$

**第 3 步：检查**

$I$ 约掉，不需要具体指令数；A 的 CPI 高但周期只有一半，结果合理。

> [!success] 答案
> - **计算机 A 更快**，性能是 B 的 **1.2 倍**

> [!warning]- 易错点
> - 只比较 CPI 或只比较周期：必须相乘。

> [!note]- English Concise Answer
> $T_A=500I$ ps, $T_B=600I$ ps, so A is $600/500=1.2$ times as fast as B.
````

### Good B：概念题（关键概念 + 题目要求）

````markdown
**关键概念**

| 概念 | 含义 | 与本题的关系 |
|---|---|---|
| 功率密度（power density） | 单位面积上的功耗 | 频率、密度上升 → 散热难 |
| 存储器延迟（latency）/ 吞吐量（throughput） | 等多久拿到数据 / 每秒传多少数据 | 跟不上处理器 → 处理器空等 |

来源：[[L02_xxx#知识块 6 · …]]（Slide 12）。

**题目要求**

列出并简要讨论障碍：课件给两项（功耗、存储器速度）；RC 延迟是教材补充，标延伸。

**分步解题**

**第 1 点：功耗与散热**……
**第 2 点：存储器延迟与吞吐量**……
**第 3 点：RC 延迟**（延伸，非原资料内容）……
````

规则/算法题（进制转换、补码）同 Good A，只把 **关键公式** 换成 **关键规则**，表头「规则 | 含义 | 本题用途」。

### Bad 反例

- 用 `### ① 中文翻译`、`### 解答` 等小标题分段：Obsidian 里字号过大，一题被切碎
- 原题只抄 PDF 文字层：表格是图片时数字全丢
- 翻译放在原题下面；原题与关键公式之间插"思路/量级估算"段
- 概念题写「关键公式：无」而不换成关键概念
- 无中文翻译、或只翻译一半（表格不译）
- 同一结论在正文、"最终答案"段、答案框里写三遍

---

## .doc 转 markdown(Step 1.55 细节)

老 `.doc`(文件头 `D0 CF 11 E0` = OLE2 二进制)pandoc 读不了,得先用 **Word COM** 转 `.docx`。这一步很爱卡死,2026-07-06 G0201 宏观 ingest 反复踩,正确姿势:

**先解锁**(inbox / 下载来的文件带"来自网络"标记,会触发 Word Protected View 阻塞自动化):
```powershell
Get-ChildItem "<source>\*.doc" | Unblock-File
```

**逐个转,每份新开一个 Word 实例**(关键——一个实例里循环开多份会整批卡死):
```powershell
# 对每个 stem 单独跑:新建 Word → Open → SaveAs2(16=docx) → Close → Quit → Release
$word = New-Object -ComObject Word.Application
$word.Visible = $false; $word.DisplayAlerts = 0
$doc = $word.Documents.Open("<base>\<stem>.doc", $false, $true, $false)  # ConfirmConversions=false, ReadOnly, 不加最近列表
$doc.SaveAs2("<base>\<stem>.docx", 16)
$doc.Close(0); $word.Quit()
[System.Runtime.Interopservices.Marshal]::ReleaseComObject($word) | Out-Null
```

**别踩的坑**:
- ❌ 参数用 `[ref]` 包 → PowerShell 报 "psobject 转换" 错。直接传值
- ❌ 用 `powershell -File 子进程` 跑 → 中文路径(`经济学原理`)编码乱码,找不到文件。**直接在 PowerShell 工具里跑**
- ❌ 一个 Word 实例批量循环 → 卡死;卡了先 `Stop-Process -Name WINWORD -Force` 再重来
- 本机没装 LibreOffice(装了的话 `soffice --headless --convert-to docx` 更省事,无 COM 坑)

**转完 pandoc**:`pandoc "<stem>.docx" -o "<stem>/full.md" --extract-media="<stem>" --wrap=none`,然后删中间 `.docx`。

→ 全局记忆版:`~/.claude/.../memory/env_word_com_doc_convert.md`

---

## Failure modes

| 模式 | 触发 | 处理 |
|---|---|---|
| 用户说"这是要交的作业" | 提交场景 | 拒绝直接解,改为复习概念 / 做相似题 |
| `.doc` 批量转 docx 卡死 | Word COM 一个实例开多份 / Protected View | 先 `Unblock-File`,逐个转+每份新开 Word 实例;卡了 kill WINWORD 重来。见上 §.doc 转 markdown |
| 数值答案缺单位 | 题目本身省单位 | 补回 SI 单位,在解答里说"原题省略" |
| 公式表与解答冲突 | 公式不一致 | FAIL,先和用户对齐正确版本 |
| 题号格式混乱 | 1.a vs 1(a) 等 | 统一 `N(a)`,文件头注明"原格式 X" |
| 物性数据不确定 | 题目要用但 AI 不知 | `> [!warning] 请核实` + 指向 handbook 条目,绝不编造 |
| Read PDF 报 password-protected | 工具偶发误报(实际未加密,PyMuPDF 直接打开 is_encrypted=False) | 主线程跑 `py -c "import fitz; ..."` 提取文本到临时 txt,把文本喂给 sub-agent;**不要让 sub-agent 自己重试 Read** |
