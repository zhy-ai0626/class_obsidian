---
name: ingest-lecture
description: 把一份 lecture 材料（.pptx/.pdf/截图/文本）整理成知识块组织的课程笔记,写入 01_Projects/<CODE>_课名/L##.md,并更新 index.md 和 manifest.md。只要用户提到"整理这节课 / 处理这份 PPT / 把 slides 变成笔记 / ingest lecture / process slides",或附上课程 PPT/PDF 要做笔记,就用本 skill,即使没说"ingest"。用户说"生成完整 index / 结课整理 index / 升级 MOC"也用本 skill（走 §结课 MOC 升级独立入口,不跑常规步骤）。不要用于:tutorial/习题（→ ingest-tutorial）、科研论文（→ ingest-paper）、要交的作业报告（→ chemeng-coursework plugin）。
---

# Skill: ingest-lecture

## Role

把一份 lecture 材料(PPT / PDF / 截图 / 文本)转成**一份**知识块组织
的 markdown 笔记。**不**逐 slide 镜像。用户会审,准确性优先于 polish。

## When to trigger

- "整理这份 lecture" / "处理这节课" / "把这份 ppt 变成笔记"
- 用户附 `.pptx` / `.pdf` / 截图 / 课程文本
- "生成完整 index" / "结课整理 index" / "升级 MOC" → **跳过 Step 1-7，走文末 §结课 MOC 升级**

不应触发:tutorial(走 ingest-tutorial)/ 模糊"summarize this"(先问)。

## Inputs

- Lecture 材料(PPT / PDF / 文本 / 图片)
- **课程代码** + **周次** + **lecture 编号**(缺则问一次,不猜)
- 可选:日期 / 标题

## Outputs

1. `01_Projects/<CODE>_课名/L##_topic_snake.md`(1 个文件)
2. 更新 `01_Projects/<CODE>_课名/index.md`(MOC,增量追加 Week 段落)

## Dependencies

启动时读:
- `${CLAUDE_PLUGIN_ROOT}/skills/ingest-lecture/assets/lecture-topic.md`(笔记模板)
- `${CLAUDE_PLUGIN_ROOT}/skills/ingest-lecture/assets/index-moc.md`(index.md 三阶段模板:桩 / Week 追加 / 结课完整 MOC)
- `01_Projects/<CODE>_课名/index.md`(MOC,若存在)

工具:
- `${CLAUDE_PLUGIN_ROOT}/shared/scripts/mineru_extract.py`(PDF → markdown + images,用 MinerU API)
- `${CLAUDE_PLUGIN_ROOT}/shared/scripts/extract_images.py`(逐页 PNG 渲染,供 vision 核对;PPT 也用)
- `.env` 含 `MINERU_API_TOKEN`(.gitignored,从 https://mineru.net/apiManage/token 申请)

## Workflow

### Step 1: 加载上下文

1. 检查 `01_Projects/<CODE>_课名/` 是否存在;若不存在,**问用户**
   课程名 + 学期,创建文件夹 + 桩 `index.md`(按 `assets/index-moc.md` **阶段①**格式)。
2. 读 MOC 看历史(domain_tags / 之前的 Week)。
3. 加载 `${CLAUDE_PLUGIN_ROOT}/skills/ingest-lecture/assets/lecture-topic.md`。
4. **Read `manifest.md`(若存在)** —— 看 Lectures 段是否有本次要处理的 PDF 那行(下次 Step 6.5 要更新它)。若整份 manifest 不存在,**不强制建**,只在 Step 7 报告里提示用户考虑建一份。

### Step 1.5: 归档原始材料(PDF / PPT)

把原始 PDF/PPT 集中复制到 `_attachments/source/` 一份,以后回溯方便:

```bash
mkdir -p "01_Projects/<CODE>_课名/_attachments/source/"
cp "<source_path>" "01_Projects/<CODE>_课名/_attachments/source/"
```

- **保留原文件名**(不要改成 source.pdf)
- 文本 / 截图输入跳过这一步
- 已被 `.gitignore` 排除 `*.pdf` `*.pptx` `*.ppt`,**不会进 git**(vault 体积不爆)
- `source/` 只放原文;MinerU 抽出来的 markdown 和图仍然落在 `_attachments/<stem>/` 子文件夹里

### Step 2: PDF/PPT 处理(MinerU 优先 + vision 兜底)

#### 2a: PDF — 用 MinerU API 抽 markdown(基础底稿)

```bash
py ${CLAUDE_PLUGIN_ROOT}/shared/scripts/mineru_extract.py "<pdf_path>" "01_Projects/<CODE>_课名/_attachments/" --model vlm
```

输出:
- `_attachments/<pdf_stem>/full.md` — MinerU 抽的 markdown(含公式 + 表格)
- `_attachments/<pdf_stem>/images/*.jpg` — MinerU 抽出的图片

如果 MinerU 失败(token 过期 / 配额超 / 超时 / 网络),**fallback 到纯 vision 模式**(跳过 2a,只跑 2b)。

#### 2b: 逐页渲染 PNG(供 vision 核对;PPT 唯一处理方式)

```bash
py ${CLAUDE_PLUGIN_ROOT}/shared/scripts/extract_images.py "<source>" "01_Projects/<CODE>_课名/_attachments/_pages/" --prefix <CODE>_L## --pages --dpi 150
```

**PDF 也跑 2b**(供 vision 对照 MinerU 结果,补 MinerU 漏抽的内容)。
**PPT 直接走 2b**(MinerU 不支持 .pptx)。
文本 / 截图跳过整个 Step 2。

### Step 3: 提取 + 核对(MinerU 底稿 + vision 补漏 + 图片描述)

#### 3a: 读 MinerU markdown(若 PDF + 2a 成功)

Read `_attachments/<pdf_stem>/full.md`,作为内容基础底稿。

#### 3b: vision 核对 + 图片重命名 + 嵌入推荐(sub-agent 三块输出)

启动多个 sub-agent 并行,每个负责一段页码:

| PDF 页数 | Agent 数 | 每个 Agent 负责 |
|---|---|---|
| ≤15 页 | 2 个 | 6-8 页 |
| 16-40 页 | 3 个 | 8-13 页 |
| >40 页 | 4 个 | 10-15 页 |

每个 Agent 输出 **块 1（逐页核对）+ 块 2（图片重命名清单）+ 块 3（嵌入推荐清单）**。完整字段、表格列、推荐度尺度、纯 vision 模式 fallback → 见 `references/workflow-detail.md` §3b。

#### 3c: 主线程聚合(批量 mv + 同步 full.md + verify Read)

收齐所有 sub-agent 报告后,主线程做三件事:**1) 批量 mv 图片**（mv 必须主线程做——sub-agent 的 Bash 写操作会被沙箱拒）、**2) 同步 full.md 图引用**（❗易漏）、**3) verify Read 推荐度 ≥ 4 的图**。详细 PowerShell 步骤 + verdict 分类 → 见 `references/workflow-detail.md` §3c。

