#!/usr/bin/env python3
"""
Stage 01: Literature Search (Pipeline Version)
------------------------------------------
Logic: 
1. Parse config from config.json or keywords.md.
2. Fetch data from S2, arXiv, CORE.
3. Save raw_papers.csv (all results).
4. Call ranker.py to score, sort, and truncate.
5. Save papers.csv (curated results).
"""

import argparse
import csv
import hashlib
import json
import os
import random
import re
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Iterable, List, Dict, Optional
from dotenv import load_dotenv

# Load Ranking Module
import sys
sys.path.append(str(Path(__file__).parent))
from ranker import rank_and_truncate

load_dotenv()
import requests
from tqdm import tqdm

# ---------- Configuration Defaults ----------
DEFAULT_YEAR_FROM = 2021
DEFAULT_LIMIT_PER_QUERY = 30
DEFAULT_MAX_RESULTS = 20

S2_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
S2_FIELDS = "title,authors,year,venue,abstract,externalIds,url,openAccessPdf"
ARXIV_URL = "http://export.arxiv.org/api/query"
CORE_URL = "https://api.core.ac.uk/v3/search/outputs"
ATOM_NS = {"a": "http://www.w3.org/2005/Atom"}

S2_API_KEY = os.environ.get("S2_API_KEY", "").strip()
CORE_API_KEY = os.environ.get("CORE_API_KEY", "").strip()

# ---------- Markdown Parser ----------

def parse_keywords_md(path: Path) -> Dict:
    """从 keywords.md 提取配置和关键词"""
    if not path.exists():
        return {}
    
    content = path.read_text(encoding="utf-8")
    config = {}
    
    # 解析配置参数
    year_from = re.search(r"-\s*\*\*Year From\*\*:\s*(\d+)", content)
    year_to = re.search(r"-\s*\*\*Year To\*\*:\s*(\d+)", content)
    max_results = re.search(r"-\s*\*\*Max Results\*\*:\s*(\d+)", content)
    limit_per = re.search(r"-\s*\*\*Limit Per Query\*\*:\s*(\d+)", content)
    
    if year_from: config["year_from"] = int(year_from.group(1))
    if year_to: config["year_to"] = int(year_to.group(1))
    if max_results: config["max_total_results"] = int(max_results.group(1))
    if limit_per: config["limit_per_query"] = int(limit_per.group(1))
    
    # 解析关键词表格
    queries = re.findall(r"\| \d+ \| `([^`]+)` \|", content)
    config["queries"] = queries
    
    return config

# ---------- API Fetchers (Simplified for Pipeline) ----------

def _request_with_retry(url, params, headers=None, max_retries=5):
    for attempt in range(max_retries):
        try:
            r = requests.get(url, params=params, headers=headers or {}, timeout=30)
            if r.status_code == 200: return r
            if r.status_code in (429, 500, 502, 503, 504):
                wait = 2.0 * (2 ** attempt) + random.uniform(0, 1)
                time.sleep(wait)
                continue
            return None
        except Exception:
            time.sleep(2.0 * (2 ** attempt))
    return None

def fetch_s2(query, year_from, year_to, limit):
    year_range = f"{year_from}-" if not year_to else f"{year_from}-{year_to}"
    params = {"query": query, "limit": limit, "year": year_range, "fields": S2_FIELDS}
    headers = {"x-api-key": S2_API_KEY} if S2_API_KEY else {}
    r = _request_with_retry(S2_URL, params, headers)
    if not r: return []
    out = []
    for p in r.json().get("data", []):
        out.append({
            "source": "semantic_scholar", "title": (p.get("title") or "").strip(),
            "authors": "; ".join(a.get("name", "") for a in (p.get("authors") or [])),
            "year": p.get("year"), "venue": p.get("venue") or "",
            "doi": (p.get("externalIds") or {}).get("DOI", ""),
            "url": p.get("url") or "", "abstract": (p.get("abstract") or "").strip(), "query": query
        })
    return out

def fetch_arxiv(query, year_from, year_to, limit):
    params = {"search_query": f"all:{query}", "max_results": limit, "sortBy": "relevance"}
    r = _request_with_retry(ARXIV_URL, params)
    if not r: return []
    try: root = ET.fromstring(r.text)
    except: return []
    out = []
    for entry in root.findall("a:entry", ATOM_NS):
        pub = entry.findtext("a:published", default="", namespaces=ATOM_NS)
        year = int(pub[:4]) if pub[:4].isdigit() else None
        if year and (year < year_from or (year_to and year > year_to)): continue
        out.append({
            "source": "arxiv", "title": entry.findtext("a:title", namespaces=ATOM_NS).strip(),
            "authors": "; ".join(a.findtext("a:name", namespaces=ATOM_NS) for a in entry.findall("a:author", ATOM_NS)),
            "year": year, "venue": "arXiv", "abstract": entry.findtext("a:summary", namespaces=ATOM_NS).strip(), "query": query
        })
    return out

def fetch_core(query, year_from, year_to, limit):
    if not CORE_API_KEY: return []
    params = {"q": f'title:("{query}")', "limit": limit}
    r = _request_with_retry(CORE_URL, params, {"Authorization": f"Bearer {CORE_API_KEY}"})
    if not r: return []
    out = []
    for p in r.json().get("results", []):
        year = p.get("yearPublished")
        if year and (int(year) < year_from or (year_to and int(year) > year_to)): continue
        out.append({
            "source": "core", "title": p.get("title"), "authors": "; ".join(a.get("name", "") for a in (p.get("authors") or [])),
            "year": year, "venue": p.get("publisher") or "CORE", "abstract": p.get("abstract"), "query": query
        })
    return out

# ---------- Utility ----------

def dedup(records):
    seen = {}
    for r in records:
        key = (r.get("title") or "").lower().strip()
        if key not in seen: seen[key] = r
    return list(seen.values())

def save_csv(path, records):
    fields = ["source", "title", "authors", "year", "venue", "doi", "url", "abstract", "query", "relevance_score"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(records)

# ---------- Main ----------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project_dir", type=str, required=True)
    args = parser.parse_args()
    project_path = Path(args.project_dir)
    
    # 1. Load Config
    md_cfg = parse_keywords_md(project_path / "keywords.md")
    year_from = md_cfg.get("year_from", DEFAULT_YEAR_FROM)
    year_to = md_cfg.get("year_to")
    limit_per = md_cfg.get("limit_per_query", DEFAULT_LIMIT_PER_QUERY)
    max_results = md_cfg.get("max_total_results", DEFAULT_MAX_RESULTS)
    queries = md_cfg.get("queries", [])
    
    if not queries:
        print("Error: No queries found in keywords.md")
        return

    # 2. Fetch Data
    all_raw = []
    for q in tqdm(queries, desc="Searching APIs"):
        all_raw += fetch_s2(q, year_from, year_to, limit_per)
        all_raw += fetch_arxiv(q, year_from, year_to, limit_per)
        all_raw += fetch_core(q, year_from, year_to, limit_per)
    
    deduped = dedup(all_raw)
    out_dir = project_path / "01_search"
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # 3. Save Raw Data
    save_csv(out_dir / "raw_papers.csv", deduped)
    print(f"Saved {len(deduped)} raw records to raw_papers.csv")
    
    # 4. Rank and Truncate
    curated = rank_and_truncate(deduped, queries, max_results)
    
    # 5. Save Curated Data
    save_csv(out_dir / "papers.csv", curated)
    print(f"Ranked and saved top {len(curated)} records to papers.csv")

if __name__ == "__main__":
    main()
