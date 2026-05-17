# ========================================
# 第10周任务：双增强RAG问答核心（整合优化版）
# 融合知识图谱 + 向量文本双源检索
# 包含：动态权重调整、语义分块、上下文压缩
# ========================================
from llm.client import qwen_client
from agent.graph.kg_connect import TourismKGRetriever
from agent.graph.vector_rag import vector_retrieve, build_vector_context
from agent.graph.rerank_filter import optimize_retrieval_results, filter_useless_docs, simple_rerank, deduplicate_docs
from typing import Dict, Any, List
import logging

logger = logging.getLogger("DualRAGQA")

# 全局实例
kg_retriever = TourismKGRetriever()

QA_PROMPT = """
结合知识图谱结构化信息 + 文本知识库内容回答用户文旅问题

知识图谱结构化数据：
{kg_info}

文本参考资料：
{vec_context}

用户问题：{question}

回答要求：
1. 优先使用知识图谱中的真实数据（如开放时间、票价、交通信息）
2. 用文本内容补充完善答案，提供更丰富的背景信息
3. 回答简洁准确，分点清晰
4. 如果没有找到相关信息，请明确说明

回答：
"""

def classify_query(query: str) -> str:
    """
    查询分类：识别用户查询类型
    :param query: 用户查询
    :return: 查询类型
    """
    traffic_keywords = ["怎么去", "交通", "地铁", "公交", "路线", "怎么到达", "乘车"]
    if any(kw in query for kw in traffic_keywords):
        return "traffic"
    
    recommend_keywords = ["推荐", "一起玩", "附近", "周边", "还有什么"]
    if any(kw in query for kw in recommend_keywords):
        return "recommend"
    
    relic_keywords = ["文物", "历史", "古迹", "收藏", "年代"]
    if any(kw in query for kw in relic_keywords):
        return "relic"
    
    spot_keywords = ["景点", "景区", "门票", "开放时间", "票价"]
    if any(kw in query for kw in spot_keywords):
        return "spot"
    
    return "general"

def dynamic_weight_adjustment(query_type: str) -> float:
    """
    动态权重调整：根据查询类型自动调整知识图谱和向量检索的权重
    :param query_type: 查询类型
    :return: 知识图谱权重
    """
    weight_map = {
        "spot": 0.7,      # 景点查询：更依赖知识图谱
        "traffic": 0.8,    # 交通查询：高度依赖知识图谱
        "recommend": 0.6,  # 推荐查询：平衡使用
        "relic": 0.7,      # 文物查询：更依赖知识图谱
        "general": 0.4     # 普通查询：更依赖向量检索
    }
    return weight_map.get(query_type, 0.5)

def semantic_chunking(contexts: List[Dict], query_type: str) -> List[Dict]:
    """
    语义分块：根据查询类型对上下文进行重组
    :param contexts: 原始上下文列表
    :param query_type: 查询类型
    :return: 重组后的上下文
    """
    if not contexts:
        return contexts
    
    grouped = {
        "spot": [],
        "traffic": [],
        "recommend": [],
        "relic": [],
        "document": []
    }
    
    for ctx in contexts:
        ctx_type = ctx.get("type", "document")
        if ctx_type in grouped:
            grouped[ctx_type].append(ctx)
    
    priority_order = []
    if query_type == "traffic":
        priority_order = ["traffic", "spot", "document", "recommend", "relic"]
    elif query_type == "recommend":
        priority_order = ["recommend", "spot", "traffic", "document", "relic"]
    elif query_type == "relic":
        priority_order = ["relic", "spot", "document", "traffic", "recommend"]
    elif query_type == "spot":
        priority_order = ["spot", "traffic", "recommend", "document", "relic"]
    else:
        priority_order = ["spot", "document", "recommend", "traffic", "relic"]
    
    reordered = []
    for ctx_type in priority_order:
        reordered.extend(grouped.get(ctx_type, []))
    
    return reordered

def context_compression(contexts: List[Dict], max_length: int = 2000) -> List[Dict]:
    """
    上下文压缩：在保持关键信息的前提下减少上下文长度
    :param contexts: 原始上下文列表
    :param max_length: 最大总长度
    :return: 压缩后的上下文
    """
    if not contexts:
        return contexts
    
    current_length = sum(len(ctx.get("page_content", ctx.get("content", ""))) for ctx in contexts)
    
    if current_length <= max_length:
        return contexts
    
    contexts.sort(key=lambda x: x.get("score", 0), reverse=True)
    
    compressed = []
    remaining_length = max_length
    
    for ctx in contexts:
        content = ctx.get("page_content", ctx.get("content", ""))
        ctx_length = len(content)
        if remaining_length >= ctx_length:
            compressed.append(ctx)
            remaining_length -= ctx_length
        else:
            truncated_content = content[:remaining_length]
            compressed.append({**ctx, "page_content": truncated_content + "...", "truncated": True})
            break
    
    return compressed

async def dual_enhance_qa(question: str, include_optimization: bool = True) -> Dict[str, Any]:
    """
    双增强RAG问答：知识图谱 + 向量文本
    :param question: 用户问题
    :param include_optimization: 是否启用优化（动态权重、语义分块、上下文压缩）
    :return: 包含问答结果和检索来源的字典
    """
    logger.info(f"处理双增强RAG查询：{question}")
    
    # 查询分类和动态权重调整
    query_type = classify_query(question)
    kg_weight = dynamic_weight_adjustment(query_type)
    
    # 1. 知识图谱结构化检索
    kg_ctx = kg_retriever.get_kg_context(question)
    
    # 2. 向量文本检索
    vec_docs = vector_retrieve(question, top_k=5)
    
    # 3. 过滤+去重+重排优化
    vec_docs = optimize_retrieval_results(question, vec_docs, top_n=4)
    
    # 4. 语义分块（可选优化）
    if include_optimization:
        vec_docs = semantic_chunking(vec_docs, query_type)
    
    # 5. 上下文压缩（可选优化）
    if include_optimization:
        vec_docs = context_compression(vec_docs)
    
    vec_ctx = build_vector_context(vec_docs)
    
    # 6. 大模型统一生成回答
    prompt = QA_PROMPT.format(
        kg_info=kg_ctx if kg_ctx else "暂无结构化数据",
        vec_context=vec_ctx if vec_ctx else "暂无文本参考",
        question=question
    )
    
    try:
        answer = await qwen_client.generate(prompt, "tenant_001")
    except Exception as e:
        answer = f"抱歉，暂时无法回答您的问题：{str(e)}"
    
    return {
        "question": question,
        "answer": answer.strip(),
        "kg_knowledge": kg_ctx,
        "vector_reference": vec_ctx,
        "query_type": query_type,
        "kg_weight": kg_weight,
        "retrieval_summary": {
            "has_kg_data": bool(kg_ctx),
            "has_vector_data": bool(vec_ctx),
            "vector_doc_count": len(vec_docs)
        }
    }
