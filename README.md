# Class Obsidian · Claudesidian for Claude Code

将 Claudesidian 课程笔记插件打包为 Claude Code 插件市场。包含 4 个技能、2 个命令，以及模板、参考资料和 Python 共享脚本。

## 在 Claude Code 中安装

在 Claude Code 对话中依次执行：

```text
/plugin marketplace add zhy-ai0626/class_obsidian
/plugin install claudesidian-notes@class-obsidian
```

安装后重启 Claude Code，在 `/plugin` 中确认插件已启用。插件名称是 `claudesidian-notes`，市场名称是 `class-obsidian`。

也可以让 Claude Code 执行以下终端命令，安装到当前用户范围：

```bash
claude plugin marketplace add zhy-ai0626/class_obsidian
claude plugin install claudesidian-notes@class-obsidian --scope user
```

这是完整插件，安装时会一并带上 `shared/` 和模板。请保留整个插件目录结构，因为技能通过 `${CLAUDE_PLUGIN_ROOT}` 引用这些文件。

## 使用方式

在 Obsidian 笔记库根目录启动 Claude Code，说明课程代号、源材料和目标目录。默认课程目录约定为 `01_Projects/<CODE>_课名/`。

| 技能 | 可以直接这样说 |
|---|---|
| `ingest-lecture` | “整理这份讲义，课程代号 AIT201，写入课程笔记并更新索引。” |
| `ingest-tutorial` | “解这份 tutorial，写出推导过程并核对课程原理。” |
| `distill-principles` | “把 AIT201 课程读薄，提炼第一原理、推导树与公式索引。” |
| `ingest-paper` | “整理这篇论文及补充材料，核对图片并生成 Markdown。” |

也可使用带插件命名空间的入口，例如 `/claudesidian-notes:ingest-lecture`。另外两个批处理命令是：

```text
/claudesidian-notes:distill-all
/claudesidian-notes:audit-tutorials AIT201
```

其中 `distill-all` 原有默认扫描范围为 `01_Projects/CME*`；其他课程前缀请明确要求 Claude 调整扫描范围。

## Python 脚本依赖

插件安装与脚本运行环境分别配置。处理 PDF、PPT、Word、Excel 等材料前，可克隆仓库，在虚拟环境中安装共享脚本依赖：

```bash
git clone https://github.com/zhy-ai0626/class_obsidian.git
cd class_obsidian
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r plugins/claudesidian-notes/requirements.txt
```

Windows 的虚拟环境激活命令为 `.venv\Scripts\Activate.ps1`。部分原技能示例使用 Windows 的 `py` 命令；macOS/Linux 请使用已激活虚拟环境中的 `python`，或对应的 `python3`。在该环境中进入笔记库目录，再启动 Claude Code。

使用 MinerU 云端解析时，在**笔记库根目录**的 `.env` 中配置 `MINERU_API_TOKEN`，也可使用同名环境变量。令牌从 [MinerU](https://mineru.net/apiManage/token) 获取，保留在本机。仓库已忽略 `.env`、虚拟环境和 Python 缓存。第三方服务访问与实际材料处理需要在使用环境中配置并验证。

## 更新

```text
/plugin marketplace update class-obsidian
/plugin update claudesidian-notes@class-obsidian
```

更新后重启 Claude Code。

## 目录与来源

```text
.claude-plugin/marketplace.json   Claude Code 插件市场入口
plugins/claudesidian-notes/
  .claude-plugin/plugin.json     插件清单
  skills/                       4 个技能及其模板、参考资料
  commands/                     2 个批处理命令
  shared/                       共享资源与 Python 脚本
  requirements.txt              脚本依赖
  README.md                     原插件详细说明
```

本仓库基于本机已安装的 `claudesidian-notes` v0.1.0，保留原插件作者署名 `iZHENGjy`。v0.1.1 增加 Claude Code 市场入口、安装说明和依赖清单，并修正插件元数据格式；技能正文与共享脚本保持原样。

结构验证命令：

```bash
claude plugin validate .
claude plugin validate plugins/claudesidian-notes
```

安装机制参考 [Claude Code 插件市场文档](https://code.claude.com/docs/en/plugin-marketplaces) 与 [插件结构文档](https://code.claude.com/docs/en/plugins-reference)。
