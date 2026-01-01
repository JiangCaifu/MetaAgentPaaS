from db.qdrant_vector_store import QdrantVectorStore
from fastapi import FastAPI
from pydantic import BaseModel
from db.qdrant_vector_store import QdrantVectorStore

app = FastAPI(title="MetaAgentPaaS RAG API")
vector_store = QdrantVectorStore()

# 替换为你的 LLM 问答函数
def llm_generate(query: str, context: str) -> str:
    """
    调用 LLM，基于检索到的上下文生成回答
    :param query: 用户问题
    :param context: 检索到的文本块拼接
    :return: LLM 生成的回答
    """
    prompt = f"""
    基于以下上下文回答用户问题，不要编造信息。
    上下文：{context}
    用户问题：{query}
    回答：
    """
    # 此处替换为你的 LLM API 调用代码
    return f"根据上下文，关于'{query}'的回答是：{context[:100]}..."

class RAGQuery(BaseModel):
    query: str
    top_k: int = 3

@app.post("/rag/qa")
def rag_qa(request: RAGQuery):
    # 1. 向量检索
    search_results = vector_store.search(request.query, top_k=request.top_k)
    # 2. 拼接上下文
    context = "\n".join([res["content"] for res in search_results])
    # 3. LLM 生成回答
    answer = llm_generate(request.query, context)
    return {
        "query": request.query,
        "answer": answer,
        "contexts": search_results
    }

# 启动命令：uvicorn rag_api:app --reload