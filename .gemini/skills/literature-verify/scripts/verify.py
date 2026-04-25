#!/usr/bin/env python3
"""
Stage 02: Metadata Verification
-------------------------------
Goal: Ensure accuracy of metadata (DOI, Year, Source).
Logic: Cross-check against CrossRef, arXiv, and OpenAlex.
Input:  projects/{project}/01_search/papers.csv
Output: projects/{project}/02_verify/verified.csv
"""

import argparse
import csv
import hashlib
import json
import os
from dotenv import load_dotenv
load_dotenv()
import re
import sys
import time
import unicodedata
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import quote_plus

import requests

try:
    from rapidfuzz import fuzz
except ImportError:
    print("Error: 'rapidfuzz' is required. Install it via: pip install rapidfuzz")
    sys.exit(1)

# API Constants
CROSSREF_BASE = "https://api.crossref.org"
OPENALEX_BASE = "https://api.openalex.org"
ARXIV_BASE = "http://export.arxiv.org/api/query"
ARXIV_DOI_PREFIX = "10.48550/arxiv."

# Thresholds
FUZZ_ACCEPT = 85          # >= this Score -> Verified
FUZZ_REVIEW = 70          # [70, 85) -> Review needed
YEAR_TOLERANCE = 1
REQUEST_TIMEOUT = 20
SLEEP_BETWEEN = 0.15      # Rate limiting
ARXIV_ATOM = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}

class Cache:
    """File-based cache for API results."""
    def __init__(self, cache_dir: Path):
        cache_dir.mkdir(parents=True, exist_ok=True)
        self.dir = cache_dir

    def _path(self, key: str) -> Path:
        h = hashlib.sha1(key.encode("utf-8")).hexdigest()
        return self.dir / f"{h}.json"

    def get(self, key: str):
        p = self._path(key)
        if p.exists():
            try:
                return json.loads(p.read_text(encoding="utf-8"))
            except: return None
        return None

    def set(self, key: str, value):
        self._path(key).write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")

