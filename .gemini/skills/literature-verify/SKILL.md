---
name: literature-verify
description: "Data cleaning and deduplication for literature search results. Verifies metadata against CrossRef, arXiv, and OpenAlex."
---

# Literature Verify Skill

This skill automates the verification and cleaning of the raw literature search results. It cross-checks the DOIs, titles, and authors against multiple databases to resolve conflicts and remove duplicates.

## Core Workflow

1. **Identify the Project**:
   - Extract the `{project_name}` from the user's prompt.
   - The project directory will be `projects/{project_name}`.

2. **Pre-check**:
   - Ensure the file `projects/{project_name}/01_search/papers.csv` exists. If it does not, inform the user that `literature-search` must be run first.

3. **Execution**:
   - Run the local verify script via shell command:
     `python .gemini/skills/literature-verify/scripts/verify.py --project projects/{project_name}`
   - The script will read the raw papers, verify them via APIs, and generate two files: `verified.csv` and `conflicts.csv`.

4. **Validation and Reporting**:
   - Read the verification summary from the console output.
   - **File Generation**: You MUST generate a Markdown report file at `projects/{project_name}/02_verify/paper_daily.md`.
   - **Sorting Requirement**: Read all entries from `projects/{project_name}/02_verify/verified.csv`. You MUST sort these entries in descending order based on their `relevance_score` before formatting them into the Markdown report.
   - **Standard Output Format**:
     Format ALL verified papers into `paper_daily.md` as follows:

     # 📚 {Project Name} 验证后论文日报 | {YYYY-MM-DD}
     
     > 共成功验证 **{Total Verified}** 篇论文，冲突 **{Total Conflicts}** 篇（下方列表已按相关度 Relevance Score 降序排列）：
     
     ---
     
     ### {Index}. {Title}
     > {arXiv ID / DOI} | 📅 {Year} | ⭐ 相关度: {relevance_score}
     > 👥 {Authors}
     > 🏛️ {Venue}
     > 🔗 [详情链接]({URL})
     > 📖 **英文摘要 (Abstract)**:
     > {Full English Abstract}
     >
     > 📖 **中文摘要 (Translation)**:
     > {Accurate Chinese Translation of the Abstract}
     
     ---
     (Repeat for ALL verified papers)

   - After creating the file, display a brief summary in the chat, confirming the number of papers processed and sorted.

## Guidelines

- **Persistence**: The `paper_daily.md` file is a mandatory project asset for the verification stage.
- **Visual Presentation**: Adhere to the "Paper Daily" (论文日报) aesthetic with emojis (📅, ⭐, 👥, 🏛️, 🔗, 📖).
- **Automation**: Do not ask the user for permission to create this file; it is a standard part of the `literature-verify` workflow.
- Ensure the python script finishes executing before reading the CSV and generating the MD report.