# CAD 电气元器件符号识别 - 文献综述自动化工作流

> 研究主题：CAD 电气元器件符号识别研究现状
> 目标：自动化采集 20 篇相关论文 → 结构化提取 → 横向对比 → Zotero 入库 → 基于 draft 生成结构化文献综述

---

## 🚀 快速启动指南 (Quick Start)

**此工作流已升级为通用引擎架构，支持运行任意方向的研究。**

### 1. 激活虚拟环境 (每次开始前必做)
在 `workflow` 根目录下执行：
```bash
cd /Users/jishenshen/5playground/ai-research-workflow/workflow
source .venv/bin/activate
```

### 2. 运行当前项目 (以 CAD 项目为例)
```bash
# 第一步：搜索并构建候选池
python scripts/01_search.py --project_dir projects/cad_symbol_recognition
```

### 🔧 进阶配置：MCP 搜索集成 (适合探索性搜索)
如果您希望直接在对话中使用 `paper-search-mcp` 插件进行交互式论文检索，请确保您的 Gemini CLI 已配置：

建议遵循**“项目局部化”**的原则。**推荐在项目的虚拟环境（venv）下安装，且不需要全局安装。**

1. **配置文件路径**：`~/.config/gemini/config.json`
2. **配置内容**：
   ```json
   {
     "mcpServers": {
       "paper-search": {
         "command": "npx",
         "args": ["-y", "@openags/paper-search-mcp"],
         "env": { "UNPAYWALL_EMAIL": "your-email@example.com" }
           //Unpaywall 论文数据库的“通行证”，填入你的邮箱即可解锁论文自动抓取功能，合法免费。
       }
     }
   }
   ```
3. **用法**：配置完成后，您可以直接在对话中指令：“使用 paper-search-mcp 搜索关于...的论文”。

### 3. 如何开启一个新研究项目？
1. 在 `projects/` 下新建一个文件夹（如 `projects/my_new_topic`）。
2. 在该文件夹内创建 `config.json`（定义目标、打分标准）和 `keywords.md` 或 `queries.txt`。
3. 运行：`python scripts/01_search.py --project_dir projects/my_new_topic`

---

## 工作流总览

```
环节1 检索采集 → 环节2 元数据验证 → 环节3 PDF下载与解析
   ↓
环节4 结构化提取（研究问题/方法/发现/局限）
   ↓
环节5 横向对比矩阵 → 环节6 Zotero 导入 → 环节7 生成结构化综述
```

---

## 环节 1：论文检索与采集（找到 20 篇相关论文）—llm的相关性分析

### 子步骤
1. 确定关键词矩阵（中英文）：
   - `CAD electrical symbol recognition`
   - `schematic symbol detection`
   - `engineering drawing recognition`
   - `deep learning circuit symbol`
   - `电气图纸符号识别` / `电路图符号检测`
2. 多源检索：Google Scholar、IEEE Xplore、Springer、arXiv、CNKI、Semantic Scholar
3. 去重 + 初筛（按标题/摘要相关性打分）
4. 输出统一 CSV：`title, authors, year, venue, doi, url, abstract`

### 实施方案
- 用 `WebSearch` + `WebFetch` 拉取 Google Scholar / arXiv / Semantic Scholar API
- 写一个 Python 脚本调用 `semanticscholar` 库 + arXiv API，输出 `papers.csv`
- 用 LLM（Claude）对每篇摘要打"相关性 1-5 分"，保留 ≥4 分的 20 篇

### 推荐 Skill
- 内置 `WebSearch` + `WebFetch`（够用）

