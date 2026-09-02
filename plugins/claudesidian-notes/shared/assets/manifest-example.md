# manifest.md 模板（原始材料清单）

> 这文件给 LLM 看：给某门课新建 `manifest.md` 时照这个抄，把示例行换成该课实际的 PDF。
> 不要去翻别的课程的 manifest 抄格式。

三张表 + 修改记录，缺哪类材料就删哪张表。**状态标记**：`✅` 已完成 / `⏳` 进行中 / `–` 未做或不需要。

```markdown
---
type: manifest
course: CMEXXX
title: "CMEXXX 课名 — 原始材料 Manifest"
last_updated: YYYY-MM-DD
---

# CMEXXX 课名 — 原始材料 Manifest

这门课所有原始 PDF 在 `_attachments/source/`。本文件追踪每份的 **类型 / MinerU 处理 / 笔记产出 / AI 可读索引路径**。

> [!tip] 这文件给谁看
> - **你**：扫一眼知道哪些 PDF 该 MinerU、哪个还没写笔记
> - **AI/skill**：启动时读这个，从 References 段拿 "MinerU 索引" 路径，做题时直接 grep 查物性
>
> **不要手改 MinerU/笔记列的状态** —— ingest-lecture / ingest-tutorial 跑完会自动更新。手动只在新加 PDF 时往表里补一行。

**状态标记**：`✅` 已完成 / `⏳` 进行中 / `–` 未做或不需要

---

## Lectures (N 份)

| PDF (in `source/`) | MinerU 索引 | 笔记 |
|---|---|---|
| `L1 xxx.pdf` | ✅ `_attachments/L1 xxx/full.md` | ✅ [[L01_topic_snake]] |
| `L2 xxx.pdf` | – | – |

---

## Tutorials (N 份)

> Tutorial 默认不跑 MinerU（题面 vision 直读够用）。若某份含**大型物性表**或**公式密集**，可例外跑一次并填"MinerU 索引"列。

| PDF (in `source/`) | MinerU 索引 | 笔记 |
|---|---|---|
| `Tutorial #1.pdf` | – | ✅ [[T01_topic_snake]] |

---

## References (N 份)

> 这一段是 **ingest-tutorial Step 1.6 自动读的来源**。只有标了 "MinerU 索引" 路径的资料才会被 skill grep。Type 字段给 skill 提示数据类型：

| PDF (in `source/`) | Type | MinerU 索引 | 用途 |
|---|---|---|---|
| `Appendix B xxx.pdf` | physprop | ✅ `_attachments/Appendix B xxx/full.md` | 什么场景查它（一句话） |
| `Table A1 xxx.pdf` | unitconv | – | 单位换算时查 |

**Type 取值**：
- `physprop` — 物性数据（Cp、ΔH、蒸汽表、Antoine 等），做题时常 grep
- `unitconv` — 单位换算表
- `textbook` — 教材章节原文
- `handbook` — 工程手册类
- `syllabus` — 课程大纲
- `external` — 外部参考（规范、SDG 等）

---

## 修改记录

- YYYY-MM-DD: 初始化

<!-- 每次 skill 更新本文件时，在这里追加一行 "YYYY-MM-DD: <skill 名> 更新 <PDF 名> 的 X 列" -->
```
