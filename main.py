# ====================== 1. 日志初始化（最顶部，确保最早执行） ======================
import logging
import os
import uuid
import json
from pydantic import BaseModel

# 第11周新增：在最开始初始化日志系统
try:
    from agent.utils.logging_config import setup_logging, agent_logger
    setup_logging("INFO")
    logger = logging.getLogger("AgentLog")
    logger.info("✅ 第11周日志系统初始化成功")
except Exception as e:
    # 如果日志系统初始化失败，使用默认日志
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("AgentLog")
    logger.warning(f"⚠️ 日志系统初始化失败，使用默认配置：{str(e)}")

from db.qdrant_vector_store import QdrantVectorStore
from agent.tools.weather_tool import WeatherTool
# 新增：导入图谱服务
# 知识图谱服务（NetworkX版，纯Python实现）
_kg_service = None

def get_kg_service():
    """懒加载知识图谱服务（NetworkX版，无需Neo4j）"""
    global _kg_service
    if _kg_service is None:
        try:
            from agent.graph.kg_service import TourismKnowledgeGraph
            _kg_service = TourismKnowledgeGraph()
            logger.info("✅ 知识图谱服务初始化成功（NetworkX版）")
        except Exception as e:
            logger.warning(f"⚠️ 知识图谱服务初始化失败：{str(e)}")
            _kg_service = None
    return _kg_service
from agent.graph.state import TourGraphState
from agent.graph.workflow import build_tour_graph
from utils.logger_config import setup_logger

# ====================== 第7周新版 LangGraph 接口 ======================
from agent.graph.workflow import build_tour_graph, TourGraphState

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Dict, List
from fastapi import FastAPI, Depends, HTTPException, Header
from pydantic import BaseModel
import aiohttp
import asyncio
# main.py 中新增以下代码（放在现有接口之后、启动服务之前）
from pydantic import BaseModel
# 导入文旅Agent核心逻辑
from agent.core.tourism_agent import call_tourism_agent
from agent.core.clean_tourism_agent import  call_clean_tourism_agent

# 自定义模块（新增）
from utils.logger_config import setup_logger
from prompt.templates import PromptManager
from db.operations import ConversationDB
from llm.client import qwen_client
from llm.embedding_client import BailianEmbeddingClient

# 配置日志（输出到控制台+文件）
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("metaagentpaas.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
#logger = logging.getLogger("MetaAgentPaaS")
# ====================== 2. 日志初始化（优化版） ======================
logger = setup_logger(name="MetaAgentPaaS", log_file="metaagentpaas.log")
# ==============================
class TourismQueryRequest(BaseModel):
    """文旅问答请求模型"""
    user_query: str = Field(..., description="用户查询内容")
    tenant_id: str = Field(default="tenant_001", description="租户ID")
    tenant_name: str = Field(default="文旅平台", description="租户名称")
    conversation_id: str = Field(default="", description="会话ID，用于多轮对话")
    history: Optional[List[Dict]] = Field(default_factory=list, description="历史对话记录")
    image_url: Optional[str] = Field(default=None, description="图片URL，提供后启用多模态图文问答")

class TourismQueryResponse(BaseModel):
    """文旅问答响应模型"""
    code: int = Field(default=200, description="响应码 200成功/500失败")
    msg: str = Field(default="success", description="响应信息")
    data: Dict = Field(default_factory=dict, description="响应数据")
    request_id: str = Field(default="", description="请求ID，用于问题排查")
# ====================== 2. 核心配置（硬编码兜底，避免.env依赖） ======================
# 租户配置（固定值，确保能匹配）
TENANT_CONFIG: Dict[str, Dict] = {
    "tenant_001": {
        "name": "文旅行业租户",
        "token": "token_001",
        "is_active": True,
        "agents": ["tourism_recommend_agent", "tourism_qa_agent"],
        "rate_limit": 100
    },
    "tenant_002": {
        "name": "制造行业租户",
        "token": "token_002",
        "is_active": True,
        "agents": ["factory_monitor_agent", "equipment_qa_agent"],
        "rate_limit": 50
    }
}

# 初始化新增组件（全局单例）
prompt_manager = PromptManager()
embedding_client = BailianEmbeddingClient()
client = BailianEmbeddingClient()
conversation_db = ConversationDB()


# ====================== 3. 模型定义 ======================
class AgentTaskRequest(BaseModel):
    agent_ids: List[str] = Field(..., description="要调用的Agent ID列表")
    user_query: str = Field(..., min_length=1, max_length=500, description="用户查询")
    context: Optional[Dict] = Field(default=None, description="上下文（如location等）")
    conversation_id: Optional[str] = Field(default=None, description="对话ID，用于多轮对话")


class AgentTaskResponse(BaseModel):
    code: int = 200
    msg: str = "success"
    data: Dict = {
        "tenant_info": {},
        "agent_results": [],
        "aggregated_result": "",
        "conversation_id": ""  # 新增：返回对话ID
    }

class EmbeddingRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=1000, description="待向量化的文本")