def norm(s: str) -> str:
    """Normalize string for comparison."""
    if not s: return ""
    s = "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))
    s = s.lower()
    s = re.sub(r"[^\w\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()

def author_parts(raw_authors):
    """Normalize authors to (last_name, initial)."""
    if isinstance(raw_authors, str):
        items = [a.strip() for a in re.split(r"[;,]", raw_authors) if a.strip()]
    else:
        items = raw_authors
    out = []
    for a in items:
        a = "".join(c for c in unicodedata.normalize("NFKD", a) if not unicodedata.combining(c)).strip()
        if "," in a:
            last, first = a.split(",", 1)
            last, first = last.strip().lower(), first.strip()
        else:
            parts = a.split()
            last = parts[-1].lower() if parts else ""
            first = parts[0] if len(parts) > 1 else ""
        out.append((last, (first[:1] or "").lower()))
    return out

def authors_overlap(row_authors, cand_authors):
    r_parts = author_parts(row_authors)
    c_parts = author_parts(cand_authors)
    if not r_parts or not c_parts: return False
    c_map = {}
    for l, i in c_parts: c_map.setdefault(l, set()).add(i)
    for l, i in r_parts:
        if l in c_map:
            if not i or not any(c_map[l]) or i in c_map[l]: return True
    return False

def get_crossref_doi(doi, session, cache):
    key = f"cr:doi:{doi.lower()}"
    cached = cache.get(key)
    if cached: return cached
    try:
        r = session.get(f"{CROSSREF_BASE}/works/{quote_plus(doi)}", timeout=REQUEST_TIMEOUT)
        if r.status_code == 200:
            msg = r.json().get("message", {})
            cache.set(key, msg)
            return msg
    except: pass
    return None

def get_crossref_title(title, session, cache):
    key = f"cr:title:{norm(title)}"
    cached = cache.get(key)
    if cached: return cached
    try:
        r = session.get(f"{CROSSREF_BASE}/works", params={"query.title": title, "rows": 3}, timeout=REQUEST_TIMEOUT)
        if r.status_code == 200:
            items = r.json().get("message", {}).get("items", [])
            cache.set(key, items)
            return items
    except: pass
    return []

def get_openalex_title(title, session, cache):
    key = f"oa:title:{norm(title)}"
    cached = cache.get(key)
    if cached: return cached
    try:
        r = session.get(f"{OPENALEX_BASE}/works", params={"search": title, "per-page": 3}, timeout=REQUEST_TIMEOUT)
        if r.status_code == 200:
            items = r.json().get("results", [])
            cache.set(key, items)
            return items
    except: pass
    return []

def get_arxiv_id(aid, session, cache):
    key = f"ax:id:{aid.lower()}"
    cached = cache.get(key)
    if cached: return cached
    try:
        r = session.get(ARXIV_BASE, params={"id_list": aid, "max_results": 1}, timeout=REQUEST_TIMEOUT)
        root = ET.fromstring(r.text)
        entry = root.find("atom:entry", ARXIV_ATOM)
        if entry is None: return None
        title = " ".join((entry.find("atom:title", ARXIV_ATOM).text or "").split())
        authors = [au.find("atom:name", ARXIV_ATOM).text.strip() for au in entry.findall("atom:author", ARXIV_ATOM)]
        year = entry.find("atom:published", ARXIV_ATOM).text[:4]
        doi_el = entry.find("arxiv:doi", ARXIV_ATOM)
        doi = doi_el.text.strip() if doi_el is not None else ""
        res = {"title": title, "authors": authors, "year": year, "doi": doi, "venue": "arXiv"}
        cache.set(key, res)
        return res
    except: pass
    return None

def extract_cr(msg):
    if not msg: return None
    return {
        "title": (msg.get("title") or [""])[0],
        "authors": [f"{a.get('given','')} {a.get('family','')}".strip() for a in msg.get("author", [])],
        "year": str(((msg.get("issued") or {}).get("date-parts") or [[None]])[0][0] or ""),
        "doi": msg.get("DOI", ""),
        "venue": (msg.get("container-title") or [""])[0]
    }

def extract_oa(item):
    if not item: return None
    return {
        "title": item.get("display_name") or "",
        "authors": [a.get("author", {}).get("display_name", "") for a in item.get("authorships", [])],
        "year": str(item.get("publication_year") or ""),
        "doi": (item.get("doi") or "").replace("https://doi.org/", ""),
        "venue": ((item.get("primary_location") or {}).get("source") or {}).get("display_name") or ""
    }

def verify_paper(row, session, cache):
    doi = (row.get("doi") or "").strip()
    arxiv_id = (row.get("arxiv_id") or "").strip()
    if not arxiv_id and doi.lower().startswith(ARXIV_DOI_PREFIX):
        arxiv_id = doi[len(ARXIV_DOI_PREFIX):]

    res = {"verified": "no", "verify_source": "", "canonical_title": "", "fuzz_score": 0, "conflict_reason": ""}

    def evaluate(cand, source):
        if not cand: return False
        score = fuzz.token_set_ratio(norm(row["title"]), norm(cand["title"]))
        reasons = []
        if score < FUZZ_REVIEW: reasons.append("low_title_fuzz")
        if not authors_overlap(row.get("authors", ""), cand["authors"]): reasons.append("author_mismatch")
        
        row_year = str(row.get("year",""))[:4]
        if row_year and cand["year"] and abs(int(row_year) - int(cand["year"])) > YEAR_TOLERANCE:
            reasons.append("year_mismatch")
        
        res.update({
            "verify_source": source,
            "canonical_title": cand["title"],
            "canonical_authors": "; ".join(cand["authors"]),
            "canonical_year": cand["year"],
            "canonical_doi": cand["doi"],
            "canonical_venue": cand["venue"],
            "fuzz_score": score
        })
        if score >= FUZZ_ACCEPT and not reasons:
            res["verified"] = "yes"
            return True
        res["conflict_reason"] = ";".join(reasons)
        return False

    # 1. arXiv Check
    if arxiv_id:
        if evaluate(get_arxiv_id(arxiv_id, session, cache), "arxiv"): return res
    
    # 2. DOI Check
    if doi:
        if evaluate(extract_cr(get_crossref_doi(doi, session, cache)), "crossref_doi"): return res

    # 3. Title Search
    for item in get_crossref_title(row["title"], session, cache):
        if evaluate(extract_cr(item), "crossref_title"): return res
    
    for item in get_openalex_title(row["title"], session, cache):
        if evaluate(extract_oa(item), "openalex_title"): return res
        
    return res

def main():
    parser = argparse.ArgumentParser(description="Stage 02: Metadata Verification")
    parser.add_argument("--project", required=True, help="Project directory path")
    parser.add_argument("--email", help="Contact email for CrossRef (overrides config)")
    args = parser.parse_args()

    project_dir = Path(args.project)
    input_file = project_dir / "01_search" / "papers.csv"
    output_dir = project_dir / "02_verify"
    output_dir.mkdir(exist_ok=True)
    
    if not input_file.exists():
        print(f"Error: Input file {input_file} not found. Run Stage 01 first.")
        sys.exit(1)

    # Resolve email
    email = args.email
    config_path = project_dir / "config.json"
    if not email and config_path.exists():
        try:
            config = json.loads(config_path.read_text())
            email = config.get("contact_email")
        except: pass
    
    if not email:
        print("Warning: No contact email provided. Using default.")
        email = "researcher@example.com"

    session = requests.Session()
    session.headers.update({"User-Agent": f"ResearchWorkflow/1.0 (mailto:{email})"})
    cache = Cache(project_dir / "02_verify" / "_cache")

    with input_file.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = reader.fieldnames

    print(f"Verifying {len(rows)} papers for project: {project_dir.name}...")
    
    verified_rows, conflict_rows = [], []
    extra_fields = ["verified", "verify_source", "canonical_title", "canonical_authors", "canonical_year", "canonical_doi", "canonical_venue", "fuzz_score", "conflict_reason"]
    
    for i, row in enumerate(rows, 1):
        print(f"[{i}/{len(rows)}] {row.get('title','')[:60]}...", end="\r")
        res = verify_paper(row, session, cache)
        full_row = {**row, **res}
        if res["verified"] == "yes":
            verified_rows.append(full_row)
        else:
            conflict_rows.append(full_row)
        time.sleep(SLEEP_BETWEEN)

    # Save outputs
    out_fields = list(fieldnames) + extra_fields
    with (output_dir / "verified.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=out_fields)
        writer.writeheader()
        writer.writerows(verified_rows)
    
    with (output_dir / "conflicts.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=out_fields)
        writer.writeheader()
        writer.writerows(conflict_rows)

    print(f"\nVerification complete:")
    print(f"- Verified : {len(verified_rows)} -> {output_dir}/verified.csv")
    print(f"- Conflicts: {len(conflict_rows)} -> {output_dir}/conflicts.csv")

if __name__ == "__main__":
    main()
