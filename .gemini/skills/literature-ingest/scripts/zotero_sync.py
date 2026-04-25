#!/usr/bin/env python3
"""
Stage 04: Zotero Synchronization (Rich Metadata Version)
-------------------------------------------------------
Goal: Sync local PDFs to Zotero with full metadata (Authors, DOI, Venue, etc.)
      by matching files against verified.csv.
"""

import argparse
import csv
import os
import sys
import time
import re
from pathlib import Path
from dotenv import load_dotenv
from pyzotero import zotero

import unicodedata

def clean_filename(title: str, max_length: int = 60) -> str:
    s = "".join(c for c in unicodedata.normalize("NFKD", title) if not unicodedata.combining(c))
    s = re.sub(r"[^\w\s-]", "", s).strip()
    s = re.sub(r"[-\s]+", "_", s)
    return s[:max_length].rstrip("_")

def parse_authors(author_str):
    """Convert 'Author A; Author B' to Zotero creator format"""
    creators = []
    if not author_str:
        return creators
    
    authors = [a.strip() for a in author_str.split(";") if a.strip()]
    for auth in authors:
        # Simple split for First/Last name
        parts = auth.split(" ")
        if len(parts) > 1:
            creators.append({
                "creatorType": "author",
                "firstName": " ".join(parts[:-1]),
                "lastName": parts[-1]
            })
        else:
            creators.append({
                "creatorType": "author",
                "lastName": auth,
                "fieldMode": 1 # Single field mode
            })
    return creators

def main():
    parser = argparse.ArgumentParser(description="Zotero PDF Sync with Metadata")
    parser.add_argument("--project", required=True, help="Project name")
    args = parser.parse_args()

    load_dotenv()
    user_id = os.getenv("ZOTERO_USER_ID") or os.getenv("ZOTERO_LIBRARY_ID")
    api_key = os.getenv("ZOTERO_API_KEY")
    library_type = os.getenv("ZOTERO_LIBRARY_TYPE", "user")

    if not user_id or not api_key:
        print("Error: ZOTERO_USER_ID and ZOTERO_API_KEY must be set in .env")
        sys.exit(1)

    project_name = args.project
    project_dir = Path("projects") / project_name
    pdf_dir = project_dir / "03_pdfs"
    verified_csv = project_dir / "02_verify" / "verified.csv"
    
    if not verified_csv.exists():
        print(f"Error: verified.csv not found at {verified_csv}")
        sys.exit(1)

    # 2. Connection
    print(f"Connecting to Zotero (ID: {user_id})...")
    z = zotero.Zotero(user_id, library_type, api_key)
    
    # 3. Collection Handling
    col_key = None
    collections = z.collections()
    for col in collections:
        if col['data']['name'] == project_name:
            col_key = col['key']
            break
    
    if not col_key:
        print(f"Creating new collection: '{project_name}'...")
        resp = z.create_collections([{'name': project_name}])
        col_key = list(resp['successful'].values())[0]['key']

    # 4. Load Metadata and Match Files
    print(f"Reading metadata from {verified_csv}...")
    with open(verified_csv, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        records = list(reader)

    # Get existing items to avoid duplicates
    print("Checking existing items in collection...")
    existing_items = z.collection_items(col_key)
    # Use DOI or Title to check for existing top-level items
    existing_identifiers = set()
    for item in existing_items:
        data = item['data']
        if data.get('DOI'):
            existing_identifiers.add(data['DOI'].lower())
        existing_identifiers.add(data.get('title', '').lower())

    success_count = 0
    skipped_count = 0
    fail_count = 0

    for i, row in enumerate(records, 1):
        title = row.get("title", "")
        doi = (row.get("canonical_doi") or row.get("doi") or "").strip()
        arxiv_id = row.get("arxiv_id", "").strip()
        year = row.get("year", "0000")
        
        # Check if already in Zotero
        if (doi and doi.lower() in existing_identifiers) or title.lower() in existing_identifiers:
            print(f"[{i}/{len(records)}] SKIP: {title[:50]}... (Already in Zotero)")
            skipped_count += 1
            continue

        # Check if PDF exists locally
        filename = f"{year}_{clean_filename(arxiv_id or doi or title)}.pdf"
        pdf_path = pdf_dir / filename
        
        if not pdf_path.exists():
            # If not found by generated name, try to see if ANY pdf matches title (fallback)
            pdf_path = None
            print(f"[{i}/{len(records)}] NO PDF: {title[:50]}...")
            # We still sync metadata even if PDF is missing
        else:
            print(f"[{i}/{len(records)}] SYNCING: {title[:50]}...")

        try:
            # Create Journal Article or Conference Paper template
            # For simplicity, default to journalArticle if venue looks like one
            venue = row.get("venue", "").lower()
            item_type = 'journalArticle'
            if 'conf' in venue or 'symposium' in venue or 'proceedings' in venue:
                item_type = 'conferencePaper'
            
            template = z.item_template(item_type)
            template['title'] = title
            template['creators'] = parse_authors(row.get("authors", ""))
            template['date'] = year
            template['DOI'] = doi
            template['url'] = row.get("url", "")
            template['abstractNote'] = row.get("abstract", "")
            template['collections'] = [col_key]
            
            if item_type == 'journalArticle':
                template['publicationTitle'] = row.get("venue", "")
            else:
                template['proceedingsTitle'] = row.get("venue", "")

            item_resp = z.create_items([template])
            
            if item_resp['successful']:
                item_key = list(item_resp['successful'].values())[0]['key']
                if pdf_path:
                    print(f"  -> Uploading PDF: {filename}")
                    z.attachment_simple([str(pdf_path)], item_key)
                print(f"  [✓] Success.")
                success_count += 1
            else:
                print(f"  [X] Failed metadata sync: {item_resp['failed']}")
                fail_count += 1
                
        except Exception as e:
            print(f"  [X] Error: {e}")
            fail_count += 1
        
        time.sleep(0.5)

    print(f"\nRich Sync Complete for {project_name}:")
    print(f"- Success: {success_count} (Metadata + PDF if available)")
    print(f"- Skipped: {skipped_count}")
    print(f"- Failed : {fail_count}")

if __name__ == "__main__":
    main()
