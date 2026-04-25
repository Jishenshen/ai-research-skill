# AI 科研工作流架构优化方案 (Architecture Optimization Proposal)

## 一、 核心痛点与优化思路回应

### 1. 将 `01_search.py` 和 `02_verify.py` 封装为 Skill
**评估：非常赞同。**
*   **当前痛点**：目前需要手动敲击命令行（如 `python scripts/01_search.py --project_dir ...`），参数传递繁琐，且 LLM 无法直接将自然语言意图无缝转化为检索动作。
*   **优化方案**：创建 `literature-search` 和 `literature-verify` 两个 Skill。
    *   **低耦合做法**：Skill 本身不写死冗长的 Python 逻辑，而是作为**“编排层 (Orchestrator)”**。在 `SKILL.md` 中定义标准操作流，指导 Gemini CLI 去调用后端的 Python 脚本或相关的 MCP 工具。这样用户只需说：“帮我搜索 CAD 符号识别的最新论文”，Agent 就能自动完成解析意图、调用脚本、读取 CSV 结果并反馈的全过程。

### 2. 空置的 `api_clients.py` 是否保留？与 Zotero-MCP 的关系？
**评估：强烈建议废弃通用 `api_clients.py`，全面拥抱 MCP 架构。**
*   **不要把 Zotero API 放进 Python 脚本**：这会导致严重的**架构冲突和功能冗余**。我们已经验证了 `zotero-mcp` 能够完美、高效地完成检索、读写和元数据提取。如果再在 `api_clients.py` 里写一套基于 `pyzotero` 的 HTTP 请求，不仅增加了维护成本，还会导致 Agent 产生“我该用 MCP 还是用 Python 脚本”的混淆。
*   **清理无用代码**：既然 `api_clients.py`、`file_helpers.py` 和 `logger.py` 目前是空的，且核心功能已被 MCP 或现有脚本接管，建议直接**删除整个 `utils/` 文件夹**，贯彻极简主义。

### 3. 基于“低耦合、高复用”的进一步架构建议
结合你的 `.venv` 目录中已经出现了 `paper-search-mcp` 等线索，我建议将系统彻底划分为 **三个解耦层**：

1.  **交互与编排层 (Agent Skills)**：`.gemini/skills/` 专门负责自然语言理解、业务逻辑编排和 Prompt 模板。
2.  **工具与能力层 (Tools / MCP Servers)**：将所有的外部 API 交互（Zotero、Semantic Scholar、arXiv）全部 MCP 化。Python 脚本仅用于纯粹的本地数据清洗（如去重、矩阵计算）。
3.  **数据与资产层 (Data Storage)**：`projects/` 专门用于存放与项目相关的配置、CSV、PDF 以及生成的 Markdown 报告，做到数据与逻辑完全分离。

---

## 二、 推荐的新目录架构 (Proposed Directory Structure)

```text
workflow/
├── .gemini/
│   ├── settings.json              # 注册所有的 MCP Servers (Zotero, Paper-Search)
│   └── skills/                    # 核心大脑：业务编排层
│       ├── literature-search/     # 负责对接 Paper-Search MCP 或 01_search.py
│       ├── literature-verify/     # 负责对接 02_verify.py 逻辑
│       ├── paper-scanner/         # 负责 Zotero 批量阅读与打分 (已验证)
│       └── deep-reading/          # 负责单篇精读与图文排版 (已验证)
│
├── mcp_servers/                   # (新增) 工具能力层：替代原 utils/ 和部分 scripts/
│   ├── paper_search/              # 封装 Semantic Scholar/arXiv/CORE 为 MCP
│   └── zotero_local/              # Zotero MCP 服务端代码
│
├── scripts/                       # 本地数据处理层：仅保留纯无状态的本地计算
│   ├── data_cleaner.py            # 数据去重、格式化清洗 (原 02_verify)
│   └── matrix_generator.py        # 负责生成文献对比矩阵 (原 06_matrix)
│
├── projects/                      # 数据资产层：业务数据完全隔离
│   └── cad_symbol_recognition/
│       ├── config.json            # 检索词、时间范围等项目级配置
│       ├── 01_search_pool.csv     # 原始检索池
│       ├── 02_verified.csv        # 初筛保留文献
│       ├── 03_pdfs/               # 本地 PDF 暂存区
│       └── 04_reports/            # Scanner 与 Deep Reading 产出的 Markdown/CSV
│
└── docs/                          # 规范与文档
```

---

## 三、 重构实施步骤建议 (Action Plan)

如果你同意上述思路，我们可以分阶段执行重构：

*   **Phase 1: 瘦身与清理 (Cleanup)**
    *   删除无用的 `utils/` 目录。
    *   将 `scripts/04_zotero_sync.py` 废弃或改为 Skill 包装器（因为同步逻辑可通过 `zotero-mcp` + Agent 自动完成）。
*   **Phase 2: 检索与初筛的 Skill 化 (Skillification)**
    *   创建 `literature-search` 技能，通过 Agent 读取项目下的 `config.json`，然后调用本地的搜索脚本（或 `paper-search-mcp`），生成 `01_search_pool.csv`。
    *   创建 `literature-verify` 技能，指导 Agent 按照特定标准（如排除没有 PDF 的、年份过老的）处理 CSV，生成清洗后的文件。
*   **Phase 3: MCP 深度整合 (MCP Integration)**
    *   将 `01_search.py` 中繁杂的 API 请求（Semantic Scholar 等）彻底抽离，配置为你环境中的 `paper-search-mcp`，使搜索动作彻底变为标准化的 Tool Call。

---
*等待用户评审...*