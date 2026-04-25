English | [简体中文](README_zh-CN.md)

# AI Research Workflow

An agentic, AI-powered literature research workflow. This project utilizes LLM agents and specialized skills to automate the process of finding, verifying, downloading, and deeply analyzing academic papers.

## 🌟 Available Skills

This project comes with a highly optimized set of integrated agent skills located in the `.gemini/skills/` directory:

- **`literature-search`**: Proactively searches for papers across Semantic Scholar, arXiv, and CORE. It uses a Markdown-driven configuration (`keywords.md`) to manage queries, date ranges, and result limits. Includes an autonomous **relevance ranking engine** (scoring based on title/abstract keyword frequency) to curate the best results.
- **`literature-verify`**: Validates metadata against CrossRef/arXiv and generates a beautifully formatted Markdown "Paper Daily" report (`paper_daily.md`). Outputs all verified papers sorted by relevance, featuring full English and translated Chinese abstracts.
- **`literature-ingest`**: Automatically downloads open-access PDFs and performs a **Rich Metadata Sync** directly to your Zotero library. It intelligently maps authors, venues, DOIs, and abstracts, automatically categorizing items as Journal Articles or Conference Papers.
- **`deep-reading-skills`**: A comprehensive academic reading assistant with two core workflows:
  - **Deep Read Mode**: Performs an in-depth extraction of a single paper, generating a detailed Chinese Markdown report that includes core problem definitions, mathematical modeling (LaTeX), methodology breakdown, and critical analysis.
  - **Batch Scan Mode**: Scans multiple papers in a Zotero collection, scoring their quality (0-10) based on rigorous academic criteria (Novelty, Rigor, Impact, Clarity) and extracting the "8 Elements of Literature Reading" into a structured Markdown report.

## 🚀 Setup & Installation

### 1. Clone the repository
```bash
git clone https://github.com/Jishenshen/ai-research-skill.git
cd ai-research-skill
```

### 2. Environment Setup
Create a Python virtual environment and install dependencies:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure API Keys
Copy the example environment file and fill in your details:
```bash
cp .env.example .env
```
Open `.env` and configure your [Zotero API keys](https://www.zotero.org/settings/keys) and optionally your Semantic Scholar/CORE API keys.

### 4. Configure MCP Settings
The agent uses the Model Context Protocol (MCP) to interact with Zotero via the `zotero-mcp-server` package (included in `requirements.txt`).

**Prerequisites:**
- [Zotero Desktop](https://www.zotero.org/download/) must be installed and running on your machine.
- Copy the settings template:
```bash
cp .gemini/settings.json.example .gemini/settings.json
```
*(Note: `zotero-mcp` will automatically read your API keys from the `.env` file. However, if you are using a virtual environment, you may need to update the `command` field in `settings.json` to point to the absolute path of your `zotero-mcp` executable, e.g., `/absolute/path/to/.../.venv/bin/zotero-mcp`)*.

## 💡 Usage

To start a new research project, create a directory under `projects/` and initialize your search configuration using the provided Markdown template:

```bash
mkdir -p projects/my-new-topic
cp .gemini/skills/literature-search/assets/keywords_template.md projects/my-new-topic/keywords.md
```

Edit `projects/my-new-topic/keywords.md` to define your specific search queries, year boundaries, and limits. Then, trigger the skills sequentially via your AI assistant:

1. *"Use literature-search to find papers for my-new-topic"*
2. *"Use literature-verify to validate the results and generate the daily report"*
3. *"Use literature-ingest to download and sync metadata/PDFs to Zotero"*
4. *"Use deep-reading-skills to [batch scan the collection / deeply analyze Paper Title]"*

## 🔒 Security Note
The `.env` and `.gemini/settings.json` files contain sensitive API keys. They are explicitly ignored in the `.gitignore` to prevent accidental commits. **Never commit these files to a public repository.**# ai-research-skill
