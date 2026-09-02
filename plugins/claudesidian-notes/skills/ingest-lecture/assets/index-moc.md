# index.md 模板（课程 MOC）

> 这文件给 LLM 看：生成 / 更新任何课程的 `index.md` 时按这里的格式，不要去翻别的课程抄。

index.md 的一生分三个阶段：

| 阶段 | 什么时候 | 谁做 |
|---|---|---|
| ① 桩 | 新建课程文件夹时 | ingest-lecture Step 1 |
| ② Week 追加 | 每处理完一节 lecture | ingest-lecture Step 6 |
| ③ 结课完整 MOC | 用户说"生成完整 index / 结课整理 index / 升级 MOC" | ingest-lecture §结课 MOC 升级 |

---

## 阶段 ①：桩（新建课程时写这个）

```markdown
---
type: course-moc
course: CMEXXX
title_en: Course Name
title_zh: 课名
semester: YYYY-Spring
tags:
  - 化工
  - 课名
  - 课程笔记
  - 主笔记
  - MOC
last_updated: YYYY-MM-DD
---

# 📘 **CMEXXX · 课名** · 主笔记

> Course Name · 一句话课程定位
> 讲师：（问用户或留空）

> [!info] 关于这份笔记
> 整门课的**主索引（MOC）**。上课期间按周追加；结课后升级成完整版（知识地图 + 决策树）。

## 按周索引

<!-- ingest-lecture 每次处理完一节课，在这行下面追加一个 Week 段 -->
```

---

## 阶段 ②：Week 追加块（每节课处理完追加一个）

```markdown
## Week {{N}}

{{一两句概要：这周讲了什么}}

- [[L##_topic_snake]]

**本周疑问**:
- （汇总笔记里的 1-3 个关键疑问）
```

规则：**append-only** —— 只在文件末尾追加，不改已有 Week 段、不修 frontmatter。

---

## 阶段 ③：结课完整 MOC（显式触发才做）

用户明说"生成完整 index / 结课整理 index / 升级 MOC"时，**整体重写** index.md
（这是唯一允许重写的场合，append-only 规则不适用）。前提：全部 L##（最好还有 T##）已生成。

### 结构（按顺序，10 段）

1. **frontmatter** — 同阶段 ①
2. **标题 + [!info] callout** — 说明"这是主索引，详细推导在子笔记里，点 [[链接]] 跳转"
3. **🗺️ 知识地图** — 一个 mermaid flowchart：课程分 3-5 个 Phase（阶段），每个 Phase 下挂对应 lecture 节点，Phase 配不同底色
4. **📌 全课速览** — 每个 Phase 一行 checkbox，一句话概括；加一段 Tutorial 清单
5. **正文按 Phase 分章** — 每个知识点一小节（格式见下方示例）
6. **🧪 Tutorial 对照表** — 每份 tutorial 配哪节 lecture、考什么重点
7. **课程总复盘** — 核心收获 TOP 5 + 一个"拿到题怎么开始"的 mermaid 决策树 + 量级校验表（算出来差几个数量级该查错）
8. **我现在最想搞清楚的点** — 把各 Week 段的"本周疑问"汇总分组（答疑时用），汇总后原 Week 段可删
9. **必看资料清单 + 课程收尾清单** — 课本 / 手册 / 考试范围 checkbox
10. **🔗 所有 lecture 一览表** — 列：序号 / [[wikilink]] / 难度⭐ / 复习状态☐

### 正文小节格式（第 5 段的最小单元）

每个知识点一小节，包含：大白话核心思想（1-3 句）→ 核心公式（最重要的加 `\boxed{}`）→ 能列表的列表格 → 末尾 [!example] callout 跳子笔记。示例：

```markdown
## 1.2 Fick 第一定律 + 总通量公式 ⭐⭐⭐

**Fick 第一定律**（扩散通量 ∝ 浓度梯度）：

$$J_A = -D_{AB}\,\frac{dc_A}{dz}$$

工程里 A 不光扩散还被对流推着走，加对流项 → **总通量公式（整门课最核心一行）**：

$$\boxed{\;N_A = -c\,D_{AB}\,\nabla y_A + y_A\,(N_A + N_B)\;}$$

| 项 | 含义 |
|---|---|
| 第一项 | 扩散贡献（Fick） |
| 第二项 | 对流贡献 |

> [!example] 🔗 深入了解
> **Fick 推导 + 总通量公式 + 浓度速度换算速查** → [[L02_diffusive_mass_transfer]]
```

### 硬规则

- 所有跳转用 wikilink `[[文件名]]`（不带 .md），**文件名必须和目录里实际文件完全一致**（写之前 Glob 核对）
- 内容只来自已有的 L## / T## 笔记，**不编造公式或数据**；笔记里没有的不写
- 这是"读薄"的索引：每个知识点只放最核心的 1-2 个公式 + 判断方法，细节留给子笔记
- 重要程度用 ⭐（1-4 颗），语言中文为主、术语保留英文
- 写完报告：Phase 划分 / 覆盖的 lecture 数 / 疑问汇总条数，让用户审
