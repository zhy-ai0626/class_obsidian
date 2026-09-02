---
name: ingest-paper
description: 把一篇论文（main + 多格式 SI）转成 markdown，含 vision 核对 + 图按 Figure 编号重命名 + 图分级 alt text。Triggers - "整理这篇论文" / "处理这篇 paper" / "转 paper 成 md" / "ingest paper"。
---

# Skill: ingest-paper

## Role

把一篇论文转成**对 AI 友好**的结构化 markdown：
- `main.pdf` → `main.md` + `images/`（图按 Figure 编号命名 + **分级 alt text**）
- `si.<任意格式>` → `si.md` + `images_si/`（同上，SI 命名前缀 figS）

**核心目的**：vision 核对发现的错漏（漏抽 caption、误识公式、表格乱）**全部修正写回 `main.md`/`si.md`，持久化**；每张图加分级 alt text（关键图详细 / 一般图一句话）—— 以后做笔记模板 / 写综述时只读 md 就能让 LLM 理解每张图讲什么，**不需要重读 PDF / 重 vision，省 token**。

**不做**：
- 字段抽取（拉伸强度、电导率等专属字段）—— 那是后续 `extract-paper-note` skill 的事
- 生成 notes.md / staging.xlsx / checklist.md —— 笔记模板是独立步骤，本 skill 不碰

## When to trigger

- "整理这篇论文" / "处理这篇 paper" / "把这篇 paper 转 md" / "ingest paper"
- 用户指定 `01_Projects/Review_<主题>/papers/(YYYY) Title/` 路径下的论文文件夹

不应触发：
- lecture（走 `ingest-lecture`）/ tutorial（走 `ingest-tutorial`）
- 模糊"summarize this paper"（先问用户）
- Stage 1 拉 PDF（那是上游文献采集流程的事，不在本 skill 范围）

## Inputs

- **论文文件夹路径**，例：`01_Projects/Review_<主题>/papers/(YYYY) Author - Title`
- 文件夹必须有 `main.pdf`；可选 `si.<ext>`（多格式）
- 可选：`backup_log.csv`（项目根 `Review_<主题>/`，用于查 Zotero metadata）

## Outputs

```
(YYYY) Title/
├── main.pdf                 # 不动（只读）
├── si.pdf / si.docx / ...   # 不动（只读）
├── main.md                  # vision 核对修正过的；图引用带分级 alt text
├── si.md                    # 同上（如有 SI）
├── images/                  # main 的图，按 fig<编号>_<topic-slug>.jpg 命名
├── images_si/               # SI 的图，按 figS<编号>_<topic-slug>.jpg 命名
├── meta.yaml                # title / authors / DOI / journal / year
└── _attachments_orig/       # 不能转 md 的原 SI（cif / 视频 / 大图集）
```

main.md 里图引用形如：
```markdown
![Stress-strain curves of 4 samples (PIBA/AM ratio 25/50/65/80 mol%). Sample 65% shows highest toughness ~22 MJ/m³, counterintuitive peak attributed to optimal phase domain size (see fig 4 morphology).](images/fig3_stress-strain.jpg)
```
关键图：alt 是密集的 AI 友好描述（关键数字 + 趋势 + 反直觉点 + 跟其他图关系）
一般图：alt 是一句话简短描述

## Dependencies

启动时读：
- 项目根 `backup_log.csv`（拿 paper metadata，可选）

工具：
- `${CLAUDE_PLUGIN_ROOT}/shared/scripts/mineru_convert.py`（PDF → md，带 batch_id 缓存断点续跑）
- `${CLAUDE_PLUGIN_ROOT}/shared/scripts/process_si.py`（SI 多格式 dispatcher）
- `${CLAUDE_PLUGIN_ROOT}/shared/scripts/extract_images.py`（PDF → 逐页 PNG，**复用 lecture 的**）
- `.env` 含 `MINERU_API_TOKEN`

依赖包（一次性）：
```bash
pip install requests PyMuPDF Pillow python-docx openpyxl
```

## Workflow

### Step 1: 加载上下文 + 检查输入

1. 检查 paper folder 存在
2. 检查 `main.pdf` 在；不在就报错让用户补
3. 列 SI 候选（`si.*` / 文件夹里所有非 `main.pdf` 非 `*.md` 的文件）
4. 从 `backup_log.csv` 拿这篇 paper 的 metadata（title/key/doi）；没 csv 就跳过

### Step 2: PDF → md（main + SI 一条命令搞定）

```bash
py ${CLAUDE_PLUGIN_ROOT}/shared/scripts/mineru_convert.py --paper-dir "<folder>"
```

`--paper-dir` 模式自动检测 `<folder>` 下的 SI 文件并分发处理：

| SI 格式 | 处理 | 走哪个流程 |
|---|---|---|
| 无 SI | 只跑 main.pdf → main.md + images/ | 仅 MinerU |
| `si.pdf` | main + SI 都走 MinerU，输出 main.md / si.md + images/ + images_si/ | MinerU |
| `si.docx` | main 走 MinerU；SI 自动 fallback 到 `process_si.py`（python-docx 解析）| MinerU + process_si |
| `si.xlsx` | 同上，SI 走 pandas → md table | MinerU + process_si |
| `si.zip` | 同上，SI 解压后递归处理内部 pdf/docx/xlsx | MinerU + process_si |
| `.cif` / 视频 / 其它 | 原文件 mv 到 `_attachments_orig/` → `si.md` 加占位行 | process_si 兜底 |