#### 3d: 覆盖率确认

每页 slide 都必须在块 1 里出现。缺失就 Read 补读。

### Step 4: 生成笔记

**先看目标 `L##_<topic>.md` 是否已存在且非空**(增量 vs 重写决策):

- **已存在且非空**:
  1. Read 旧版列章节清单
  2. **优先 Edit 增量改动**(加图、修 OCR 错、补漏)— **不 Write 重写**
  3. 仅在用户明确说"重写"或旧版质量不可接受时才 Write
  4. Write 前列「v2 章节 vs v1 章节」对照清单,**v2 章节数 ≥ v1 章节数**
- **不存在或空**:按 `${CLAUDE_PLUGIN_ROOT}/skills/ingest-lecture/assets/lecture-topic.md` 模板从零写。

模板字段含义、知识块/术语/图片嵌入/内容层次的完整规则 → 见 `references/workflow-detail.md` §4。

### Step 5: 自检

- **slide 覆盖率**:每页核心信息是否在某知识块?未覆盖标"跳过(装饰
  /过渡)"或补充。报告 `Slides 覆盖: 18/20`。
- **术语自洽**:首次术语是否已定义?未定义补完。
- **Tutorial 反向校验**(若同目录有对应 `T##*.md`):
  1. Glob `01_Projects/<CODE>_课名/T*.md`,挑出 frontmatter `related:`
     字段含 `[[L##_*]]`(当前 lecture)的 tutorial 文件。无则跳过这条。
  2. 对每个匹配的 tutorial,收集它引用的知识点(两代格式都支持):
     - **新规范**:grep tutorial 里所有 `(X.Y)` 公式编号 → Read `_principles.md`
       找到对应 `\tag{X.Y}` 公式,看该公式在 _principles 里标注的来源 lecture
       是否为当前 L##;是 → 该公式进校验清单
     - **老规范兜底**:grep 该 tutorial 全文 `[[L##_*]]`(公式速查来源列 +
       各题 wiki link),收所有指回当前 L## 的概念 / 术语
     - 两路都空 → 报告里写"反向校验: 该 tutorial 未引用本讲内容(或格式无法
       识别)",**不要报 N/N 通过**
  3. 对每条公式/术语,在新生成的 L## 笔记里 grep 同名公式 / 术语 /
     wiki link(`[[术语]]`)。**找不到 = 缺漏**。
  4. 报告 `Tutorial 反向校验: N/N 命中` — 若有缺漏,列出缺哪些 +
     建议在哪个知识块补,**让用户决定是否补**(不要擅自加,避免动到用户
     已审阅过的内容)。
  5. 若当前 L## 是新讲(对应 T## 还没生成),跳过这条,Step 7 报告里提示
     "T## 生成后建议回头跑一次反向校验"。

