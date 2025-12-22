from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel  # 用于定义请求/响应模型
from typing import Optional
import asyncio
import aiohttp

# 初始化FastAPI应用（企业级规范：加标题、描述、版本）
app = FastAPI(
    title="MetaAgentPaaS",
    description="企业级多模态AI Agent智能中台API服务",
    version="1.0.0"
)

# ====================== 第一步：定义公共依赖（多租户鉴权基础） ======================
# 模拟租户信息（后续会替换为数据库查询）
TENANT_LIST = {
    "tenant_001": {"name": "文旅租户", "token": "token_001", "is_active": True},
    "tenant_002": {"name": "制造租户", "token": "token_002", "is_active": True}
}


# 定义租户鉴权依赖（后续会扩展为多租户隔离核心）
async def get_current_tenant(
        tenant_id: str = "tenant_001",  # 默认租户ID，后续从请求头获取
        tenant_token: str = "token_001"  # 默认租户Token，后续从请求头获取
):
    """验证租户身份，返回租户信息"""
    tenant = TENANT_LIST.get(tenant_id)
    if not tenant or tenant["token"] != tenant_token or not tenant["is_active"]:
        raise HTTPException(status_code=403, detail="租户鉴权失败：ID或Token错误")
    return tenant


# ====================== 第二步：定义基础接口 ======================
# 1. 健康检查接口（云原生必备：K8s会定期调用这个接口检查服务是否存活）
@app.get("/health", tags=["基础接口"])
async def health_check():
    return {
        "status": "healthy",
        "service": "MetaAgentPaaS Core API",
        "version": "1.0.0"
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


# ====================== 启动服务 ======================
if __name__ == "__main__":
    import uvicorn

    # 启动FastAPI服务（host=0.0.0.0允许外部访问，port=8000）
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True  # 开发模式：修改代码自动重启
    )