- ⭐ [`paper-search-mcp`](https://github.com/openags/paper-search-mcp)：MCP 服务器，集成 arXiv/PubMed/bioRxiv/Google Scholar

- 如果还没有安装，只需要一条命令：帮我在gemini cli中安装paper-search-mcp

  ```
  核心功能：                    
    - 多源搜索：arXiv、PubMed、bioRxiv、medRxiv、Google Scholar、Semantic Scholar、Crossref、OpenAlex、PMC、CORE 等 20+ 学术数据库        
    - 下载 PDF：支持 source-native 下载，带 fallback 策略（OpenAIRE → Unpaywall DOI 解析 → 可选 Sci-Hub）                                 
    - 提取文本：把 PDF 转成可读文本喂给 LLM                                              
    - 统一输出格式：所有来源的论文都返回标准化的 dict（通过 Paper 类）
    - 需要用到个人
    邮箱作为unpaywall，mcp必填项
    
    可以去申请获取core /Semantic Scholar API key的配额
   注意：复用工作流推荐 Python 脚本，不要 MCP。核心理由：MCP 依赖 Claude 会话——每次跑都要消耗 token、无法 cron 调度、无法                    
    CI，脚本则是零成本可重复
  ```

  ![image-20260417093617805](/Users/jishenshen/5playground/ai-research-workflow/img/image-20260417093617805.png)

  ![image-20260417094854305](/Users/jishenshen/5playground/ai-research-workflow/img/image-20260417094854305.png)

- 备选：`scholarly`（Python 库，绕 Google Scholar）

---

## 环节 2：论文元数据自动验证（标题/作者/DOI/年份）

### 子步骤
1. 对每篇用 DOI 反查 CrossRef API → 校验 title/authors/year
2. 缺 DOI 的用标题模糊匹配 CrossRef / OpenAlex
3. 标记冲突项人工 review

### 实施方案
- Python 脚本 + `habanero`（CrossRef 客户端）或直接 `requests` 调 `api.crossref.org/works?query.title=...`
- OpenAlex API（免费、无 key、覆盖更全）作为二次验证源
- 输出 `papers_verified.csv` + `conflicts.csv`

### 推荐 Skill / 工具
- ⭐ [`OpenAlex MCP`](https://github.com/reetp14/openalex-mcp) - 30篇以下,复用工作流必须是 Python 脚本，不要 MCP。核心理由：MCP 依赖 Claude 会话——每次跑都要消耗 token、无法 cron 调度、无法CI，脚本则是零成本可重复。

- `crossref-commons`（Python）- `verify.py` 批量推荐

  ![image-20260417102904383](/Users/jishenshen/5playground/ai-research-workflow/img/image-20260417102904383.png)

- 也可用 `claude-api` skill 让 Claude 直接处理 API 调用

---

## 环节 3：PDF 下载与文本提取

### 子步骤
1. 按 DOI/URL 下载 PDF（开放获取优先：arXiv、Unpaywall API）
2. PDF → 结构化文本（保留章节、图表 caption）
3. 失败的标记为"需手动获取"

### 实施方案
- `unpywall` API 找 OA 链接 → `requests` 下载
- 解析：`pymupdf4llm`（输出 markdown，对 LLM 友好）或 `grobid`（最佳学术解析，需 Docker）
- 内置 `Read` 工具直接读取 PDF（≤10 页）

### 推荐 Skill
- ⭐ 内置 `pdf` skill（Claude Code 自带）
- [`grobid`](https://github.com/kermitt2/grobid)：学术 PDF 解析黄金标准
- `pymupdf4llm`：轻量替代

---

## 环节 4：逐篇结构化提取（研究问题/方法/发现/局限）

### 子步骤
1. 设计统一抽取 schema（JSON）：
   ```json
   {
     "research_question": "",
     "method": "",
     "dataset": "",
     "findings": "",
     "limitations": "",
     "metrics": {}
   }
   ```
2. 对每篇 PDF 文本调用 Claude 抽取 → JSON
3. 校验 JSON 完整性，失败项重试

### 实施方案
- 写一个 batch 脚本，每篇 PDF 调用 Claude API（用 prompt caching 缓存 schema 说明，省 token）
- 输出 `extractions/{paper_id}.json`
- 汇总成 `extractions.jsonl`

### 推荐 Skill
- ⭐ 内置 `claude-api` skill（专为这种 batch 抽取设计，自带 prompt caching）

---

## 环节 5：横向对比矩阵

### 子步骤
1. 构建对比维度：年份 / 方法类别（CNN / Transformer / 传统 CV）/ 数据集 / mAP / 输入类型（栅格 / 矢量）/ 局限
2. 生成 `comparison_matrix.xlsx`：行=论文，列=维度
3. 自动聚类：按方法 / 年份分组，生成时间线图、方法分布饼图

### 实施方案
- `pandas` 把 `extractions.jsonl` 透视成矩阵
- `matplotlib` / `plotly` 出图
- Claude 写一段 markdown 对比分析

### 推荐 Skill
- ⭐ 内置 `xlsx` skill（直接生成结构化对比表）
- 内置 `algorithmic-art` 或 `frontend-design`（如需可视化网页）

---

## 环节 6：导入 Zotero

### 子步骤
1. 把 `papers_verified.csv` 转 BibTeX 或 RIS
2. 通过 Zotero Web API 批量上传（带 PDF 附件）
3. 自动打标签：按方法类别 / 年份

### 实施方案
- Zotero Local API（`http://localhost:23119/api/`，Zotero 7 桌面端开启即可）或 Web API（需 user key）
- ⭐ Python `pyzotero` 库，最简单

### 推荐 Skill
- ⭐ [`zotero-mcp`](https://github.com/54yyyu/zotero-mcp)：MCP 服务器，Claude 可直接读写 Zotero 库
- 备选：[`mcp-zotero`](https://github.com/kujenga/mcp-zotero)

---

## 环节 7：基于 draft 生成结构化综述

### 子步骤
1. 读取你的 draft（章节大纲）
2. 把抽取结果按章节"挂载"到对应位置（引言 / 相关工作 / 方法对比 / 挑战 / 展望）
3. 自动生成引用（`\cite{}` 或 `[1]`），保持与 Zotero key 一致
4. 输出 `.md` + `.docx`

### 实施方案
- Claude 读 draft outline → 生成每节内容 → 引用键回填
- `pandoc` 转 docx，bib 文件由 Zotero 导出

### 推荐 Skill
- ⭐ 内置 `docx` skill（直接出 Word）
- 内置 `doc-coauthoring` skill（结构化协同写作）

---

## 执行顺序与验证节点

| 阶段 | 产出物 | 验证方式 |
|---|---|---|
| 1 + 2 | `papers_verified.csv`（20 条） | 人工抽查 5 篇 DOI |
| 3 | `pdfs/` 目录 + `texts/` | 检查下载成功率 |
| 4 | `extractions.jsonl` | 抽查 3 篇 JSON 质量 |
| 5 | `comparison_matrix.xlsx` | 看是否能一眼对比 |
| 6 | Zotero 库新增 collection | Zotero 客户端确认 |
| 7 | `review.docx` | 阅读 + 引用核对 |

---

## 目录结构建议

```
workflow/
├── literature-review-workflow.md   # 本文件
├── 01_search/
│   ├── keywords.md
│   ├── search.py
│   └── papers.csv
├── 02_verify/
│   ├── verify.py
│   └── papers_verified.csv
├── 03_pdfs/
│   ├── download.py
│   ├── pdfs/
│   └── texts/
├── 04_extract/
│   ├── extract.py
│   ├── schema.json
│   └── extractions.jsonl
├── 05_compare/
│   ├── compare.py
│   └── comparison_matrix.xlsx
├── 06_zotero/
│   └── import_zotero.py
└── 07_review/
    ├── draft.md
    └── review.docx
```
