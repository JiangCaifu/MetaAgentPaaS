from fastapi import FastAPI, Depends, HTTPException, Header
from pydantic import BaseModel  # 用于定义请求/响应模型
from typing import Optional
from typing import Dict
import asyncio
import aiohttp
import logging

# ====================== 1. 初始化日志（企业级服务必备） ======================
# 配置日志（输出到文件+控制台，方便排查问题）
logging.basicConfig(
    level=logging.INFO,
    encoding="utf-8",
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("metaagentpaas.log"),  # 日志文件
        logging.StreamHandler()  # 控制台输出
    ]
)
logger = logging.getLogger("MetaAgentPaaS")

# ====================== 2. 多租户配置（模拟数据库，后续替换为真实DB） ======================
# 租户配置（包含Agent列表、权限、限流规则）
TENANT_CONFIG: Dict[str, Dict] = {
    "tenant_001": {
        "name": "文旅行业租户",
        "token": "token_001",
        "is_active": True,
        "agents": ["tourism_recommend_agent", "tourism_qa_agent"],  # 租户专属Agent
        "rate_limit": 100  # 每秒请求限制
    },
    "tenant_002": {
        "name": "制造行业租户",
        "token": "token_002",
        "is_active": True,
        "agents": ["factory_monitor_agent", "equipment_qa_agent"],
        "rate_limit": 50
    }
}


# ====================== 3. 多租户鉴权依赖（从请求头获取参数） ======================
async def get_current_tenant(
        tenant_id: Optional[str] = Header(None),  # 从请求头获取租户ID
        tenant_token: Optional[str] = Header(None)  # 从请求头获取租户令牌
):
    """
    多租户鉴权：从请求头读取租户信息，验证合法性
    请求头需携带：X-Tenant-ID、X-Tenant-Token
    """
    # 1. 检查请求头是否包含租户信息
    if not tenant_id or not tenant_token:
        logger.error("租户鉴权失败：请求头缺少X-Tenant-ID或X-Tenant-Token")
        raise HTTPException(
            status_code=400,
            detail="请求头必须包含X-Tenant-ID和X-Tenant-Token"
        )

    # 2. 检查租户是否存在
    tenant = TENANT_CONFIG.get(tenant_id)
    if not tenant:
        logger.error(f"租户鉴权失败：租户ID {tenant_id} 不存在")
        raise HTTPException(
            status_code=404,
            detail=f"租户ID {tenant_id} 不存在"
        )

    # 3. 检查租户是否激活+令牌是否正确
    if not tenant["is_active"]:
        logger.error(f"租户鉴权失败：租户ID {tenant_id} 已停用")
        raise HTTPException(
            status_code=403,
            detail=f"租户ID {tenant_id} 已停用"
        )
    if tenant["token"] != tenant_token:
        logger.error(f"租户鉴权失败：租户ID {tenant_id} 令牌错误")
        raise HTTPException(
            status_code=403,
            detail="租户令牌错误"
        )

    # 4. 鉴权成功，返回租户配置
    logger.info(f"租户鉴权成功：{tenant_id}（{tenant['name']}）")
    return tenant


# ====================== 4. 保留原有FastAPI初始化和健康检查接口 ======================
app = FastAPI(
    title="MetaAgentPaaS",
    description="企业级多模态AI Agent智能中台API服务（多租户版）",
    version="2.0.0"
)

# ====================== 第二步：定义基础接口 ======================
# 1. 健康检查接口（云原生必备：K8s会定期调用这个接口检查服务是否存活）
@app.get("/health", tags=["基础接口"])
async def health_check():
    return {
        "status": "healthy",
        "service": "MetaAgentPaaS Core API（多租户版）",
        "version": "2.0.0",
        "tenant_count": len(TENANT_CONFIG),  # 新增租户数量
        "timestamp": logging.Formatter("%Y-%m-%d %H:%M:%S").format(logging.datetime.now())
    }

# ====================== 5. 多租户Agent请求/响应模型 ======================
class AgentTaskRequest(BaseModel):
    """多Agent任务请求模型"""
    agent_ids: list[str]  # 要调用的Agent列表（需属于租户的专属Agent）
    user_query: str  # 用户查询
    context: Optional[Dict] = None  # 上下文（如用户位置、设备信息）

class AgentTaskResponse(BaseModel):
    """多Agent任务响应模型"""
    code: int = 200
    msg: str = "success"
    data: Dict = {
        "tenant_info": {},
        "agent_results": [],
        "aggregated_result": ""
    }
