#!/usr/bin/env python3
import re
from typing import List, Dict

def calculate_relevance_score(record: Dict, queries: List[str]) -> float:
    """
    计算论文与检索词的相关度分数。
    评分逻辑：
    1. 将所有查询词拆解为单词集（去重、小写）。
    2. 标题 (Title) 命中权重: 2.0
    3. 摘要 (Abstract) 命中权重: 1.0
    """
    title = (record.get("title") or "").lower()
    abstract = (record.get("abstract") or "").lower()
    
    # 提取查询词中的核心单词
    search_terms = set()
    for q in queries:
        terms = re.findall(r"\w+", q.lower())
        search_terms.update(terms)
    
    score = 0.0
    if not search_terms:
        return score

    for term in search_terms:
        # 标题匹配
        title_matches = len(re.findall(rf"\b{re.escape(term)}\b", title))
        score += title_matches * 2.0
        
        # 摘要匹配
        abstract_matches = len(re.findall(rf"\b{re.escape(term)}\b", abstract))
        score += abstract_matches * 1.0
        
    # 年份微调：更近的论文获得极小的加分，作为同分时的破局指标
    year = record.get("year")
    if year:
        try:
            score += int(year) * 0.0001
        except:
            pass
            
    return round(score, 4)

def rank_and_truncate(records: List[Dict], queries: List[str], max_results: int = None) -> List[Dict]:
    """
    对记录进行打分、排序并截断。
    """
    for r in records:
        r["relevance_score"] = calculate_relevance_score(r, queries)
    
    # 按分数降序排列
    sorted_records = sorted(records, key=lambda x: x["relevance_score"], reverse=True)
    
    if max_results and max_results > 0:
        return sorted_records[:max_results]
    
    return sorted_records
