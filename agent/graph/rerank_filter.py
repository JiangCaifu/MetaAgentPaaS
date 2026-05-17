# ========================================
# 第10周任务：检索重排 + 无用过滤模块
# ========================================
from typing import List, Dict
import numpy as np

def filter_useless_docs(docs: List[Dict]) -> List[Dict]:
    """过滤空内容、低价值文档"""
    valid = []
    for doc in docs:
        content = doc.get("page_content", "").strip()
        # 过滤条件：内容长度>20，不包含"暂无"等低价值关键词
        if len(content) > 20 and "暂无" not in content and "无相关" not in content:
            valid.append(doc)
    return valid

def simple_rerank(query: str, docs: List[Dict], top_n: int = 4) -> List[Dict]:
    """
    简单重排序：基于关键词匹配和相似度分数
    :param query: 用户查询
    :param docs: 检索结果列表
    :param top_n: 返回前N个结果
    :return: 重排序后的结果
    """
    if not docs:
        return docs
    
    scored_docs = []
    
    for doc in docs:
        content = doc.get("page_content", "")
        base_score = doc.get("score", 0.5)
        
        # 关键词匹配加分
        query_words = query.replace("?", "").replace("？", "").split()
        match_count = sum(1 for word in query_words if word in content)
        keyword_score = match_count * 0.15
        
        # 长度归一化
        length_penalty = min(1.0, len(content) / 200)
        
        # 综合分数
        total_score = base_score * 0.6 + keyword_score + length_penalty * 0.2
        
        scored_docs.append((total_score, doc))
    
    # 按分数降序排序
    scored_docs.sort(reverse=True, key=lambda x: x[0])
    
    # 返回前top_n个
    return [doc for _, doc in scored_docs[:top_n]]

def deduplicate_docs(docs: List[Dict]) -> List[Dict]:
    """去重：移除内容重复的文档"""
    seen_contents = set()
    unique_docs = []
    
    for doc in docs:
        content = doc.get("page_content", "")[:100]  # 取前100字符作为去重依据
        if content not in seen_contents:
            seen_contents.add(content)
            unique_docs.append(doc)
    
    return unique_docs

def optimize_retrieval_results(query: str, docs: List[Dict], top_n: int = 4) -> List[Dict]:
    """
    完整的检索结果优化流程：过滤 → 去重 → 重排
    :param query: 用户查询
    :param docs: 原始检索结果
    :param top_n: 最终返回数量
    :return: 优化后的结果
    """
    # 1. 过滤低价值文档
    filtered = filter_useless_docs(docs)
    
    # 2. 去重
    deduplicated = deduplicate_docs(filtered)
    
    # 3. 重排序
    reranked = simple_rerank(query, deduplicated, top_n=top_n)
    
    return reranked
