---
name: literature-search
description: "Agent proactive literature search skill. It first actively looks up the project's keywords from local config files, then executes the search using the underlying script, and reports the results."
---

# Literature Search Skill

This skill automates the process of finding relevant academic papers for a specific project. It uses an **Agent Proactive Lookup** model to find the keywords without requiring the user to provide them directly.

## Core Workflow

1. **Identify the Project**:
   - Extract the `{project_name}` from the user's prompt.
   - The project directory will be `projects/{project_name}`.

2. **Proactive Knowledge Acquisition (Keyword & Config)**:
   - Use file reading tools to check `projects/{project_name}/keywords.md`.
   - **Initialization**: If `keywords.md` does not exist, copy the template from `.gemini/skills/literature-search/assets/keywords_template.md` to the project directory and fill it based on user requirements.
   - The script will parse the Markdown file for `Year From`, `Year To`, `Max Results`, and the query table.

3. **Execution**:
   - Run the local search script via shell command:
     `python .gemini/skills/literature-search/scripts/search.py --project_dir projects/{project_name}`
   - **Pipeline Logic**:
     1. Fetches raw data from APIs.
     2. Saves all unique results to `01_search/raw_papers.csv`.
     3. **Ranking**: Automatically calculates a relevance score based on keyword frequency in Title (weight 2.0) and Abstract (weight 1.0).
     4. Saves the top ranked results to `01_search/papers.csv` (limited by `Max Results`).

4. **Validation and Reporting**:
   - Check `projects/{project_name}/01_search/papers.csv`.
   - Report the total raw papers found and the number of curated papers after ranking.

## Guidelines

- Never hardcode keywords. Always use the `keywords.md` as the single source of truth.
- Explain the ranking results briefly (e.g., "Found 100 papers, selected top 20 based on relevance").
- Ensure the Python script finishes executing before reading results.