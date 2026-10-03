---
name: ingest-lecture
description: 把一份 lecture 材料（.pptx/.pdf/截图/文本）整理成知识块组织的课程笔记,写入课程文件夹 <COURSE_ROOT>/L##.md,并更新 index.md 和 manifest.md。只要用户提到"整理这节课 / 处理这份 PPT / 把 slides 变成笔记 / ingest lecture / process slides",或附上课程 PPT/PDF 要做笔记,就用本 skill,即使没说"ingest"。用户说"生成完整 index / 结课整理 index / 升级 MOC"也用本 skill（走 §结课 MOC 升级独立入口,不跑常规步骤）。不要用于:tutorial/习题（→ ingest-tutorial）、科研论文（→ ingest-paper）、要交的作业报告（→ chemeng-coursework plugin）。
---

# Skill: ingest-lecture

## Role

把一份 lecture 材料(PPT / PDF / 截图 / 文本)转成**一份**知识块组织
的 markdown 笔记。**不**逐 slide 镜像。

**目标：笔记能替代一次补课。** 用户上课常常没听懂，笔记是学习材料，不是 PPT 转录。
**讲透优先**：在"不歪曲课件事实"的前提下，讲解越透越好（标准见 `references/workflow-detail.md` §4「讲透标准」）。

## When to trigger

- "整理这份 lecture" / "处理这节课" / "把这份 ppt 变成笔记"
- 用户附 `.pptx` / `.pdf` / 截图 / 课程文本
- "生成完整 index" / "结课整理 index" / "升级 MOC" → **跳过 Step 1-7，走文末 §结课 MOC 升级**

不应触发:tutorial(走 ingest-tutorial)/ 模糊"summarize this"(先问)。

## Inputs

- Lecture 材料(PPT / PDF / 文本 / 图片)
- **课程代码** + **周次** + **lecture 编号**(缺则问一次,不猜)
- **COURSE_ROOT**:课程文件夹。用户给了路径就用它(可以在桌面等任意位置);没给时默认 vault 下 `01_Projects/<CODE>_课名/`
- 可选:日期 / 标题

## Outputs

1. `<COURSE_ROOT>/L##_topic_snake.md`(1 个文件)
2. 更新 `<COURSE_ROOT>/index.md`(MOC,增量追加 Week 段落)

## Dependencies

启动时读:
- `${CLAUDE_PLUGIN_ROOT}/skills/ingest-lecture/assets/lecture-topic.md`(笔记模板)
- `${CLAUDE_PLUGIN_ROOT}/skills/ingest-lecture/assets/index-moc.md`(index.md 三阶段模板:桩 / Week 追加 / 结课完整 MOC)
- `<COURSE_ROOT>/index.md`(MOC,若存在)

工具:
- `${CLAUDE_PLUGIN_ROOT}/shared/scripts/mineru_extract.py`(PDF → markdown + images,用 MinerU API)
- `${CLAUDE_PLUGIN_ROOT}/shared/scripts/extract_images.py`(逐页 PNG 渲染,供 vision 核对;PPT 也用)
- **平台与路径**:命令按 macOS / Linux 写(`python3`、POSIX shell);Windows 把 `python3` 换成 `py`。
  `${CLAUDE_PLUGIN_ROOT}` 只在 Claude Code 里有值;Codex 等其他环境 = 本 SKILL.md 所在目录往上两级(插件根,含 `shared/`)
