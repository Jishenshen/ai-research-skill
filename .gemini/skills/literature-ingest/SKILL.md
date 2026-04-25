---
name: literature-ingest
description: "In-situ literature acquisition skill. It downloads PDF files to local storage and synchronizes them to the Zotero library."
---

# Literature Ingest Skill

This skill handles the "Inhalation" of verified literature. It first downloads the PDF files from the web to the project's local directory and then synchronizes these local assets into the project's Zotero collection.

## Core Workflow

1. **Identify the Project**:
   - Extract the `{project_name}` from the user's prompt.
   - The project directory will be `projects/{project_name}`.

2. **Phase 1: Download PDFs**:
   - Run the local download script:
     `python .gemini/skills/literature-ingest/scripts/download.py --project_dir projects/{project_name}`
   - The script will read `projects/{project_name}/02_verify/verified.csv` and download available PDFs to `projects/{project_name}/03_pdfs/`.
   - Report the download success/failure count to the user.

3. **Phase 2: Zotero Synchronization**:
   - After the download is complete, run the Zotero sync script:
     `python .gemini/skills/literature-ingest/scripts/zotero_sync.py --project {project_name}`
   - The script will upload the local PDFs and create corresponding entries in the Zotero collection named `{project_name}`.

4. **Reporting**:
   - Summarize the ingestion status: "X papers downloaded and synced to Zotero collection '{project_name}'."

## Guidelines

- **Persistence**: Ensure the project-specific PDF directory exists before syncing.
- **Agentic Continuity**: If download fails for all papers, inform the user and ask if they still want to attempt Zotero sync for metadata only.
- **Environment**: Ensure `.env` is correctly loaded by the scripts for Zotero API credentials.