# 定义Agent工具调用请求模型（与现有模型风格一致）
class TourismAgentRequest(BaseModel):
    user_query: str = Field(..., min_length=1, max_length=500, description="用户文旅相关查询")

# ====================== 4. 租户鉴权（核心修复：兼容所有请求头格式） ======================
async def get_current_tenant(
        # 关键修复：alias兼容所有常见格式，default强制兜底
        tenant_id: str = Header(default="tenant_001", alias="X-Tenant-ID"),
        tenant_token: str = Header(default="token_001", alias="X-Tenant-Token")
):
    """
    租户鉴权：
    1. 默认值兜底（tenant_001/token_001），避免None
    2. alias兼容X-Tenant-ID/tenant-id/x_tenant_id等格式
    """
    logger.info(f"接收到的租户参数：tenant_id={tenant_id}, tenant_token={tenant_token}")

    # 1. 检查租户是否存在
    tenant = TENANT_CONFIG.get(tenant_id)
    if not tenant:
        logger.error(f"租户不存在：{tenant_id}")
        raise HTTPException(status_code=404, detail=f"租户ID {tenant_id} 不存在")

    # 2. 检查租户状态和令牌
    if not tenant["is_active"]:
        raise HTTPException(status_code=403, detail=f"租户 {tenant_id} 已停用")
    if tenant["token"] != tenant_token:
        raise HTTPException(status_code=403, detail="租户令牌错误")

    # 3. 返回租户配置+租户ID（关键：把tenant_id一起返回）
    return {
        "tenant_id": tenant_id,
        **tenant  # 合并租户配置
    }


# ====================== 5. Agent调用（集成Prompt模板+格式容错） ======================
async def call_single_agent(agent_id: str, query: str, context: Dict, tenant_info: Dict) -> Dict:
    """调用单个Agent（集成百炼大模型+简化格式容错，保留原有逻辑不变）"""
    # 初始化默认结果（提前兜底，避免异常后无返回值）
    default_result = {
        "agent_id": agent_id,
        "status": "failed",
        "response": "Agent调用初始化异常",
        "cost_time": 0.0
    }
    try:
        # 新增：先打印前置参数，验证是否存在
        logger.info(f"前置参数校验：agent_id={agent_id}, query={query}, tenant_info={tenant_info}, context={context}")
        # 新增：校验 tenant_info 关键键是否存在
        if "name" not in tenant_info:
            logger.error(f"tenant_info 缺少 'name' 键，当前 tenant_info：{tenant_info}")
            # 手动抛出异常，明确错误
            raise KeyError(f"tenant_info 中不存在键 'name'")
        # 1. 提取租户ID和城市（你的原有逻辑，完全保留）
        tenant_id = tenant_info["tenant_id"]
        tenant_name = tenant_info["name"]
        city = context.get("location", "北京") if context else "北京"
        prompt= prompt_manager.render_prompt(agent_id, tenant_name, query, city)
        #logger.info(f"传给百炼大模型的Prompt：{prompt}")

        # 原有Prompt分支（不使用模板的prompt）
        """
        # 2. 根据Agent类型构造专属提示词（你的原有逻辑，无修改）
        if agent_id == "tourism_recommend_agent":
            prompt = f\"""你是{tenant_info['name']}的专属文旅推荐Agent，用户需求：{query}，目标城市：{city}
            请按照以下要求回复：
            1. 推荐3-5个该城市的5A景区；
            2.每个景区包含「名称、门票价格、推荐理由」；
            3.语言简洁，分点列出，不要多余话术；
            4. 仅回复推荐内容，无需其他开头/结尾。\"""
        else:
            prompt = f\"""
你是{tenant_info['name']}的专属Agent，用户问题：{query}，请直接、简洁地回答。\"""
        """
        if agent_id == "tourism_recommend_agent":
            #prompt = f"""你是{tenant_name}的专属文旅推荐Agent，用户需求：{query}，目标城市：{city}
        #请严格按照以下要求回复，仅返回文本内容，无需多余格式：
        #1.  推荐3-5个该城市的5A景区；
        #2.  每个景区包含「名称、门票价格、推荐理由」；
        #3.  语言简洁，分点列出（用1. 2. 3. 格式）；
        #4.  仅回复推荐内容，不要其他开头、结尾或多余话术。"""
            prompt = prompt
        else:
            prompt = f"你是{tenant_name}的专属Agent，用户问题：{query}，请直接、简洁地回答。"

            # 放弃模板调用（若必须使用模板，可注释上方代码，保留下方代码）
            # prompt = prompt_manager.render_prompt(agent_id, tenant_name, query, city)

            # ===== 关键修改2：大模型调用增加异常捕获（单独包裹，避免整体报错） =====
        llm_response = ""

        # 2. 调用大模型（你的原有逻辑，完全保留）
        try:
            # 单独捕获大模型调用异常
            # logger.info(f"传给百炼大模型的Prompt：{prompt}")
            llm_response = await qwen_client.generate(prompt, tenant_id)
        except Exception as e:
            # 大模型调用失败时，手动赋值兜底响应
            logger.warning(f"大模型调用异常，使用兜底响应：{str(e)}")
            llm_response = "暂无法获取推荐结果（大模型调用异常）"

        # ===== 仅新增：简化格式容错逻辑（无分支，一行判断+兜底，不影响原有逻辑） =====
        # 针对 tourism_recommend_agent 做格式校验（仅一行判断，无多余分支）
        if agent_id == "tourism_recommend_agent":
            # 清理多余换行和空格
            clean_response= llm_response.strip().replace("\n", "").replace("  ", "").replace("\\n", "")
            # 直接封装为有效响应（无需判断JSON，避免解析报错）
            final_response = json.dumps({
                "recommendations": clean_response if clean_response else [],
                "desc": "北京5A景区推荐结果" if clean_response else "暂无法获取有效推荐",
                "raw": llm_response
            }, ensure_ascii=False)
        else:
            final_response = llm_response

        # 3. 返回结果（你的原有格式，完全保留）
        return {
            "agent_id": agent_id,
            "status": "success",
            "response": final_response,
            "cost_time": 0.5
        }
    except Exception as e:
        logger.error(f"Agent调用失败：{agent_id}，错误：{str(e)}")
        # 最终异常兜底
        error_msg = f"调用失败：{str(e)}"
        logger.error(f"Agent调用失败：{agent_id}，错误：{error_msg}")
        default_result["response"] = error_msg
        return default_result

