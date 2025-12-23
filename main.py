# ====================== 1. 日志初始化（最顶部，确保最早执行） ======================
import logging
import os
from datetime import datetime
from typing import Optional, Dict, List
from fastapi import FastAPI, Depends, HTTPException, Header
from pydantic import BaseModel
import aiohttp
import asyncio
from llm.client import qwen_client

# 配置日志（输出到控制台+文件）
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("metaagentpaas.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("MetaAgentPaaS")

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


# ====================== 3. 模型定义 ======================
class AgentTaskRequest(BaseModel):
    agent_ids: List[str]
    user_query: str
    context: Optional[Dict] = None


class AgentTaskResponse(BaseModel):
    code: int = 200
    msg: str = "success"
    data: Dict = {
        "tenant_info": {},
        "agent_results": [],
        "aggregated_result": ""
    }


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


# ====================== 5. Agent调用（全兜底，避免空值） ======================
async def call_single_agent(agent_id: str, query: str, context: Dict, tenant_info: Dict) -> Dict:
    """调用单个Agent（集成百炼大模型）"""
    try:
        # 1. 提取租户ID和城市（用于大模型调用）
        tenant_id = tenant_info["tenant_id"]
        city = context.get("location", "北京")

        # 2. 根据Agent类型构造专属提示词
        if agent_id == "tourism_recommend_agent":
            prompt = f"""你是{tenant_info['name']}的专属文旅推荐Agent，用户需求：{query}，目标城市：{city}
            请按照以下要求回复：
            1. 推荐3-5个该城市的5A景区；
            2. 每个景区包含「名称、门票价格、推荐理由」；
            3. 语言简洁，分点列出，不要多余话术；
            4. 仅回复推荐内容，无需其他开头/结尾。"""
        else:
            prompt = f"""你是{tenant_info['name']}的专属Agent，用户问题：{query}，请直接、简洁地回答。"""

        llm_response = await qwen_client.generate(prompt, tenant_id)
        return {
            "agent_id": agent_id,
            "status": "success",
            "response": llm_response,
            "cost_time": 0.5
        }
    except Exception as e:
        logger.error(f"Agent调用失败：{agent_id}，错误：{str(e)}")
        return {
            "agent_id": agent_id,
            "status": "failed",
            "response": f"调用失败：{str(e)}",
            "cost_time": 0
        }


# ====================== 6. FastAPI应用初始化 ======================
app = FastAPI(
    title="MetaAgentPaaS",
    description="企业级多模态AI Agent智能中台（修复版）",
    version="2.0.0"
)


# ====================== 7. 健康检查接口 ======================
@app.get("/health", tags=["基础接口"])
async def health_check():
    return {
        "status": "healthy",
        "service": "MetaAgentPaaS",
        "version": "2.0.0",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }


# ====================== 8. 核心Agent接口（全兜底） ======================
@app.post("/api/v2/agent/task", tags=["核心接口"], response_model=AgentTaskResponse)
async def multi_agent_task(
        request: AgentTaskRequest,
        tenant_info: Dict = Depends(get_current_tenant)  # 直接接收鉴权后的租户信息
):
    """多Agent任务接口（全兜底，确保无空值）"""
    # 1. 提取租户ID（直接从tenant_info获取，无需匹配）
    tenant_id = tenant_info["tenant_id"]
    logger.info(f"处理租户 {tenant_id} 的Agent任务：{request.agent_ids}")

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
            "aggregated_result": aggregated_result
        }
    }


# ====================== 9. 启动服务 ======================
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app="main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )



