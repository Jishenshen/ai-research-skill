[English](README.md) | 简体中文

# AI 科研工作流 (AI Research Workflow)

一个基于 Agent 和大模型的自动化文献研究工作流。本项目利用 LLM Agent 和定制化技能（Skills）来自动化文献检索、交叉验证、下载归档以及论文的深度精读。

## 🌟 核心技能 (Available Skills)

本项目在 `.gemini/skills/` 目录下集成了一套高度优化的 Agent 技能：

- **`literature-search`**: 主动检索。支持 Semantic Scholar, arXiv, CORE 等数据库。采用 **Markdown 驱动配置** (`keywords.md`) 来管理查询词、年份跨度和输出数量。内置**相关度打分引擎**（基于标题/摘要词频加权），自动筛选最高质量的文献池。
- **`literature-verify`**: 交叉验证。通过 CrossRef/arXiv 验证元数据，并自动生成排版精美的 Markdown“论文日报”(`paper_daily.md`)。报告会输出所有验证通过的文献，严格按相关度降序排列，并附带完整的**中英双语摘要**。
- **`literature-ingest`**: 自动下载开源 PDF 并执行**富元数据同步 (Rich Metadata Sync)** 到 Zotero。智能映射作者、摘要、DOI、来源期刊等信息，并自动将文献归类为期刊文章 (Journal Article) 或会议论文 (Conference Paper)。
- **`deep-reading-skills`**: 学术文献精读与质检技能，包含两个核心工作流：
  - **单篇深读模式 (Deep Read Mode)**：对选定的单篇论文进行深度结构化分析，提取核心研究问题、数学建模（LaTeX 公式）、方法论，并生成详尽的中文批判性分析报告。
  - **批量扫读模式 (Batch Scan Mode)**：扫描 Zotero 集合中的多篇文献，根据严格的学术标准（创新性、严谨性、影响力、表达）进行 0-10 分质量打分，并为每篇文献提取“文献阅读八要素”，输出排版精美的 Markdown 报告。

## 🚀 安装与配置

### 1. 克隆项目
```bash
git clone https://github.com/yourusername/ai-research-workflow.git
cd ai-research-workflow
```

### 2. 环境配置
创建 Python 虚拟环境并安装依赖：
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. 配置 API 密钥
复制环境变量模板文件并填写你的凭证：
```bash
cp .env.example .env
```
打开 `.env` 文件，填入你的 [Zotero API 密钥](https://www.zotero.org/settings/keys) 以及可选的学术数据库 API Key。

### 4. 配置 MCP 服务
Agent 依赖 Model Context Protocol (MCP) 与 Zotero 交互，该功能由 `zotero-mcp-server` 包提供（已包含在 `requirements.txt` 中）。

**前提条件：**
- 你的电脑上必须已安装并正在运行 [Zotero 桌面端](https://www.zotero.org/download/)。
- 复制配置模板：
```bash
cp .gemini/settings.json.example .gemini/settings.json
```
*（注：`zotero-mcp` 服务会自动读取你刚才配置好的 `.env` 文件中的密钥，无需重复配置。但如果你使用的是虚拟环境，可能需要将 `settings.json` 中的 `command` 字段修改为 `zotero-mcp` 可执行文件的绝对路径，例如：`/absolute/path/to/.../.venv/bin/zotero-mcp`）*。

## 💡 使用指南

要开启一个新的研究项目，请在 `projects/` 目录下创建一个新文件夹，并使用提供的 Markdown 模板初始化你的检索配置：

```bash
mkdir -p projects/my-new-topic
cp .gemini/skills/literature-search/assets/keywords_template.md projects/my-new-topic/keywords.md
```

打开 `projects/my-new-topic/keywords.md`，编辑你想搜索的关键词、年份和数量限制。然后，通过你的 AI 助手依次触发以下技能：

1. *"使用 literature-search 帮我检索 my-new-topic 的相关论文"*
2. *"使用 literature-verify 验证检索结果并生成双语日报"*
3. *"使用 literature-ingest 下载文献并携带富元数据同步到 Zotero"*
4. *"使用 deep-reading-skills 帮我 [批量扫读质检该分类 / 对某篇论文做深度精读]"*

## 🔒 安全提示
`.env` 和 `.gemini/settings.json` 文件包含敏感的 API 密钥。它们已经在 `.gitignore` 中被排除，以防意外提交。**请绝对不要将这些文件提交到公开的代码仓库中。**