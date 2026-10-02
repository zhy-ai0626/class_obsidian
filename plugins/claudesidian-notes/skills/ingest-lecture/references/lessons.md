# Lessons — ingest-lecture

踩过的坑和参考样例。遇到怪现象先翻这份。

---

## Failure modes

| 模式 | 触发 | 处理 |
|---|---|---|
| PDF 读 password-protected 误报 | Read 工具说 PDF 加密但实际未加密 | 改用 `PyMuPDF`（`import fitz`）提取 |
| 课程文件夹不存在 | `01_Projects/<CODE>_课名/` 没有 | 问用户课程名 + 学期，创建文件夹 + index.md，**不擅自猜** |
| extract_images.py 失败 | PPT 解析错 / 0 图 | WARN，继续生成笔记（无图嵌入），报告用户 |
| MOC 已存在但 frontmatter 不合规 | index.md 缺 frontmatter | WARN，只追加 Week 段，**不修 frontmatter** |
| 一讲多 PDF/PPT | 用户传多份附件 | 逐份提取后合并到**同一笔记**；不为每份生成独立笔记 |
| **忠实转录化**(CST309 L01, 2026-10) | 提示词里有"不得补写原资料没有的内容",或模型把"准确性优先"理解成"只转述 slide"→ 笔记充满"原页未展开 / 不能读成"(L01 一份约 40 处),延伸讲解 0 处,"Stateless routers"只写"不能读成路由器没有状态"却不讲是什么 | 准确性红线只管"不歪曲课件事实";课件点名没解释的概念按教材口径讲清;Step 5 讲透自检 grep 免责语应为 0 |
| 教学内容被拆出正文 | 把直觉 / 例子 / 自测挪到单独 quickref,正文"回到贴近 PPT" | 讲解属于正文主体;quickref 可以另做,但不能以掏空正文为代价 |
| sub-agent 报告主导写笔记 | 主线程拿到 sub-agent 输出 + MinerU md 后**没 Read 旧笔记 / 模板**就动笔 | **STOP**，回到 Step 4 开头先 Read 旧笔记列章节清单，再决定 Edit 还是 Write |

---

## Example — Good

讲透版知识块(直觉 → 动机 → 定义 → 代入算 → 常见坑):

```markdown
## 知识块 5 — 为什么 Internet 是"网络的网络"

**一句话直觉**: 全世界几万个小网络不可能两两拉线,于是大家都连到少数几个"大中转站",再由中转站之间互连。

**为什么需要它**: 假设有 N 个接入 ISP,要两两直连,需要的链路数是

$$\binom{N}{2} = \frac{N(N-1)}{2} = O(N^2)$$

**代入算一次**: N=10 → 45 条;N=1000 → 约 50 万条。每新增一个 ISP 就要和所有人新拉线——显然不可扩展。

所以课件 pp.26–31 一步步搭出分层结构:接入 ISP → 区域 ISP → tier-1 ISP,
同层之间用 [[C_peering|peering]] 免费互通,在 [[C_ixp|IXP]] 集中交换流量……

> [!warning] 常见坑
> 不要把它画成严格的树:内容商(Google 等)会自建网络直接连到下层 ISP,绕过 tier-1。
```

## Example — Bad

- 全英文
- slide-by-slide 镜像
- 没有知识块组织
- 通用 padding 替代具体解读
- **免责语代替讲解**:"Best effort service model:本页未展开其保证范围。"——新手读完仍不知道 best effort 是什么。应写:"尽力而为 = 网络尽量送,但不保证送到、不保证按序、不保证时延;丢了由端系统(如 TCP)自己处理。"
- **只有定义没有例子**:$O(N^2)$ 不代数字,读者感受不到为什么不可扩展