# ====================== 6. FastAPI应用初始化 ======================
app = FastAPI(
    title="MetaAgentPaaS",
    description="企业级多模态AI Agent智能中台（集成Prompt+Embedding+数据库）",
    version="2.0.0"
)

# ====================== 第11周新增：日志中间件 ======================
try:
    from agent.utils.log_middleware import LogMiddleware
    app.add_middleware(LogMiddleware)
    logger.info("✅ 第11周日志中间件加载成功")
except Exception as e:
    logger.warning(f"⚠️ 日志中间件加载失败：{str(e)}")

# ====================== 云资源管理路由 ======================
try:
    from cloud.api import router as cloud_router
    app.include_router(cloud_router)
    logger.info("✅ 云资源管理API加载成功")
except Exception as e:
    logger.warning(f"⚠️ 云资源管理API加载失败：{str(e)}")

# ====================== 多模态问答路由 ======================
try:
    from multimodal.api import router as multimodal_router
    app.include_router(multimodal_router)
    logger.info("✅ 多模态问答API加载成功")
except Exception as e:
    logger.warning(f"⚠️ 多模态问答API加载失败：{str(e)}")

# ====================== 缓存管理路由 ======================
try:
    from cache.cache_api import router as cache_router
    app.include_router(cache_router)
    logger.info("✅ 缓存管理API加载成功")
except Exception as e:
    logger.warning(f"⚠️ 缓存管理API加载失败：{str(e)}")

# ====================== Redis缓存客户端 ======================
try:
    from cache.redis_client import redis_cache
    logger.info(f"✅ Redis缓存初始化：{'Redis' if redis_cache.is_available else '内存降级'}模式")
except Exception as e:
    logger.warning(f"⚠️ Redis缓存初始化失败：{str(e)}")
    redis_cache = None


# ====================== 启动时自动清缓存（防止代码更新后返回旧数据） ======================
@app.on_event("startup")
async def startup_clear_cache():
    """服务启动时清空Redis缓存，确保代码/模型更新后不会返回旧数据"""
    if redis_cache and redis_cache.is_available:
        redis_cache.clear_all()
        logger.info("✅ 启动时已清空Redis缓存（防止旧数据残留）")
    elif redis_cache:
        redis_cache._memory_cache.clear()
        logger.info("✅ 启动时已清空内存缓存")


# ====================== 7. 健康检查接口 ======================
@app.get("/health", tags=["基础接口"])
async def health_check():
    """健康检查：新增数据库和Embedding连通性检查"""
    try:
        # 检查数据库
        conversation_db.get_conversations("tenant_001")
        # 检查Embedding API
        embedding_client.get_embedding("健康检查")
        return {
        "status": "healthy",
        "service": "MetaAgentPaaS",
        "version": "2.0.0",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "dependencies": {
                "database": "connected",
                "embedding_api": "connected"
            }
    }
    except Exception as e:
        logger.error(f"健康检查失败：{str(e)}")
        raise HTTPException(status_code=500, detail=f"服务异常：{str(e)}")

