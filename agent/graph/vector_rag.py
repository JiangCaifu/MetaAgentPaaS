# ========================================
# 第10周任务：向量文本RAG模块
# ========================================
from db.qdrant_vector_store import QdrantVectorStore
from typing import List, Dict
import os

DB_PATH = "./local_qdrant_data"
COLLECTION_NAME = "test_collection"

def init_vector_db() -> QdrantVectorStore:
    """初始化文旅向量知识库"""
    return QdrantVectorStore(
        collection_name=COLLECTION_NAME,
        path=DB_PATH,
        vector_dimension=1024
    )

def vector_retrieve(query: str, top_k: int = 5) -> List[Dict]:
    """向量检索：从Qdrant中检索相似文档"""
    db = init_vector_db()
    results = db.search(query, top_k=top_k)
    
    # 格式化结果，兼容LangChain格式
    formatted_results = []
    for res in results:
        formatted_results.append({
            "page_content": res.get("content", ""),
            "metadata": res.get("metadata", {}),
            "score": res.get("score", 0.0)
        })
    
    return formatted_results

def build_vector_context(docs: List[Dict]) -> str:
    """将检索结果拼接为上下文文本"""
    context_parts = []
    for i, doc in enumerate(docs, 1):
        content = doc.get("page_content", "")
        if content:
            source = doc.get("metadata", {}).get("name", f"文档{i}")
            context_parts.append(f"【{source}】\n{content}")
    return "\n\n".join(context_parts)
