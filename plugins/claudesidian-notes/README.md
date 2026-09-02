# claudesidian-notes

**课程笔记处理** plugin。从 PPT/tutorial → `_principles.md` 考试速查的全套流水线。

> 论文处理（`ingest-paper`）跟课程笔记是不同领域（科研 vs 课程），流程也独立，但为了打包方便一起收在本 plugin 的 `skills/ingest-paper/`。

## 4 个 Skill

| Skill | 触发 | 输入 → 输出 |
|---|---|---|
| `ingest-lecture` | "整理这节课"、"处理这份 PPT"；另有独立入口"生成完整 index / 结课整理 MOC"（见其 SKILL.md §结课 MOC 升级） | PPT/PDF → `L##.md`（知识块组织笔记）+ index.md 更新 |
| `ingest-tutorial` | "解这份 tutorial"、"做这份习题" | 题目 PDF → `T##.md`（教学质量解答 + 反向校验 `_principles`） |
| `distill-principles` | "蒸馏 CMEXXX"、"把 XXX 课读薄" | 整门课所有 `L*.md` → `_principles.md`（第一原理 + 推导树 + 公式索引） |
| `ingest-paper` | "整理这篇论文"、"ingest paper" | 论文 main + SI → `main.md` / `si.md`（vision 核对 + 图重命名） |

## 2 个 Slash Command

| Command | 用 |
|---|---|
| `/distill-all` | 扫 `01_Projects/CME*` 所有有 lecture 的课 → 批量跑 distill-principles |
| `/audit-tutorials CMEXXX` | 扫一个课所有 `T##` → 批量反向校验 `_principles` → 汇总 bug 报告 |

## 目录结构（当前实际状态）

```
claudesidian-notes/
├── .claude-plugin/plugin.json    元数据
├── README.md                      （本文件）
├── skills/
│   ├── ingest-lecture/
│   │   ├── SKILL.md               主流程入口（含 §结课 MOC 升级独立入口）
│   │   ├── assets/
│   │   │   ├── lecture-topic.md   L## 笔记模板
│   │   │   └── index-moc.md       index.md 三阶段模板（桩 / Week 追加 / 结课完整 MOC）
│   │   └── references/            workflow-detail.md + lessons.md
│   ├── ingest-tutorial/           同上结构（assets/tutorial.md）
│   ├── distill-principles/
│   │   ├── SKILL.md
│   │   ├── assets/template.md     _principles.md 完整结构模板
│   │   └── references/            workflow-detail.md + style-guide.md + lessons.md
│   └── ingest-paper/
│       ├── SKILL.md
│       └── references/            workflow-detail.md + lessons.md
├── commands/
│   ├── distill-all.md
│   └── audit-tutorials.md
└── shared/
    ├── assets/
    │   └── manifest-example.md    manifest.md 模板（两个 ingest skill 共用）
    └── scripts/                   跨 skill 共享脚本
        ├── extract_formulas.py
        ├── validate_principles.py
        ├── reverse_audit.py
        ├── mineru_extract.py      PDF → markdown（MinerU API）
        ├── mineru_convert.py      论文 main + SI 批量转换
        ├── extract_images.py      逐页 PNG 渲染（供 vision 核对）
        └── process_si.py          SI 多格式 dispatcher
```

**未来可能补充的**（按需）：
- `shared/style-guides/textbook-style.md` — 把 distill-principles 的 style-guide 抽到共享（让 4 个 skill 都引用同一份）
- `shared/schemas/formula-id.md` — (X.Y) 公式编号约定文档
- `agents/` `hooks/` — 暂未用到
- 各 skill 的 `scripts/` `assets/` `examples/` 子目录 — 按需创建，**不强求**

## 数据流（一个学期的典型使用）

```
PPT  ─┐
      ├─ ingest-lecture  ─► L01.md, L02.md, ... L##.md
PDF  ─┘                              │
                                     ▼
                            distill-principles  ─► _principles.md（公式编号 (X.Y)）
                                     ▲                  │
                                     │                  ▼
Tutorial PDF  ─► ingest-tutorial  ──┘            ingest-tutorial 引用 (X.Y)
                       │                                │
                       └── Step 7.6 reverse_audit  ◄────┘
                                  │
                                  ▼
                       bug 报告写回 T##.md + chat 提示重蒸馏
```

## 共享工具

`shared/scripts/`（**已就绪**）：

| 脚本 | 干啥 |
|---|---|
| `extract_formulas.py <CODE>` | 扫整门课所有 lecture 公式（治 distill-principles "漏抽"病） |
| `validate_principles.py <path>` | `_principles.md` 自检（编号连续 / 跨节引用 / 长度 / 无 callout） |
| `reverse_audit.py <tutorial.md>` | tutorial → `_principles` 对账（自动撞出 bug） |
| `mineru_extract.py <pdf> <outdir>` | 单份 PDF → markdown + images（MinerU API，lecture 用） |
| `mineru_convert.py --paper-dir <dir>` | 论文 main + SI 批量转换，带 batch_id 缓存断点续跑 |
| `extract_images.py <src> <outdir>` | PPT/PDF → 逐页 PNG，供 vision 核对 |
| `process_si.py <paper-folder>` | SI 多格式（pdf/docx/xlsx/zip）dispatcher |

**当前 plugin 不包含**：style-guides、schemas — 各 skill 自己的 `references/` 已经覆盖了风格规则，等真有跨 skill 重复时再抽出来。共享 assets 已有一个：`shared/assets/manifest-example.md`。

## 版本

v0.1.0 — 初始版本，4 skills 移入 plugin，shared/ 待逐步抽取
