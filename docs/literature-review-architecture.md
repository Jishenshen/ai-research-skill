# 文献综述自动化工作流：架构设计文档 (v1.0)

## 1. 设计哲学
本工作流采用 **“规范驱动开发 (Spec-Driven Development) + 微引擎驱动 + 阶段性交付”** 模式。
*   **规范与代码分离**：所有的业务逻辑与边界条件定义在 `specs/`（Markdown），所有的代码实现存放在 `scripts/`（Python），确保 AI 协作时方向清晰、代码可控。
*   **逻辑与数据分离**：所有的自动化逻辑存放在 `scripts/`（高复用），所有的项目数据存放在 `projects/`（隔离性）。
*   **抽象沉淀**：通用功能（如API请求、日志、文件读写）抽离到 `utils/`，保持核心脚本的极简。
*   **人在回路 (Human-in-the-Loop)**：每一阶段的输出结果都存放在独立的文件夹中，通过物理隔离强制用户在进入下一阶段前进行质量确认。
*   **断点续传**：基于文件的状态管理，脚本执行失败或人工干预后，可从任意阶段重新启动。

---

## 2. 目录结构规范

```text
ai-research-workflow/
├── specs/                        # 【业务规范】规范与逻辑文档库 (AI Input)
│   ├── 00_global_config_spec.md  # 全局配置、环境变量与通用规范
│   ├── 01_search_spec.md         # 文献检索逻辑规范
│   ├── 02_verify_spec.md         # 交叉验证与清洗规范
│   ├── 03_download_spec.md       # PDF下载逻辑规范
│   └── 04_zotero_sync_spec.md    # Zotero同步规范
├── scripts/                      # 【核心引擎】自动化工作流执行脚本 (AI Output)
│   ├── 01_search.py              # 多源论文检索与初筛
│   ├── 02_verify.py              # 元数据验证与真实性核对
│   ├── 03_download.py            # PDF 抓取与全文文本化
│   ├── 04_zotero_sync.py         # Zotero 文献库同步
│   ├── 05_extract.py             # LLM 结构化核心字段抽取
│   ├── 06_matrix.py              # 对比矩阵生成与数据透视
│   └── 07_synthesize.py          # 基于大纲生成综述初稿
├── utils/                        # 【通用工具】基础组件与复用逻辑
│   ├── logger.py                 # 日志记录器
│   ├── api_clients.py            # Zotero/Arxiv等API基础封装
│   └── file_helpers.py           # 文件读写通用方法
├── projects/                     # 【项目空间】各研究课题数据隔离
│   └── {project_name}/
│       ├── config.json           # 项目全局配置（目标、字段、API参数）
│       ├── 01_search/            # 检索阶段产出 (Input: keywords)
│       │   └── papers.csv        # 初始候选池
│       ├── 02_verify/            # 验证阶段产出 (Input: 01_search/papers.csv)
│       │   └── verified.csv      # 已确认真实性的清单
│       ├── 03_pdfs/              # 下载阶段产出 (Input: 02_verify/verified.csv)
│       │   ├── pdfs/             # 原始 PDF 库
│       │   └── texts/            # 解析后的 Markdown/Text 库
│       ├── 04_zotero/            # 文献库状态 (Input: 02_verify/verified.csv)
│       │   └── sync_log.json     # 导入状态记录
│       ├── 05_extract/           # 抽取阶段产出 (Input: 03_pdfs/texts/)
│       │   └── results/*.json    # 每篇论文的结构化数据
│       ├── 06_matrix/            # 对比阶段产出 (Input: 05_extract/results/)
│       │   └── comparison.xlsx   # 横向对比大表
│       └── 07_review/            # 综述阶段产出 (Input: draft.md + 06_matrix/)
│           ├── draft.md          # 预设的综述大纲（由用户提供）
│           └── review.md         # 自动生成的文献综述初稿
├── docs/                         # 【项目文档】高层级架构与说明
│   ├── literature-review-architecture.md
│   └── literature-review-workflow.md
├── .env                          # 环境密钥管理 (Claude API, Zotero Key, etc.)
└── requirements.txt              # Python 依赖清单
```

---

## 3. 七大阶段详情 (The 7 Stages)

### Stage 01: 检索 (Search)
* **目标**：构建广泛的候选论文池。

* **逻辑**：聚合 arXiv, Semantic Scholar, OpenAlex 等 API。—知网风控比较严格

* **关键交付物**：`papers.csv`。

  ```python
  python scripts/01_search.py --project projects/{project_name}
  ```

### Stage 02: 验证 (Verify)
* **目标**：确保论文元数据（DOI、年份、来源）的准确性。

* **逻辑**：通过 CrossRef 反查，自动纠正错误条目，标记无法验证的论文。

* **关键交付物**：`verified.csv`。

  ```python
  # 运行脚本
  python scripts/02_verify.py --project projects/{project_name}
  ```

  <mark>需要补充：论文相关度的逻辑验证</mark>

  ```text
  从关键词匹配、学术影响力、时效性、新颖度、来源可靠性五个维度给每篇论文打分（满分100分）
  ```


### Stage 03: 下载与解析 (Download & Parse)
*   **目标**：获取全文内容并转化为 LLM 友好格式。
*   **逻辑**：利用 Unpaywall 寻找 OA 链接；<mark>使用 `pymupdf4llm` 进行 Markdown 转化.</mark>
*   **关键交付物**：`pdfs/` 文件夹及对应的 `texts/`。
*   每次运行完下载脚本后，自动生成一个 failed_downloads.csv

### Stage 04: Zotero 同步 (Sync)
* **目标**：将经过验证的文献正式纳入学术管理系统。

* **逻辑**：调用 PyZotero API 创建条目，自动上传对应的本地 PDF。

* **关键交付物**：Zotero 库中的指定 Collection。


### Stage 05: 结构化抽取 (Extraction)
*   **目标**：将非结构化论文转化为结构化知识点。
*   **逻辑**：利用 LLM 针对 `research_question`, `methodology`, `findings`, `limitations` 进行抽取。
*   **关键交付物**：一系列独立 JSON 文件。

### Stage 06: 对比矩阵 (Matrix)
*   **目标**：实现文献间的横向透视。
*   **逻辑**：将分散的 JSON 汇总，生成支持过滤和排序的 Excel 矩阵。
*   **关键交付物**：`comparison.xlsx`。

### Stage 07: 综述合成 (Synthesis)
*   **目标**：输出可读性强的综述草案。
*   **逻辑**：读取用户提供的 `draft.md`，将 Stage 06 的对比结论作为素材填充至对应章节。
*   **关键交付物**：`final_review.md`。

---

## 4. 数据契约 (Data Contract)
所有阶段脚本必须支持通过命令行指定项目路径，例如：
```bash
python scripts/03_download.py --project projects/cad_symbol_recognition
```
每个阶段的输出必须为下一阶段提供清晰、格式化的输入。

---

## 5. 扩展性设计
*   **LLM 适配**：Stage 05 & 07 的提示词模板化，支持随时切换 Claude/GPT/DeepSeek。
*   **多语言支持**：在 `config.json` 中配置语言偏好，使脚本能同时处理中英文献。
