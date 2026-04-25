import csv
from pathlib import Path
import re

def clean_filename(s):
    s = s.replace("/", "_").replace(":", "_")
    return re.sub(r'[\\/*?:"<>|]', "", s).replace(" ", "_")

pdf_dir = Path("projects/ai-education/03_pdfs")
with open("projects/ai-education/02_verify/verified.csv", "r", encoding="utf-8") as f:
    records = list(csv.DictReader(f))

for i, row in enumerate(records[:10]):
    doi = (row.get("canonical_doi") or row.get("doi") or "").strip()
    arxiv_id = row.get("arxiv_id", "").strip()
    year = row.get("year", "0000")
    title = row.get("title", "")
    
    # In download.py: doi = row.get("canonical_doi", "").strip() or row.get("doi", "").strip()
    # Let's see what zotero_sync is generating vs actual file
    filename = f"{year}_{clean_filename(arxiv_id or doi or title)}.pdf"
    pdf_path = pdf_dir / filename
    print(f"Generated: {filename} -> Exists: {pdf_path.exists()}")
