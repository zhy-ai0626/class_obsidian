# Workflow detail — ingest-lecture

主 SKILL.md 里 Step 3 / Step 4 的完整版本在这里。改 sub-agent 协议或笔记模板规则时改这份。

---

## §3b — Sub-agent "块 1/2/3 输出" 协议

每个 Agent 读 `_attachments/_pages/<page>.png` + MinerU md 对应段，**输出三块**。

### 块 1 — 逐页核对（每页一段）

```
### Slide X: [页面标题]
**MinerU 已抽**: (从 full.md 对应段落复制)
**vision 补漏**: (MinerU 漏的文字 / 公式 / callout)
**误识修正**: (公式 / 字符纠正)
**本页图表**: (描述 + 引用 hash)
```

### 块 2 — 图片重命名清单

本段所有 MinerU 抽出的图，**全部都要列**：

| 旧 hash | 新文件名 | 类型 |
|---|---|---|
| `45f8a3b9c1d2e4f5...完整 32 位` | `<CODE>_L##_p<2位页码>_<topic-slug>_<type>.jpg` | concept |

⚠️ **旧 hash 必须给完整 32 位**（从 full.md 里 `![](images/<hash>.jpg)` 直接抄），不要缩写 — 主线程要用它做精确替换。

⚠️ **页号映射**：PNG `<prefix>_pageNN.png` 中的 NN 直接 = slide N，新名前缀写 `p<NN>`。不要做任何 ±1 偏移猜测（过往 sub-agent 误以为"封面占一页 → slide=page+1"导致整批图错位 +1）。

`type` 取值：`concept` / `data` / `flow` / `formula` / `table` / `decor`

### 块 3 — 嵌入推荐清单

只列推荐度 ≥ 3：

| 新文件名 | 推荐度 | 理由 | 建议放哪个知识块 |
|---|---|---|---|
| ... | 5 | ... | ... |

推荐度尺度：5 必嵌 / 4 强烈建议 / 3 可嵌可不嵌 / 2-1 不必列。

### 纯 vision 模式（2a 失败时）

无块 2/3（没 MinerU 图），只输出块 1。

---

## §3c — 主线程聚合（mv + 同步 full.md + verify Read 三步）

收齐所有 sub-agent 报告后，**主线程做**：

### 1. 批量 mv

按"块 2 重命名清单"把 `_attachments/<pdf_stem>/images/` 下的 hash 文件名改成语义名。

### 2. 同步 full.md 图引用（❗易漏）

批量替换 `_attachments/<pdf_stem>/full.md` 里所有 `![](images/<旧 hash>.jpg)` 为 `![](images/<新语义名>.jpg)`。

**不做这一步的后果**：笔记本身没事（它用新名），但 `full.md` 在 Obsidian 里所有图全坏（指向已不存在的 hash 文件），留档的 full.md 也是坏的。

- PowerShell 实操：读 full.md 内容 → 对块 2 清单每行做 `-replace [regex]::Escape($oldHash), $newName` → 写回。
- 块 2 清单里的 hash 必须是**完整 32 位**（不是缩写），否则替换不到。

### 3. verify Read

对"块 3"中**推荐度 ≥ 4** 的图，Read 一次亲眼看 — 确认 sub-agent 描述准、值得嵌。每张图打三种 verdict：

- **VERIFIED 嵌入** — 进笔记
- **VERIFIED 跳过** — 不进笔记（sub-agent 推荐度高估）
- **追加嵌入** — sub-agent 没推荐但 Read 时发现值得嵌

---

## §4 — 笔记生成模板规则

按 `${CLAUDE_PLUGIN_ROOT}/skills/ingest-lecture/assets/lecture-topic.md` 模板填。

### frontmatter

按模板字段写（`lecture: L##`）。

### 知识结构图

Mermaid 图展示本讲核心概念关系。

### 知识块

**按逻辑主题组织，不按 slide 编号**。

- 每个知识块 = 一个独立可理解的知识点
- 公式用 LaTeX + 一行中文解读
- **目标读者 = 高中毕业生**，笔记要脱离 PPT 后独立可读

### 术语定义

首次术语必须就地定义 1-2 句（若 PPT 没解释）。

### 图片嵌入

`![[file.png]]` 紧跟知识块，有信息量加一句 `> 说明`。

### 内容层次

- PPT 原文 → 折叠在末尾 `> [!info]-` callout
- AI 解释 → 正文知识块，无标记
- AI 延伸 → `> [!tip] 延伸(非 PPT 内容)` callout

### 疑问

3-5 个具体可操作的问题，放 `## 我的疑问` 段。
