#!/usr/bin/env python3
"""
Stage 03: Download & Parsing (PDF Download + Sci-Hub Fallback)
-------------------------------------------
Goal: Download PDF files for papers listed in verified.csv.
Logic: 
  1. Use explicit pdf_url if available.
  2. Use arxiv_id to construct arXiv PDF URL.
  3. Query OpenAlex API with canonical_doi to find Open Access (OA) PDF links.
  4. Fallback: Try Sci-Hub mirrors for non-OA papers using DOI.
Input:  projects/{project}/verified.csv
Output: projects/{project}/pdfs/*.pdf
"""

import argparse
import csv
import json
import os
from dotenv import load_dotenv
load_dotenv()
import re
import sys
import time
import unicodedata
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

try:
    from tqdm import tqdm
except ImportError:
    print("Warning: 'tqdm' is not installed. (pip install tqdm)")
    tqdm = None

OPENALEX_BASE = "https://api.openalex.org/works"
SCIHUB_MIRRORS = ["https://sci-hub.se", "https://sci-hub.st", "https://sci-hub.ru"]
REQUEST_TIMEOUT = 30
SLEEP_BETWEEN = 1.5

def clean_filename(title: str, max_length: int = 60) -> str:
    s = "".join(c for c in unicodedata.normalize("NFKD", title) if not unicodedata.combining(c))
    s = re.sub(r"[^\w\s-]", "", s).strip()
    s = re.sub(r"[-\s]+", "_", s)
    return s[:max_length].rstrip("_")

def get_oa_pdf_url(doi: str, session: requests.Session) -> str:
    if not doi: return ""
    try:
        url = f"{OPENALEX_BASE}/https://doi.org/{doi}"
        r = session.get(url, timeout=REQUEST_TIMEOUT)
        if r.status_code == 200:
            data = r.json()
            oa = data.get("open_access", {})
            if oa.get("is_oa") and oa.get("oa_url"):
                oa_url = oa.get("oa_url")
                if oa_url.endswith(".pdf"): return oa_url
                best_loc = data.get("best_oa_location") or {}
                if best_loc.get("pdf_url"): return best_loc.get("pdf_url")
                return oa_url
    except: pass
    return ""

def download_from_scihub(doi: str, filepath: Path, session: requests.Session) -> bool:
    """Try to download PDF from Sci-Hub mirrors."""
    if not doi: return False
    
    print(f"  -> Attempting Sci-Hub fallback for DOI: {doi}")
    for mirror in SCIHUB_MIRRORS:
        try:
            target_url = f"{mirror}/{doi}"
            r = session.get(target_url, timeout=REQUEST_TIMEOUT)
            if r.status_code != 200: continue
            
            soup = BeautifulSoup(r.text, "html.parser")
            # Sci-Hub usually puts the PDF in an iframe or an embed with id 'pdf' or 'book-viewer'
            pdf_tag = soup.find("iframe", id="pdf") or soup.find("embed", id="pdf")
            
            if pdf_tag and pdf_tag.get("src"):
                pdf_url = pdf_tag.get("src")
                if pdf_url.startswith("//"):
                    pdf_url = "https:" + pdf_url
                elif not pdf_url.startswith("http"):
                    pdf_url = urljoin(mirror, pdf_url)
                
                print(f"    [+] Found Sci-Hub PDF: {pdf_url}")
                return download_file(pdf_url, filepath, session)
        except Exception as e:
            print(f"    [!] Mirror {mirror} failed: {e}")
            continue
    return False

def download_file(url: str, filepath: Path, session: requests.Session) -> bool:
    if filepath.exists(): return True
    try:
        headers = session.headers.copy()
        headers["User-Agent"] = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        
        with session.get(url, stream=True, timeout=REQUEST_TIMEOUT, headers=headers) as r:
            r.raise_for_status()
            # Basic check to ensure it's not an HTML landing page
            if "text/html" in r.headers.get("Content-Type", "").lower() and "arxiv" not in url.lower():
                return False

            total_size = int(r.headers.get("content-length", 0))
            with filepath.open("wb") as f:
                if tqdm and total_size > 0:
                    with tqdm(total=total_size, unit="B", unit_scale=True, desc=filepath.name, leave=False) as pbar:
                        for chunk in r.iter_content(chunk_size=8192):
                            f.write(chunk)
                            pbar.update(len(chunk))
                else:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
        return True
    except Exception as e:
        if filepath.exists(): filepath.unlink()
        return False

def main():
    parser = argparse.ArgumentParser(description="Stage 03: Download PDF Papers with Sci-Hub")
    parser.add_argument("--project", required=True, help="Project directory path")
    args = parser.parse_args()

    project_dir = Path(args.project)
    input_file = project_dir / "02_verify" / "verified.csv"
    output_dir = project_dir / "03_pdfs"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if not input_file.exists():
        print(f"Error: Input file {input_file} not found.")
        sys.exit(1)

    session = requests.Session()
    # Mask as a real browser
    session.headers.update({"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"})

    with input_file.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    print(f"Starting Download Phase for project: {project_dir.name}")
    
    success_count, fail_count = 0, 0
    failed_rows = []

    for i, row in enumerate(rows, 1):
        title = row.get("title", f"Unknown_{i}")
        year = row.get("year", "0000")
        arxiv_id = row.get("arxiv_id", "").strip()
        doi = row.get("canonical_doi", "").strip() or row.get("doi", "").strip()
        pdf_url = row.get("pdf_url", "").strip()
        
        safe_title = clean_filename(title)
        filename = f"{year}_{clean_filename(arxiv_id or doi or title)}.pdf"
        filepath = output_dir / filename
        
        if filepath.exists():
            print(f"[{i}/{len(rows)}] EXISTS: {filename}")
            success_count += 1
            continue
            
        print(f"[{i}/{len(rows)}] Processing: {title[:60]}...")
        downloaded = False
        
        # 1. Official / ArXiv
        target_url = None
        if pdf_url and pdf_url.startswith("http"):
            target_url = pdf_url
            if "arxiv.org/abs/" in target_url: target_url = target_url.replace("/abs/", "/pdf/") + ".pdf"
        elif arxiv_id:
            target_url = f"https://export.arxiv.org/pdf/{arxiv_id.split('v')[0]}.pdf"
        
        if target_url:
            print(f"  -> Downloading from Official/ArXiv Source...")
            downloaded = download_file(target_url, filepath, session)
        
        # 2. OpenAlex OA
        if not downloaded and doi:
            print("  -> Searching Open Access via OpenAlex...")
            oa_url = get_oa_pdf_url(doi, session)
            if oa_url:
                downloaded = download_file(oa_url, filepath, session)
        
        # 3. Sci-Hub Fallback
        if not downloaded and doi:
            downloaded = download_from_scihub(doi, filepath, session)
            
        if downloaded:
            success_count += 1
            print(f"  [✓] Success!")
        else:
            fail_count += 1
            failed_rows.append(row)
            print(f"  [!] Failed to retrieve PDF.")
            
        time.sleep(SLEEP_BETWEEN)

    # Export failure list
    if failed_rows:
        failed_csv = output_dir / "failed_downloads.csv"
        with failed_csv.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["title", "doi", "url"], extrasaction='ignore')
            writer.writeheader()
            writer.writerows(failed_rows)
        print(f"\n[!] Wrote {len(failed_rows)} failed items to {failed_csv}")

    print(f"\nPhase Complete. Success: {success_count}, Failed: {fail_count}")

if __name__ == "__main__":
    main()