### Step 5.5: 清理临时页

**必须在 Step 5 自检通过后才删**——自检发现缺页时要回来 Read 对应 PNG 补读。

```bash
# 清理逐页 PNG(供 vision 用,自检通过后不再需要)
rm -rf 01_Projects/<CODE>_课名/_attachments/_pages/
```

**保留** `_attachments/<pdf_stem>/`(MinerU 抽的 markdown + 已重命名的图,这是图片唯一存档)。

### Step 6: 增量 MOC 更新

`index.md` **追加** Week 段落(不改已有;格式 = `assets/index-moc.md` **阶段②**):

```markdown
## Week {{WEEK}}

{{一两句概要}}

- [[L##_topic_snake]]

**本周疑问**:
- (汇总笔记里的 1-3 个关键疑问)
```

**Append-only**:不修改已有 Week 段落。

### Step 6.5: 更新 manifest.md(若存在)

若 `01_Projects/<CODE>_课名/manifest.md` 存在:

1. 在 **Lectures 段**找对应 PDF 文件名那行(按第一列 `<PDF 名>` 匹配)
   - **找到该行** → Edit 那一行:
     - "MinerU 索引" 列改为 `✅ _attachments/<pdf_stem>/full.md`
     - "笔记" 列改为 `✅ [[L##_topic_snake]]`
   - **没找到该行**(用户没在 manifest 预登记) → 在 Lectures 表末尾**追加新行**
2. 在文件末尾"修改记录"段追加一行:`YYYY-MM-DD: ingest-lecture 更新 <PDF 文件名>`

若 manifest.md **不存在**:跳过本步,Step 7 报告里提示用户"考虑建 manifest.md 跟踪状态"——用户点头就按 `${CLAUDE_PLUGIN_ROOT}/shared/assets/manifest-example.md` 模板建。

⚠️ **只动你刚处理的那一行 + 修改记录段**。不要碰其他课程笔记的行,不要重排表格,不要改 Tutorials / References 段。

### Step 7: 报告

```markdown
## Ingestion complete: <CODE> Week ## L##

**笔记**: [[L##_topic_snake]]
**Slides 覆盖**: X/Y(跳过 Z 页:课程信息页/装饰页)
**术语自洽**: N/N(全部已定义或已链接)
**图片**: N 张嵌入
**疑问汇总**:
- (笔记里的疑问)
```

## §结课 MOC 升级(独立入口)

用户明说"生成完整 index / 结课整理 index / 升级 MOC"时走这里(不跑 Step 1-7):

1. Glob `01_Projects/<CODE>_课名/L*.md` + `T*.md`,确认 lecture 齐了(缺很多就提醒用户,问要不要继续)
2. Read 全部 L##(至少读每份的标题层级 + 核心公式段)+ 现有 index.md 的各 Week 疑问段
3. 按 `assets/index-moc.md` **阶段③** 的 10 段结构**整体重写** index.md
   (这是唯一允许重写 index 的场合)
4. 写完报告:Phase 划分 / 覆盖 lecture 数 / 疑问汇总条数,让用户审

## Rules

1. **不编造 slide 内容** — PPT 文字稀疏时写"原文未明",不要自己编
2. **解读长度匹配 slide 密度** — 一行 slide 一行解读。术语首次定义除外
3. **AI 延伸必须用 `> [!tip] 延伸(非 PPT 内容)` callout** — 不混进正文
4. **MOC 更新 append-only** — 不改已有 Week 段落(唯一例外:§结课 MOC 升级是显式整体重写)

## Reference index

| 文件 | 何时翻 |
|---|---|
| `assets/lecture-topic.md` | Step 4 写 L## 笔记时的模板 |
| `assets/index-moc.md` | 一切 index.md 操作:Step 1 建桩(阶段①)/ Step 6 追加 Week(阶段②)/ §结课 MOC 升级(阶段③) |
| `../../shared/assets/manifest-example.md` | 给课程新建 manifest.md 时照抄 |
| `references/workflow-detail.md` | 改 sub-agent 协议（§3b 块 1/2/3 字段）/ 主线程聚合三步细节（§3c）/ 笔记模板规则（§4 frontmatter / 知识块 / 术语 / 图片嵌入 / 内容层次） |
| `references/lessons.md` | 遇到怪现象先查 Failure modes 表 / 写笔记前看 Good 示例对齐风格 |
