---
name: distill-principles
description: 把一门课的所有 lecture 笔记蒸馏成一份"第一原理 + 推导树 + 公式索引"总览（_principles.md），按守恒 / 公理 → 派生公式组织。Triggers - "蒸馏 CMEXXX" / "把 XXX 课读薄" / "做 XXX 的原理图谱" / "distill principles" / "生成 XXX 的 _principles"。
---

# Skill: distill-principles

## Role

把一门课所有 L## 笔记里 30-60 个公式压成一份**教科书风格**的"原理 → 推导树 → 公式索引"，让用户上完课不忘 / 期末复习只看一份 / 考场忘了公式能从原理现场推。

**目标读者**：本科生（编程入门级读者），不是教授。

## When to trigger

- "蒸馏 / distill CMEXXX" / "把这门课读薄" / "做 CMEXXX 的 _principles"

不应触发：整理单节课（→ ingest-lecture）/ 做习题（→ ingest-tutorial）

## Inputs / Outputs

- **In**：课程代码 + 课名（缺则问一次）；该课程 L01-L1N lecture 笔记；可选 Formula Sheet / Appendix
- **Out**：`01_Projects/<CODE>_课名/_principles.md`（200-400 行）

## Dependencies

启动读：`L*.md`、`manifest.md`（若存在）、`manifest.md` References 段标 ✅ 的资料

## Workflow

### Step 1: Glob lecture + manifest

`Glob L*.md`，统计 lecture 数。Read `manifest.md`。

⚠️ **不要只看 revision / 速查卡节** — 必须 Step 1.5 全文扫公式。

### Step 1.5: 全 lecture 强制扫公式 — **关键步骤**

跑脚本自动提取所有公式 + tutorial 速查表：

```bash
python ${CLAUDE_PLUGIN_ROOT}/shared/scripts/extract_formulas.py <CODE>
```

脚本会输出整门课所有 lecture 的 `$$ ... $$` 公式块（含 L## + 行号）+ 所有 tutorial 的"本次公式速查"段。LLM 在此基础上判断哪些进 _principles。

**详细做法 + CME222 教训** → `references/workflow-detail.md §Step 1.5`

### Step 1.6: 读已有 tutorial 公式速查表

Glob `T*.md`。每个 tutorial 的 `## 本次公式速查` 段 → 加到大清单"tutorial 实际用到"列。

### Step 2: 识别根本起点（3-5 条守恒 / 公理）

**判断标准 + 各课程类型起点参考表** → `references/workflow-detail.md §Step 2`

### Step 3: 构建推导树 → 线性化成 §1 → §N

把所有公式按"原理 → 假设 → 派生"组织成树，线性化成章节序列。每章公式带连续编号 (X.Y)。

**线性化原则** → `references/workflow-detail.md §Step 3`

### Step 4: 写入模板（教科书风格）

按 `assets/template.md` 的完整文件结构（frontmatter + Nomenclature 三表 + §1-§N + 公式索引）。

**风格规则 + Good/Bad 例子** → `references/style-guide.md`

### Step 5: 符号说明编制（Roman / Greek / 下标，双语）

**多义 / 易混符号标注规则** → `references/workflow-detail.md §Step 5`

### Step 6: 自检（跑脚本自动校验）

```bash
python ${CLAUDE_PLUGIN_ROOT}/shared/scripts/validate_principles.py 01_Projects/<CODE>_课名/_principles.md
```

脚本自动检查:
- 公式编号 `\tag{X.Y}` 连续无跳号
- 跨节引用 `(X.Y)` 都对应已定义的公式
- 文件长度 200-400 行
- 没有 callout（教科书风格禁用）

退出码 0 = 通过；1 = 有问题，按输出修。**手工 checklist** → `references/workflow-detail.md §Step 6`

### Step 7: 报告

```markdown
## Distill complete: <CODE>
**文件**: [[_principles]]
**覆盖**: L01-L1N 全部 N 节
**根本起点**: M 条
**公式总数**: K 个（(1.1) → (N+1.X)）
**符号表**: Roman X / Greek Y / 下标 Z
**文件长度**: ~XXX 行
**需要用户审阅**: (1) 根本起点选对吗？(2) 推导树合理吗？(3) 哪些故意没进 _principles？
**评分预期**: 8.5-9.5/10
```

## Rules（硬规则）

1. **目标读者 = 本科生**，不是教授。任何"显然 / 略"步骤都展开
2. **不重推 lecture 物理意义** — 只展示"假设 + 数学化简"的推导链
3. **教科书风格优先严谨 + 简洁**，新人友好性由"常见错"+ 物理意义短句满足
4. **不修原 L## 笔记** — 只读不动

## 文件目录索引

### `assets/`（素材）

| 文件 | 用 |
|---|---|
| `assets/template.md` | `_principles.md` 完整结构模板 + 符号表 schema + 编号约定。Step 4 写文件时按这个 |

### `../../shared/scripts/`（plugin 共享，LLM 用 Bash 调用）

| 脚本 | 何时跑 | 输出 |
|---|---|---|
| `extract_formulas.py <CODE>` | **Step 1.5**（治 CME222-bug 关键）| 整门课所有 L## 的 `$$ ... $$` 公式块 + 所有 T## 公式速查表 |
| `validate_principles.py <path>` | **Step 6** 自检 | 检查编号连续 / 跨节引用 / 长度 / 无 callout，输出问题清单 |
| `reverse_audit.py <tutorial.md>` | 给 `ingest-tutorial` Step 7.6 调用 | 扫 tutorial 引用 `(X.Y)` + ⚠️ 缺标记，跟 _principles 对账 |

### `references/`（按需读的规范）

| 文件 | 看什么 |
|---|---|
| `references/style-guide.md` | 教科书风格硬规则 + Good/Bad 例子 + "常见错" blockquote 规则 |
| `references/workflow-detail.md` | 每个 Step 的具体操作 + 判断标准 + 检查 checklist |
| `references/lessons.md` | CME213 v1→v4 迭代教训 + CME222 17 bug 经验 + Failure modes + Example flow |