# ====================== 9. 新增：文本向量化接口 ======================
@app.post("/api/v2/text/embedding", tags=["工具接口"])
async def text_embedding(request: EmbeddingRequest):
    """文本向量化接口（集成百炼Embedding API）"""
    try:
        vector = embedding_client.get_embedding(request.text)
        #vector = embedding_client.get_embedding("北京故宫是明清两代的宫殿")
        return {
            "code": 200,
            "msg": "success",
            "data": {
                "text": request.text,
                "vector": vector,
                "dimension": len(vector)
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"向量化失败：{str(e)}")

# ====================== 10. 新增：历史对话查询接口 ======================
@app.get("/api/v2/conversations", tags=["核心接口"])
async def get_conversations(
        tenant_id: str = Header(default="tenant_001", alias="X-Tenant-ID"),
        tenant_info: Dict = Depends(get_current_tenant)
):
    """查询租户历史对话"""
    try:
        conversations = conversation_db.get_conversations(tenant_id)
        return {
            "code": 200,
            "msg": "success",
            "data": {
                "tenant_id": tenant_id,
                "conversations": conversations,
                "count": len(conversations)
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询对话失败：{str(e)}")



# ====================== 8. 核心Agent接口（集成数据库） ======================
@app.post("/api/v2/agent/task", tags=["核心接口"], response_model=AgentTaskResponse)
async def multi_agent_task(
        request: AgentTaskRequest,
        tenant_info: Dict = Depends(get_current_tenant)  # 直接接收鉴权后的租户信息
):
    """多Agent任务接口（集成Prompt模板+对话记录）"""
    # 1. 提取租户ID（直接从tenant_info获取，无需匹配）
    tenant_id = tenant_info["tenant_id"]
    conversation_id = request.conversation_id or f"conv_{uuid.uuid4().hex[:8]}"
    logger.info(f"处理租户 {tenant_id} 的Agent任务：{request.agent_ids},对话ID：{conversation_id}")

    # 2. 验证Agent权限
    invalid_agents = [aid for aid in request.agent_ids if aid not in tenant_info["agents"]]
    if invalid_agents:
        raise HTTPException(
            status_code=403,
            detail=f"无权限调用Agent：{invalid_agents}，仅可调用：{tenant_info['agents']}"
        )

    # 3. 调用Agent（确保有参数，无None）
    agent_tasks = [
        call_single_agent(aid, request.user_query, request.context or {}, tenant_info)
        for aid in request.agent_ids
    ]
    agent_results = await asyncio.gather(*agent_tasks)

    # 4. 聚合结果（兜底空值）
    aggregated_result = "\n".join(
        [f"{r['agent_id']}：{r['response']}" for r in agent_results]) if agent_results else "暂无结果"

    conversation_db.add_conversation(
        tenant_id=tenant_id,
        agent_ids=request.agent_ids,
        user_query=request.user_query,
        aggregated_result=aggregated_result,
        conversation_id=conversation_id
    )
    # 5. 构造响应（确保所有字段有值）
    return {
        "code": 200,
        "msg": "success",
        "data": {
            "tenant_info": {
                "tenant_id": tenant_id,
                "tenant_name": tenant_info["name"],
                "rate_limit": tenant_info["rate_limit"]
            },
            "agent_results": agent_results,
            "aggregated_result": aggregated_result,
            "conversation_id": conversation_id  # 返回对话ID
        }
    }

# 定义全局单例变量
_qdrant_singleton = None

# 单例依赖函数：确保全局仅一个 QdrantVectorStore 实例
def get_qdrant_vector_store_singleton():
    global _qdrant_singleton
    # 仅当实例不存在时，才创建新实例
    if _qdrant_singleton is None:
        _qdrant_singleton = QdrantVectorStore()
    return _qdrant_singleton
# 定义RAG查询模型（与main.py中的其他模型同级）
class RAGQuery(BaseModel):
    query: str
    top_k: int = 3
# 新增RAG问答接口（与main.py中的其他接口同级）
@app.post("/api/v2/rag/qa", tags=["核心接口"])
async def rag_qa(
        request: RAGQuery,
        tenant_info: Dict = Depends(get_current_tenant),
        # 注入单例实例，避免重复创建
        vector_store: QdrantVectorStore = Depends(get_qdrant_vector_store_singleton)
):
    """RAG基础问答接口（集成Qdrant向量检索+LLM生成）"""
    try:
        # 1. 向量检索
        search_results = vector_store.search(request.query, top_k=request.top_k)
        # 2. 拼接上下文
        context = "\n".join([res["content"] for res in search_results])
        # 3. 复用main.py中的LLM调用逻辑（call_single_agent或直接调用qwen_client）
        prompt = f"""
        基于以下上下文回答用户问题，不要编造信息。
        上下文：{context}
        用户问题：{request.query}
        回答：
        """
        llm_response = await qwen_client.generate(prompt, tenant_info["tenant_id"])
        # 4. 构造响应
        return {
            "code": 200,
            "msg": "success",
            "data": {
                "query": request.query,
                "answer": llm_response,
                "contexts": search_results
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"RAG问答失败：{str(e)}")

# 新增文旅Agent工具调用接口（集成租户鉴权）
@app.post("/api/v2/agent/tourism/tool-qa", tags=["核心接口"])
async def tourism_agent_tool_qa(
request: TourismAgentRequest,
        tenant_info: Dict = Depends(get_current_tenant) # 复用现有租户鉴权
):
    """文旅问答Agent接口（支持天气查询、景点开放时间查询工具调用）"""
    try:
    # 调用文旅Agent（传入租户信息）
        logger.info("===== 手动测试调用 call_clean_tourism_agent =====")
        agent_response = await call_tourism_agent(
        tenant_id = tenant_info["tenant_id"],
        tenant_name = tenant_info["name"],
        user_query = request.user_query
        )
        # 记录对话（复用现有ConversationDB）
        conversation_id = f"conv_{uuid.uuid4().hex[:8]}"
        conversation_db.add_conversation(
        tenant_id = tenant_info["tenant_id"],
        agent_ids = ["tourism_qa_agent"],  #
                    user_query = request.user_query,
        aggregated_result = agent_response,
        conversation_id = conversation_id
        )
        return {
        "code": 200,
        "msg": "success",
        "data":{
        "tenant_info":{
        "tenant_id": tenant_info["tenant_id"],
        "tenant_name": tenant_info["name"]
        },
        "user_query": request.user_query,
        "agent_response": agent_response,
        "conversation_id": conversation_id
        }
        }
    except Exception as e:
        logger.error(f"文旅Agent接口调用失败：{str(e)}")
        raise HTTPException(status_code=500, detail=f"Agent接口调用失败：{str(e)}")
#weather_tool = WeatherTool()
@app.get("/weather/{city}")
async def get_weather(city: str):
    weather_tool = WeatherTool()
    result = await weather_tool._arun(city)
    return {"city": city, "weather": result}



graph = build_tour_graph()

# ========== 核心：会话存储（内存版，生产环境可替换为Redis/数据库） ==========
# 存储结构：{conversation_id: {"tenant_id": "", "history": []}}
conversation_store: Dict[str, Dict] = {}
# 线程安全锁（FastAPI异步环境）
conversation_store_lock = asyncio.Lock()

class GraphRequest(BaseModel):
    user_query: str
    conversation_id: Optional[str] = None
    context: Optional[Dict] = None

@app.post("/api/v2/agent/graph", tags=["LangGraph"])
async def graph_agent(
    request: GraphRequest,
    tenant_info: Dict = Depends(get_current_tenant)
):
    try:
        # ========== 新增：类型转换，兼容元组值 ==========
        # 提取tenant_id，若为元组则取第一个元素，否则直接用
        tenant_id = tenant_info["tenant_id"][0] if isinstance(tenant_info["tenant_id"], (tuple, list)) else tenant_info[
            "tenant_id"]
        # 提取tenant_name，同理
        tenant_name = tenant_info["name"][0] if isinstance(tenant_info["name"], (tuple, list)) else tenant_info["name"]
        # 确保最终是字符串（防止空值）
        tenant_id = str(tenant_id).strip()
        tenant_name = str(tenant_name).strip()
        conversation_id = request.conversation_id or f"conv_{uuid.uuid4().hex[:8]}"
        # ========== 核心修改：复用get_conversations过滤历史（无新增方法） ==========
        history = []
        if request.conversation_id:  # 仅前端传了ID才加载历史
            # 1. 调用现有方法：获取该租户的所有会话记录
            all_tenant_convs = conversation_db.get_conversations(tenant_id)
            # 2. 过滤：只保留当前conversation_id的记录
            target_convs = [
                conv for conv in all_tenant_convs
                if conv["conversation_id"] == request.conversation_id
            ]
            # 3. 排序：按create_time升序（保证历史顺序正确）
            target_convs_sorted = sorted(
                target_convs,
                key=lambda x: x["create_time"] if x["create_time"] else "",
                reverse=False
            )
            # 4. 拼接成LangGraph需要的history格式
            for conv in target_convs_sorted:
                # 追加用户问题
                history.append({
                    "role": "user",
                    "content": conv["user_query"],
                    "timestamp": conv["create_time"]
                })
                # 追加助手回答/反问
                history.append({
                    "role": "assistant",
                    "content": conv["aggregated_result"],
                    "timestamp": conv["create_time"]
                })
        state = TourGraphState(
            user_query=request.user_query,
            tenant_id=tenant_id,
            tenant_name=tenant_name,
            conversation_id=conversation_id,
            history=history  # 加载历史上下文
        )

        result = await graph.ainvoke(state.model_dump())

        # ========== 关键：模型调用后必执行add_conversation（高亮） ==========
        # 确定要保存的结果（反问内容/正常回答）
        save_result = result["ask_message"] if result.get("need_ask") else result.get("answer", "")
        # 执行保存（无论是否反问，都写入数据库）
        conversation_db.add_conversation(
            tenant_id=tenant_id,
            agent_ids=["langgraph_tour_agent"],
            user_query=request.user_query,
            aggregated_result=save_result,
            conversation_id=conversation_id
        )

        # 如果需要反问
        if result.get("need_ask"):

            return {
                "code": 200,
                "msg": "need_ask",
                "data": {
                    "ask": result["ask_message"],
                    "conversation_id": state.conversation_id
                }
            }

        return {
            "code": 200,
            "msg": "success",
            "data": {
                "query": request.user_query,
                "intent": result.get("intent"),
                "city": result.get("city"),
                "scenic": result.get("scenic_name"),
                "answer": result.get("answer"),
                "conversation_id": conversation_id  # 新增这一行
            }
        }
    except Exception as e:
        logger.error(f"GraphAgent接口调用失败：{str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"接口调用失败：{str(e)}")

tour_graph_app = build_tour_graph()
# 核心多Agent问答接口
# ==============================
@app.post("/api/tourism/query", summary="文旅多Agent问答接口", response_model=TourismQueryResponse)
async def tourism_query(request: TourismQueryRequest):
    """
    核心接口：基于多Agent协作的文旅问答
    - 支持意图理解→景点推荐双Agent协作
    - 支持天气查询、景点开放时间查询、普通问答
    - 支持租户隔离、多轮对话
    """
    # 生成请求ID
    request_id = f"req_{asyncio.current_task().get_name()}_{id(request)}"

    try:
        # 1. 参数校验
        if not request.user_query.strip():
            raise HTTPException(status_code=400, detail="用户查询内容不能为空")

        logger.info(
            f"【多Agent请求开始】request_id={request_id}, tenant_id={request.tenant_id}, user_query={request.user_query[:50]}...")

        # 2. 多模态分支：有图片时走图文问答
        if request.image_url:
            logger.info(f"【多模态分支】request_id={request_id}, image_url={request.image_url[:80]}")
            try:
                from multimodal.multimodal_agent import multimodal_agent
                mm_result = multimodal_agent.analyze(
                    query=request.user_query.strip(),
                    image_url=request.image_url,
                )
                response_data = {
                    "user_query": request.user_query.strip(),
                    "intent": "multimodal",
                    "need_recommend": False,
                    "city": "",
                    "scenic_name": "",
                    "answer": mm_result.get("answer", ""),
                    "weather_info": "",
                    "scenic_info": mm_result.get("kg_supplement", ""),
                    "time_info": "",
                    "need_ask": False,
                    "ask_message": "",
                    "conversation_id": request.conversation_id or request_id,
                    "error": "",
                    "image_url": request.image_url,
                    "multimodal": True,
                }
                logger.info(f"【多模态请求完成】request_id={request_id}")
                return TourismQueryResponse(code=200, msg="success", data=response_data, request_id=request_id)
            except Exception as e:
                logger.warning(f"【多模态分支失败，回退到普通流程】{str(e)}")
                # 降级到普通流程继续执行

        # 3. 查询缓存
        cache_key = None
        if redis_cache:
            cache_key = redis_cache.make_key("cache:tourism:query", request.tenant_id, request.user_query.strip(), request.image_url or "")
            cached = redis_cache.get_json(cache_key)
            if cached:
                logger.info(f"【缓存命中】request_id={request_id}")
                return TourismQueryResponse(code=200, msg="success (cached)", data=cached, request_id=request_id)

        # 3. 构建LangGraph状态
        graph_state = TourGraphState(
            user_query=request.user_query.strip(),
            tenant_id=request.tenant_id,
            tenant_name=request.tenant_name,
            conversation_id=request.conversation_id or request_id,
            history=request.history or []
        )

        # 4. 异步调用多Agent流程
        result_state = await tour_graph_app.ainvoke(graph_state)

        # 5. 构建响应数据
        response_data = {
            "user_query": result_state.get("user_query", ""),
            "intent": result_state.get("intent", ""),
            "need_recommend": result_state.get("need_recommend", False),
            "city": result_state.get("city", ""),
            "scenic_name": result_state.get("scenic_name", ""),
            "answer": result_state.get("answer") or result_state.get("ask_message", ""),
            "weather_info": result_state.get("weather_info", ""),
            "scenic_info": result_state.get("scenic_info", ""),
            "time_info": result_state.get("time_info", ""),
            "need_ask": result_state.get("need_ask", False),
            "ask_message": result_state.get("ask_message", ""),
            "conversation_id": result_state.get("conversation_id", ""),
            "error": result_state.get("error", "")
        }

        logger.info(f"【多Agent请求完成】request_id={request_id}, answer={response_data['answer'][:50]}...")

        # 6. 写入缓存
        if redis_cache and cache_key:
            redis_cache.set_json(cache_key, response_data, ttl=300)
            logger.info(f"【缓存写入】request_id={request_id}")

        # 7. 返回响应
        return TourismQueryResponse(
            code=200,
            msg="success",
            data=response_data,
            request_id=request_id
        )

    except HTTPException as e:
        # 客户端错误
        logger.error(f"【多Agent请求失败】request_id={request_id}, 客户端错误：{e.detail}")
        return TourismQueryResponse(
            code=e.status_code,
            msg=f"error: {e.detail}",
            data={},
            request_id=request_id
        )

    except Exception as e:
        # 服务器错误
        error_msg = str(e)
        logger.error(f"【多Agent请求失败】request_id={request_id}, 服务器错误：{error_msg}", exc_info=True)
        return TourismQueryResponse(
            code=500,
            msg=f"服务器内部错误：{error_msg[:100]}",
            data={},
            request_id=request_id
        )


# 专用景点推荐接口（简化版）
# ==============================
@app.post("/api/tourism/recommend", summary="景点推荐专用接口", response_model=TourismQueryResponse)
async def tourism_recommend(request: TourismQueryRequest):
    """
    专用接口：仅处理景点推荐请求（简化版）
    直接触发意图理解→景点推荐双Agent流程
    """
    # 包装用户查询，确保触发景点推荐意图
    enhanced_query = f"推荐{request.user_query}的景点，要求简洁实用，列出3-5个核心景点"
    request.user_query =enhanced_query

    # 复用核心问答接口逻辑
    return await tourism_query(request)
# ==========================
# 新增：知识图谱专用接口（第9周学习任务）
# ==========================
@app.get("/api/kg/city/{city_name}", summary="查询城市景点（知识图谱）")
async def get_city_spots(city_name: str):
    """直接调用知识图谱查询指定城市的景点（NetworkX版），带Redis缓存"""
    # 查缓存
    if redis_cache:
        cache_key = redis_cache.make_key("cache:kg:city", city_name)
        cached = redis_cache.get_json(cache_key)
        if cached:
            return {"code": 200, "msg": "success (cached)", "data": cached}

    kg_service = get_kg_service()
    if not kg_service:
        raise HTTPException(status_code=503, detail="知识图谱服务未初始化")

    spots = kg_service.get_city_scenic_spots(city_name)
    if not spots:
        raise HTTPException(status_code=404, detail=f"未查询到{city_name}的景点数据")

    # 写缓存
    result = {"city": city_name, "spots": spots}
    if redis_cache:
        redis_cache.set_json(cache_key, result, ttl=600)

    return {"code": 200, "msg": "success", "data": result}

@app.get("/api/kg/scenic/{spot_name}/traffic", summary="查询景点交通信息（知识图谱）")
async def get_scenic_traffic(spot_name: str):
    """查询指定景点的交通信息（NetworkX版），带Redis缓存"""
    # 查缓存
    if redis_cache:
        cache_key = redis_cache.make_key("cache:kg:scenic:traffic", spot_name)
        cached = redis_cache.get_json(cache_key)
        if cached:
            return {"code": 200, "msg": "success (cached)", "data": cached}

    kg_service = get_kg_service()
    if not kg_service:
        raise HTTPException(status_code=503, detail="知识图谱服务未初始化")

    traffic = kg_service.get_scenic_traffic(spot_name)
    if not traffic:
        raise HTTPException(status_code=404, detail=f"未查询到{spot_name}的交通信息")

    # 写缓存
    result = {"spot": spot_name, "traffic": traffic}
    if redis_cache:
        redis_cache.set_json(cache_key, result, ttl=600)

    return {"code": 200, "msg": "success", "data": result}

@app.get("/api/kg/scenic/{spot_name}/recommend", summary="查询景点推荐（知识图谱）")
async def get_scenic_recommend(spot_name: str):
    """查询与指定景点联动推荐的其他景点（NetworkX版）"""
    kg_service = get_kg_service()
    if not kg_service:
        raise HTTPException(status_code=503, detail="知识图谱服务未初始化")
    
    recommends = kg_service.get_recommend_spots(spot_name)
    if not recommends:
        raise HTTPException(status_code=404, detail=f"未查询到{spot_name}的推荐景点")
    return {
        "code": 200,
        "msg": "success",
        "data": {"spot": spot_name, "recommendations": recommends}
    }

@app.get("/api/kg/city/{city_name}/relics", summary="查询城市文物收藏（知识图谱）")
async def get_city_relics(city_name: str):
    """查询指定城市的文物收藏信息（NetworkX版）"""
    kg_service = get_kg_service()
    if not kg_service:
        raise HTTPException(status_code=503, detail="知识图谱服务未初始化")
    
    relics = kg_service.get_city_cultural_relics(city_name)
    if not relics:
        raise HTTPException(status_code=404, detail=f"未查询到{city_name}的文物信息")
    return {
        "code": 200,
        "msg": "success",
        "data": {"city": city_name, "relics": relics}
    }

# ==========================
# 第10周新增：RAG+知识图谱双增强接口
# ==========================
class RAGQueryRequest(BaseModel):
    """RAG查询请求模型"""
    query: str = Field(..., description="用户查询")
    include_evaluation: bool = Field(default=False, description="是否包含评估结果")

@app.post("/api/v2/rag/kg/qa", tags=["第10周任务"], summary="双增强RAG问答（知识图谱+向量）")
async def dual_rag_qa(request: RAGQueryRequest):
    """
    双增强RAG问答接口（第10周核心任务）
    - 知识图谱结构化检索 + 向量文本检索
    - 支持过滤、去重、重排优化
    - 可选评估功能
    
    流程：
    1. 知识图谱检索 → 获取结构化数据（景点、交通、推荐）
    2. 向量检索 → 获取文本参考资料
    3. 过滤去重 → 清理低质量结果
    4. 重排优化 → 提升相关性
    5. 大模型生成 → 整合双源信息
    """
    try:
        from agent.graph.dual_rag_qa import dual_enhance_qa
        
        result = await dual_enhance_qa(request.query)
        
        # 是否需要评估
        if request.include_evaluation:
            from agent.graph.rag_evaluate import RagasEvaluator
            
            evaluator = RagasEvaluator()
            contexts = []
            if result["kg_knowledge"]:
                contexts.append(result["kg_knowledge"])
            if result["vector_reference"]:
                contexts.append(result["vector_reference"])
            
            evaluation = evaluator.evaluate_single(
                question=result["question"],
                answer=result["answer"],
                contexts=contexts
            )
            result["evaluation"] = evaluation
        
        return {
            "code": 200,
            "msg": "success",
            "data": result
        }
    except Exception as e:
        logger.error(f"双增强RAG问答失败：{str(e)}")
        raise HTTPException(status_code=500, detail=f"双增强RAG问答失败：{str(e)}")

@app.post("/api/v2/rag/kg/evaluate", tags=["第10周任务"], summary="RAG效果批量评估（Ragas）")
async def ragas_evaluate(request: dict = {}):
    """
    RAG效果批量评估接口（第10周核心任务）
    - 使用Ragas风格评估指标：faithfulness、relevancy、precision、recall
    - 生成评估报告并保存到文件
    """
    try:
        from agent.graph.rag_evaluate import run_rag_evaluation
        
        # 获取测试查询列表
        test_samples = request.get("samples", None)
        
        result = await run_rag_evaluation(test_samples)
        
        return {
            "code": 200,
            "msg": "success",
            "data": {
                "total_samples": result["total_samples"],
                "average_scores": result["average"],
                "grade": result["grade"],
                "report_file": "ragas_evaluation_report.txt"
            }
        }
    except Exception as e:
        logger.error(f"Ragas评估失败：{str(e)}")
        raise HTTPException(status_code=500, detail=f"Ragas评估失败：{str(e)}")

@app.get("/api/v2/rag/kg/config", tags=["第10周任务"], summary="获取RAG配置信息")
async def get_rag_config():
    """
    获取RAG服务配置信息
    """
    return {
        "code": 200,
        "msg": "success",
        "data": {
            "description": "双增强RAG问答服务（知识图谱+向量检索）",
            "version": "1.0.0",
            "modules": {
                "kg_connect": "知识图谱检索模块（NetworkX版）",
                "vector_rag": "向量文本检索模块（Qdrant）",
                "rerank_filter": "检索重排与过滤模块",
                "dual_rag_qa": "双增强问答核心模块",
                "rag_evaluate": "Ragas效果评估模块"
            },
            "features": [
                "知识图谱结构化检索（景点、交通、推荐、文物）",
                "向量文本语义检索",
                "无用文档过滤",
                "检索结果重排",
                "文档去重",
                "Ragas指标评估（faithfulness、relevancy、precision、recall）"
            ],
            "endpoints": [
                "POST /api/v2/rag/kg/qa - 双增强问答",
                "POST /api/v2/rag/kg/evaluate - Ragas评估",
                "GET /api/v2/rag/kg/config - 获取配置"
            ]
        }
    }

# ==============================
# 启动配置

# ====================== 9. 启动服务 ======================
if __name__ == "__main__":
    vector_store = QdrantVectorStore(collection_name="test_collection",
        path="./local_qdrant_data",  # 本地文件存储，可改为 host+port 连接服务端
        vector_dimension=1024)
    import uvicorn

    uvicorn.run(
        app="main:app",
        host="0.0.0.0",
        port=8000,
        reload=False
    )