# 2. 定义Agent问答请求模型（Pydantic规范入参）
class AgentQueryRequest(BaseModel):
    agent_id: str  # Agent ID（比如"tourism_agent_001"）
    user_query: str  # 用户查询（比如"推荐北京的景点"）
    tenant_id: Optional[str] = "tenant_001"  # 可选租户ID


# 3. Agent基础问答接口（复用第一周的异步请求，调用通义千问测试接口）
@app.post("/api/v1/agent/query", tags=["Agent核心接口"])
async def agent_query(
        request: AgentQueryRequest,
        tenant=Depends(get_current_tenant)  # 注入租户鉴权依赖
):
    """基础Agent问答接口（模拟调用大模型）"""

    # 模拟调用通义千问API（异步请求，复用第一周的aiohttp）
    async def call_llm_api(query: str) -> str:
        """异步调用大模型测试接口"""
        test_url = "https://httpbin.org/post"  # 用测试接口模拟大模型API
        async with aiohttp.ClientSession() as session:
            async with session.post(
                    test_url,
                    json={"query": query, "tenant_id": tenant["name"]}
            ) as response:
                result = await response.json()
                # 模拟大模型返回结果
                return f"【{tenant['name']}】已收到你的查询：{query}，推荐景点：故宫、颐和园（模拟回复）"

    # 调用异步函数获取大模型回复
    llm_response = await call_llm_api(request.user_query)

    # 返回规范响应（企业级接口格式：code+msg+data）
    return {
        "code": 200,
        "msg": "success",
        "data": {
            "agent_id": request.agent_id,
            "user_query": request.user_query,
            "response": llm_response,
            "tenant_info": tenant["name"]
        }
    }


# ====================== 6. 多Agent异步协同核心接口 ======================
@app.post("/api/v2/agent/task", tags=["Agent核心接口"], response_model=AgentTaskResponse)
async def multi_agent_task(
        request: AgentTaskRequest,
        tenant=Depends(get_current_tenant)
):
    """
    多租户多Agent异步协同接口：
    1. 验证Agent是否属于当前租户
    2. 并行调用多个Agent
    3. 聚合Agent结果返回
    """
    # 1. 验证Agent是否属于租户
    invalid_agents = [aid for aid in request.agent_ids if aid not in tenant["agents"]]
    if invalid_agents:
        logger.error(f"Agent权限失败：租户 {tenant['name']} 无权限调用 {invalid_agents}")
        raise HTTPException(
            status_code=403,
            detail=f"租户无权限调用以下Agent：{invalid_agents}（仅可调用：{tenant['agents']}）"
        )

    # 2. 异步调用多个Agent（并行执行，体现异步优势）
    async def call_single_agent(agent_id: str, query: str, context: Optional[Dict]) -> Dict:
        """调用单个Agent（异步）"""
        try:
            # 模拟调用Agent接口（后续替换为真实大模型/工具调用）
            async with aiohttp.ClientSession() as session:
                async with session.post(
                        url="https://httpbin.org/post",
                        json={
                            "agent_id": agent_id,
                            "user_query": query,
                            "context": context,
                            "tenant": tenant["name"]
                        },
                        timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    result = await response.json()
                    # 构造Agent返回结果
                    agent_result = {
                        "agent_id": agent_id,
                        "status": "success",
                        "response": f"【{agent_id}】处理结果：{query}（模拟回复）",
                        "cost_time": 0.2  # 模拟耗时
                    }
                    logger.info(f"Agent调用成功：{agent_id}（租户：{tenant['name']}）")
                    return agent_result
        except Exception as e:
            logger.error(f"Agent调用失败：{agent_id}（租户：{tenant['name']}），错误：{str(e)}")
            return {
                "agent_id": agent_id,
                "status": "failed",
                "response": f"调用失败：{str(e)}",
                "cost_time": 0
            }

    # 3. 并行执行所有Agent任务（asyncio.gather核心）
    agent_tasks = [call_single_agent(aid, request.user_query, request.context) for aid in request.agent_ids]
    agent_results = await asyncio.gather(*agent_tasks)

    # 4. 聚合Agent结果（简单聚合，后续可升级为大模型总结）
    aggregated_result = "\n".join([f"{r['agent_id']}：{r['response']}" for r in agent_results])

    # 5. 返回多租户格式的响应
    return {
        "code": 200,
        "msg": "success",
        "data": {
            "tenant_info": {
                "tenant_id": [k for k, v in TENANT_CONFIG.items() if v == tenant][0],
                "tenant_name": tenant["name"],
                "rate_limit": tenant["rate_limit"]
            },
            "agent_results": agent_results,
            "aggregated_result": aggregated_result
        }
    }


# ====================== 7. 启动服务 ======================
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app="main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )



