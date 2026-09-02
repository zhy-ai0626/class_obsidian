# ingest-tutorial — Lessons (Example + Failure modes)

跑 skill 前可选读;遇到具体 failure 模式时按表查。

---

## Example

> ⚠️ 本例写于老规范时期,公式引用格式以 SKILL.md Step 3/5 为准(_principles 编号,不用 wikilink 引 lecture / 概念);看结构(一气呵成解答 + English Concise Answer),别抄"来源"列和"涉及知识点"的引用格式。

**Good**(方案 B 结构):
```markdown
## 本次公式速查

| 公式 | 含义 | 来源 |
|---|---|---|
| $PV = nRT$ | 理想气体状态方程 | [[L03_equations_of_state]] |
| $(P + \frac{n^2a}{V^2})(V-nb) = nRT$ | 范德华方程 | [[L03_equations_of_state]] |

## Problem 2

> (原题) Closed rigid vessel 0.1 m³, 2 mol CO₂, 300 K. Calculate
> pressure using (a) ideal gas (b) van der Waals. Discuss deviation.
>
> **中文翻译**:一个 0.1 m³ 的密闭刚性容器,内含 2 mol CO₂,温度 300 K。
> 求压强:(a) 用理想气体方程 (b) 用范德华方程,并讨论二者偏差。

**涉及知识点**: [[状态方程]], [[范德华方程]]

### 解答

这题本质是对比理想气体 vs 实际气体的修正,关键在理解范德华 `a`(分子间
吸引,降 P)和 `b`(分子体积,升 P)的物理作用。

**量级估算**:P ≈ 2×8.3×300/0.1 ≈ 50 kPa(0.5 atm)。CO₂ 在这条件下
偏差应在 1–5% 范围。

**(a) 理想气体**——直接代入,无相互作用修正:
$$P = \frac{nRT}{V} = \frac{2 \times 8.314 \times 300}{0.1} \approx 49.9 \text{ kPa}$$
与量级估算一致。

**(b) 范德华**——加入 a, b 修正项。先把方程展开求 P:
$$P = \frac{nRT}{V - nb} - \frac{n^2 a}{V^2}$$
代入 CO₂ 的 a = 0.3640 Pa·m⁶/mol², b = 4.267×10⁻⁵ m³/mol(此处查 [[Perry's Handbook]]):
$$P_{vdW} \approx 48.2 \text{ kPa}$$
偏差 3.4%,与估算的 1–5% 吻合;`b` 让 P 略升, `a` 让 P 略降,后者占主导,所以 P_vdW < P_ideal。

**最终答案**:(a) $P_{ideal} = 49.9$ kPa;(b) $P_{vdW} = 48.2$ kPa,偏差 3.4%

### English Concise Answer

Using the **ideal gas equation** with $n$=2 mol, $T$=300 K, $V$=0.1 m³:
$$P_{ideal} = \frac{nRT}{V} = \frac{2 \times 8.314 \times 300}{0.1} \approx 49.9 \text{ kPa}$$

Using the **van der Waals equation** with CO₂ constants $a = 0.3640$ Pa·m⁶/mol² and $b = 4.267 \times 10^{-5}$ m³/mol:
$$P_{vdW} = \frac{nRT}{V - nb} - \frac{n^2 a}{V^2} \approx 48.2 \text{ kPa}$$

The van der Waals pressure is about **3.4 % lower** than the ideal-gas value. The attractive term $-n^2a/V^2$ dominates over the excluded-volume correction $-nb$, so real CO₂ exerts slightly less pressure than predicted by the ideal-gas law at this condition.

### 易错

> [!warning]
> - $n^2a/V^2$ 里 $n^2$ 容易写成 $n$
> - 范德华 a 在不同文献单位不同,差 10⁶ 倍要小心
```

**Bad 反例**:
- 无中文翻译(中文母语用户读长英文题面慢)
- 无 English Concise Answer(考试 / 作业要交英文版没法直接用)
- "思路"和"解答"分两段写,同一推理说两遍
- "解答"末尾给答案,又开"最终答案"段再写一次(同结论说 3 次)

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
