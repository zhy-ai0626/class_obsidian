# ingest-paper — workflow detail

详细的 Step 3 vision 核对协议、alt text 分级规则、多 panel 图写法、主线程聚合步骤。SKILL.md 主流程引用本文件。

---

## Step 3 — 多 sub-agent 并行 vision 核对（完整协议）

按页数分 sub-agent（参考 lecture，论文规模相近）：

| PDF 页数 | Agent 数 | 每个 Agent 负责 |
|---|---|---|
| ≤8 页 | 2 个 | 4 页 |
| 9-15 页 | 2 个 | 6-8 页 |
| 16-30 页 | 3 个 | 8-12 页 |
| >30 页 | 4 个 | 10-15 页 |

main 和 SI **分别拆 sub-agent**（不混在一起，避免 caption 编号串位）。

每个 sub-agent 读 `_pages_<main|si>/<page>.png` + `<main|si>.md` 对应段，输出**四块**：

### 块 1 — patches（修正 main.md / si.md）

每条 patch 给：
```
{
  "file": "main.md" | "si.md",
  "anchor": "<旧文本片段，唯一可定位>",
  "new": "<修正后的文本>",
  "reason": "MinerU 漏抽 / 公式误识 / 表格结构乱 / caption 截断"
}
```

不用行号（行号易飘），用文本片段做锚点。

### 块 2 — 图重命名清单 + 分级 + alt text

```json
[
  {
    "old_hash": "45f8a3b9c1d2e4f5...完整 32 位...",
    "new_name": "fig3_stress-strain.jpg",
    "type": "data",
    "tier": "critical",
    "alt": "Stress-strain curves of 4 samples (PIBA/AM 25/50/65/80 mol%). Yield at ~5% strain. Ultimate elongation 200-800%, increasing with PIBA. Sample 65% shows highest toughness ~22 MJ/m³ — counterintuitive non-monotonic peak, authors attribute to optimal phase domain size (see fig 4 morphology, section 3.2)."
  },
  {
    "old_hash": "8a3c1e2d...",
    "new_name": "fig1_synthesis-scheme.jpg",
    "type": "schematic",
    "tier": "critical",
    "alt": "Synthesis scheme: PIBA+AM monomers + EMIM-TFSI IL (65 wt%) + HDDA crosslinker (0.5 mol%) → UV 365 nm 60s → polymerization-induced microphase separation → bicontinuous network with polymer-rich and IL-rich domains ~20-50 nm."
  },
  {
    "old_hash": "c4f2a9d1...",
    "new_name": "fig2_setup-photo.jpg",
    "type": "photo",
    "tier": "general",
    "alt": "Photo of UV-curing setup with sample mold."
  }
]
```

**命名规则**：
- main 图：`fig<编号>_<topic-slug>.<ext>` 例：`fig1_morphology-sem.jpg`
- main 表：`tab<编号>_<topic-slug>.<ext>` 例：`tab1_mechanical-data.jpg`
- SI 图：`figS<编号>_<topic-slug>.<ext>` 例：`figS1_xrd-pattern.jpg`
- SI 表：`tabS<编号>_<topic-slug>.<ext>` 例：`tabS1_compositions.jpg`
- **TOC graphic / 期刊封面装饰图** = `fig0_toc.jpg` 或 `fig0_<topic>.jpg`（tier 默认 general）
- **多 panel 图**（一张 Fig 含 a/b/c/d 多 panel，mineru 经常切成多张）= `fig<编号><panel>_<topic>.jpg`，例：`fig2a_stress-strain.jpg` / `fig2b_dma.jpg` / `fig2c_creep.jpg`
- `<topic-slug>`：3-5 个英文小写词中划线连接

**多 panel alt text 写法**（避免 alt 重复一大段）：
- **lead panel**（fig2a）：完整 C 级 alt，含"Figure 2 contains panels a-d"等说明
- **后续 panel**（fig2b, fig2c...）：简写 `"Same Figure 2, panel b: <这个 panel 自己讲什么>"`
- 这样既保证 lead panel 信息密集，又避免每 panel 重复全图叙述

**`tier` 分级**：
- `"critical"`：数据图（曲线/柱状/热力图）/ 机理 schematic / 关键形貌（SEM/AFM/TEM）/ 反直觉结果图 / 作者重点讨论图
- `"general"`：装置照片 / 样品宏观照片（非关键现象）/ 装饰图 / 不重要的辅助图

**`alt` 写法**：
- critical → **C 级密集描述**：关键数字 + 趋势 + 反直觉点 + 跟其他图关系。可以很长（一行 markdown 没事），可英文，技术，**给 AI 看不是给人看**
- general → **一句话简短**（"experimental setup photo" 这种就够）

⚠️ **`old_hash` 必须给完整 32 位**，主线程做精确替换。
⚠️ **alt 里双引号要 escape**（用 `\"` 或换单引号），别破坏 markdown 语法。

### 块 3 — Figure/Table caption 完整性 + metadata 核对

第一个 sub-agent 额外做：
- **metadata 核对**：vision 看封面页 → 拉出标题 / 作者 / DOI / 期刊 → 跟 backup_log.csv 比对，写入 `meta.yaml`
- **caption 完整性**：每个 Figure/Table 的 caption 是不是完整（MinerU 经常截断）→ 不完整就进块 1 patch

### 块 4 — 跨页内容核对（每个 sub-agent 都做）

- 公式有没有识别错（上下标 / 希腊字母 / 分式 / 积分）
- 表格结构有没有乱（合并单元格被拆 / 列错位）
- 段落有没有被切断或合并
- 这些都进块 1 patches

---

## Step 3c — 主线程聚合 + apply patches

收齐所有 sub-agent 报告后：

1. **批量 mv 图**：按块 2 清单，重命名 `images/` 和 `images_si/` 下文件
2. **同步 md 图引用 + 写入 alt text**：批量替换
   `![](images/<旧 hash>.jpg)` → `![<块 2 给的 alt>](images/<新名>.jpg)`
   - critical 图 alt 是密集长描述（一行 markdown 没事，别折行）
   - general 图 alt 是一句话
   - 双引号 escape
3. **apply patches**：按块 1，用 anchor 文本定位，替换为 new 文本
4. **写 meta.yaml**：基于块 3 的 metadata 写
5. **verify Read**：随机抽 3 个 patch、3 张图，Read 一次确认：
   - 图引用 alt 写进去了（critical 图的 alt 不能是空、不能是占位）
   - patch new 文本确实在 md 里
   - 图文件已重命名