- `.env` 含 `MINERU_API_TOKEN`(.gitignored,从 https://mineru.net/apiManage/token 申请)

## Workflow

### Step 1: 加载上下文

1. 检查 `<COURSE_ROOT>/` 是否存在;若不存在,**问用户**
   课程名 + 学期,创建文件夹 + 桩 `index.md`(按 `assets/index-moc.md` **阶段①**格式)。
2. 读 MOC 看历史(domain_tags / 之前的 Week)。
3. 加载 `${CLAUDE_PLUGIN_ROOT}/skills/ingest-lecture/assets/lecture-topic.md`。
4. **Read `manifest.md`(若存在)** —— 看 Lectures 段是否有本次要处理的 PDF 那行(下次 Step 6.5 要更新它)。若整份 manifest 不存在,**不强制建**,只在 Step 7 报告里提示用户考虑建一份。

### Step 1.5: 归档原始材料(PDF / PPT)

把原始 PDF/PPT 集中复制到 `_attachments/source/` 一份,以后回溯方便:

```bash
mkdir -p "<COURSE_ROOT>/_attachments/source/"
cp "<source_path>" "<COURSE_ROOT>/_attachments/source/"
```

- **保留原文件名**(不要改成 source.pdf)
- 文本 / 截图输入跳过这一步
- 已被 `.gitignore` 排除 `*.pdf` `*.pptx` `*.ppt`,**不会进 git**(vault 体积不爆)
- `source/` 只放原文;MinerU 抽出来的 markdown 和图仍然落在 `_attachments/<stem>/` 子文件夹里

### Step 2: PDF/PPT 处理(MinerU 优先 + vision 兜底)

#### 2a: PDF — 用 MinerU API 抽 markdown(基础底稿)

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/shared/scripts/mineru_extract.py "<pdf_path>" "<COURSE_ROOT>/_attachments/" --model vlm
```

输出:
- `_attachments/<pdf_stem>/full.md` — MinerU 抽的 markdown(含公式 + 表格)
- `_attachments/<pdf_stem>/images/*.jpg` — MinerU 抽出的图片

如果 MinerU 失败(token 过期 / 配额超 / 超时 / 网络),**fallback 到纯 vision 模式**(跳过 2a,只跑 2b)。

#### 2b: 逐页渲染 PNG(供 vision 核对;PPT 唯一处理方式)

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/shared/scripts/extract_images.py "<source>" "<COURSE_ROOT>/_attachments/_pages/" --prefix <CODE>_L## --pages --dpi 150
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

收齐所有 sub-agent 报告后,主线程做三件事:**1) 批量 mv 图片**（mv 必须主线程做——sub-agent 的 Bash 写操作会被沙箱拒）、**2) 同步 full.md 图引用**（❗易漏）、**3) verify Read 推荐度 ≥ 4 的图**。详细步骤(Python 脚本,跨平台) + verdict 分类 → 见 `references/workflow-detail.md` §3c。

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
- **讲透自检**(逐个知识块):
  - 有"一句话直觉"吗?有"为什么需要"吗?
  - 每个公式 / 数量级有代入数字吗?每个过程有 walk-through 吗?
  - 新手最容易错的点有 `[!warning] 常见坑` 吗?
  - grep 正文免责语(`未展开|未说明|不能读成|不能当作|不补|没有给出`)——应为 0,命中就改成讲解或移到疑问
  - 报告 `讲透自检: N/N 知识块达标`,不达标的列出来补写后再报告
- **讲解核查**(讲透自检只查"有没有",这一步查"对不对"):
  按页码把笔记分 2-4 段(和 Step 3b 同样的分段),每段派一个**只读** sub-agent,
  对照该段 `_pages/` 里的 PNG 原图逐条核两类问题——
  1. **与课件不符**:笔记说"课件说 X"、引用 `(p.N)`、数字 / 年份 / 例子 / 定义,原页不是这样
  2. **讲解技术错误**:直觉、类比、例子、计算、常见坑、自测答案本身错误或误导新手(按该学科标准教材口径)
  主线程逐条复核后修正;报告 `讲解核查: X 页 / 发现 N 条 / 已修 N 条`。
  不支持 sub-agent 的环境由主线程分段自己核。**必须在 Step 5.5 删 PNG 之前做。**
- **Tutorial 反向校验**(若同目录有对应 `T##*.md`):
  1. Glob `<COURSE_ROOT>/T*.md`,挑出 frontmatter `related:`
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
rm -rf <COURSE_ROOT>/_attachments/_pages/
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

若 `<COURSE_ROOT>/manifest.md` 存在:

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
**讲透自检**: N/N 知识块达标(正文免责语 0 处)
**讲解核查**: X 页 / 发现 N 条 / 已修 N 条
**图片**: N 张嵌入
**疑问汇总**:
- (笔记里的疑问)
```

## §结课 MOC 升级(独立入口)

用户明说"生成完整 index / 结课整理 index / 升级 MOC"时走这里(不跑 Step 1-7):

1. Glob `<COURSE_ROOT>/L*.md` + `T*.md`,确认 lecture 齐了(缺很多就提醒用户,问要不要继续)
2. Read 全部 L##(至少读每份的标题层级 + 核心公式段)+ 现有 index.md 的各 Week 疑问段
3. 按 `assets/index-moc.md` **阶段③** 的 10 段结构**整体重写** index.md
   (这是唯一允许重写 index 的场合)
4. 写完报告:Phase 划分 / 覆盖 lecture 数 / 疑问汇总条数,让用户审

## Rules

1. **讲透优先** — 每个知识块按 §4「讲透标准」写：先直觉、讲动机、公式代入算、过程走一遍、易混对比、常见坑。长度由理解难度决定，**不由 slide 字数决定**
2. **不歪曲课件事实** — 课件里的数据 / 公式 / 定义 / 例子必须与原件一致;不把课件没说的内容说成"课件说"。这是唯一的准确性红线——**老师式讲解(直觉 / 例子 / 类比 / 补全课件只点名没解释的术语)不属于编造**,直接写正文,不加标记
3. **延伸 callout 只放超范围内容** — `> [!tip] 延伸(非 PPT 内容)` 只用于后续章节 / 课外的新知识点,不用来装本讲的讲解
4. **正文不写免责语** — 不写"原页未展开 / 不能读成 / 本页未说明"之类;能讲清就讲清,真存疑放 `## 我的疑问`
5. **课件有错或过时,保留原说法 + 一句纠正** — 例:"1970 ALOHAnet(课件写作 satellite network;教材通行说法是连接各岛的无线电分组网)"。这是讲解,不是免责语;不要默默照抄错误,也不要默默改掉课件
6. **页码引用必须核实** — 写 `(p.N)` 前确认该页确有此内容;一条信息跨页时写全页码(`p.41、p.44`)
7. **MOC 更新 append-only** — 不改已有 Week 段落(唯一例外:§结课 MOC 升级是显式整体重写)
8. **质量核查服务于笔记,不喧宾夺主** — 用 skill 自带脚本;不额外自建 QA 脚本 / 报告体系,核查结果只写进 Step 7 报告

## Reference index

| 文件 | 何时翻 |
|---|---|
| `assets/lecture-topic.md` | Step 4 写 L## 笔记时的模板 |
| `assets/index-moc.md` | 一切 index.md 操作:Step 1 建桩(阶段①)/ Step 6 追加 Week(阶段②)/ §结课 MOC 升级(阶段③) |
| `../../shared/assets/manifest-example.md` | 给课程新建 manifest.md 时照抄 |
| `references/workflow-detail.md` | 改 sub-agent 协议（§3b 块 1/2/3 字段）/ 主线程聚合三步细节（§3c）/ 笔记模板规则（§4 frontmatter / 知识块 / 术语 / 图片嵌入 / 内容层次） |
| `references/lessons.md` | 遇到怪现象先查 Failure modes 表 / 写笔记前看 Good 示例对齐风格 |