**输出**：`<folder>/main.md` + `<folder>/si.md`（如有 SI）+ `<folder>/images/<hash>.jpg` + `<folder>/images_si/<hash>.jpg`

如果 MinerU 失败（token 过期 / 配额超 / 超时），**fallback 到纯 vision 模式**（跳过 Step 2，靠 Step 4 的 vision 写 main.md）。

### Step 3: 渲染 PDF → 逐页 PNG（vision 核对用）

```bash
# main
py ${CLAUDE_PLUGIN_ROOT}/shared/scripts/extract_images.py "<folder>/main.pdf" "<folder>/_pages_main/" --prefix main --pages --dpi 150

# SI（只对 PDF SI 跑，DOCX/XLSX 已经准确转过 md 不需要 vision）
py ${CLAUDE_PLUGIN_ROOT}/shared/scripts/extract_images.py "<folder>/si.pdf" "<folder>/_pages_si/" --prefix si --pages --dpi 150
```

### Step 4: 多 sub-agent 并行 vision 核对

按页数拆 sub-agent（≤8 页用 2 个 / 9-15 页 2 个 / 16-30 页 3 个 / >30 页 4 个）。main 和 SI 分开拆，避免 caption 编号串位。

每个 sub-agent 读 `_pages_<main|si>/<page>.png` + `<main|si>.md` 对应段，输出**四块结构化报告**：

1. **块 1 — patches**：用 anchor 文本（非行号）定位的 md 修正
2. **块 2 — 图重命名清单**：完整 32 位 old_hash + 新名 + tier + alt text
3. **块 3 — caption 完整性 + metadata 核对**（仅第一个 sub-agent）
4. **块 4 — 跨页公式/表格/段落核对**

→ 完整的四块输出格式、命名规则、alt text 分级规则（critical 密集 / general 一句话）、多 panel 图 lead+follow 写法：见 `references/workflow-detail.md` §Step 3

### Step 5: 主线程聚合 + apply patches

收齐所有 sub-agent 报告后：批量 mv 图 → 同步 md 图引用 + 写入 alt → apply 块 1 patches → 写 meta.yaml → verify Read 抽查 3 patch + 3 图。

→ 详细聚合步骤、verify 检查项：见 `references/workflow-detail.md` §Step 3c

### Step 6: 清理临时

```bash
rm -rf <folder>/_pages_main/ <folder>/_pages_si/ <folder>/_tmp_si/
```

**保留**：`main.md`、`si.md`、`images/`、`images_si/`、`meta.yaml`、`_attachments_orig/`（如有）。

### Step 7: 报告

```markdown
## ingest-paper 完成: (YYYY) Title

**main.md**: X 行，应用 N 个 patch
**si.md**: Y 行（如有），应用 M 个 patch
**图**: main N 张（A critical + B general）/ SI M 张（C critical + D general）
**alt text**: 全写入 ✓
**metadata**: title ✓ / authors ✓ / DOI ✓
**SI 格式**: pdf / docx / xlsx / zip / 无
**Token 使用**: MinerU N 次（cache 续跑省 K 次）/ vision N agent × M 页
```

## Rules

1. **不动 PDF / 原 SI 文件**（只读，纯单向产出）
2. **vision 修正必须写回 main.md / si.md**——本 skill 的核心价值。修正只在 console 里 print 出来等于浪费
3. **图重命名按 Figure/Table 编号**，不用 hash。已经是语义名（不是 32 位 hex）的图跳过，不重复重命名
3.5. **图必须有分级 alt text**（本 skill 默认行为）：critical 图 C 级密集描述、general 图一句话。写给 AI 看不是给人看。已经有非空 alt（不是占位）的图跳过，不重复改
4. **不抽字段 / 不生成 notes.md**——笔记模板（notes.md / staging.xlsx / checklist.md）是 `extract-paper-note` skill 的事，本 skill 完全不碰。但 vision 必须保证表格/caption/公式/数值**完整准确进 md**，为后续 skill 铺路
5. **MinerU 失败有 fallback**——纯 vision 模式仍可生成 main.md（质量略低但不阻塞）
6. **DOCX/XLSX/ZIP 不走 vision**——这些格式 python-docx / pandas 转换已经精准，不需要 vision 核对，也不加 alt text
7. **跨 sub-agent 不要让它们看对方的 md**——main 的 sub-agent 看 main.pdf，SI 的看 si.pdf，避免 caption 编号串位

## 跟其他 skill 的关系

- **`ingest-lecture`**：思路相似（MinerU + vision），但 lecture 是 slide-by-slide 模式 + 嵌入推荐；本 skill 是论文专用，砍嵌入推荐、加多格式 SI、加 metadata 核对
- **Stage 1（从文献管理软件拉 PDF）**：归上游的文献采集脚本，不在本 skill 范围；本 skill 处理已经落到 vault 里的 PDF
- **未来 笔记模板**：等用户定下来后，写新 skill `extract-paper-note`，从本 skill 产出的 md 里提取字段

## Reference index

| 文件 | 什么时候翻 |
|---|---|
| `references/workflow-detail.md` | Step 3 派 sub-agent 前 → 看完整四块输出格式 + 命名规则 + alt text 分级 + 多 panel 写法；Step 5 聚合前 → 看 mv/替换/verify 的精确步骤 |
| `references/lessons.md` | 跑出错时 → 查 Failure modes 表对症处理；要看完整跑通的样子 → 翻文末的 Example |
