# ingest-paper — lessons & failure modes

跑这个 skill 容易踩的坑 + 一个完整例子。每次跑遇到异常情况，先查这里。

---

## Failure modes

| 模式 | 触发 | 处理 |
|---|---|---|
| `main.pdf` 不在 | 文件夹里没这个 | STOP，让用户补，**不擅自从别处拷** |
| MinerU token 过期 / 配额超 | API 错误码 A0211 / -60018 | fallback 到纯 vision；提示用户去 https://mineru.net 处理 |
| SI 是 zip 但解压后没找到能识别的格式 | 全是 cif / 视频 | si.md 写占位，原 zip mv 到 `_attachments_orig/` |
| 图是 hash 名但 sub-agent 没给重命名 | 块 2 漏 | 默认保留 hash 名，警告用户 |
| 图新名给了但 alt 字段为空 / 占位 | sub-agent 偷懒 | alt 字段写 `[alt-missing tier=<critical/general>]` 占位，警告用户。**不要拿原 caption 凑数**（caption 已经在 md 正文里了） |
| sub-agent 给的 alt 含未 escape 的双引号 | 直接拼会破坏 md | 主线程 apply 时统一把 alt 内部的 `"` 替换成 `\"`（或换单引号），自动修复 |
| patches 的 anchor 文本在 md 里找不到（飘了） | sub-agent 引用了不存在的片段 | 跳过这条 patch，记日志，**不擅自模糊匹配** |
| MinerU 输出的 main.md 已存在 | 重跑 | 先备份成 `main.md.<timestamp>.bak`，再覆盖 |
| 某个 sub-agent 失败 | 网络 / 超时 | 重启**单个** sub-agent 跑该 page range；不重跑全部 |

---

## Example: 一篇带 SI 的论文

输入：`01_Projects/Review_<主题>/(YYYY) Author - Title/`，含 `main.pdf` (8 页) + `si.pdf` (12 页)

跑完后：
```
(YYYY) Author - Title/
├── main.pdf, si.pdf       (不动)
├── main.md                # 8 页正文，含 5 个 Figure caption + 2 个公式
├── si.md                  # 12 页 SI，含 8 个 Figure S* + 3 个 Table S*
├── images/                # fig1_stress-strain.jpg, fig2_morphology.jpg ... 5 张
├── images_si/             # figS1_dsc.jpg, figS2_xrd.jpg ... 8 张
└── meta.yaml              # title, authors, DOI, journal, year
```
