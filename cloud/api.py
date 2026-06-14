# api.py
# ========================================
# 云资源管理API路由
# 功能：提供云资源查询和调度接口
# 安全：所有写操作默认 dry_run=True，不会产生费用
# ========================================

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List
from cloud.ecs_manager import ecs_manager
from cloud.scheduler import scheduler
import logging

logger = logging.getLogger("MetaAgentPaaS.cloud.api")

router = APIRouter(prefix="/api/cloud", tags=["云资源管理"])


# ==============================
# 请求/响应模型
# ==============================
class CreateInstanceRequest(BaseModel):
    """创建实例请求"""
    instance_type: str = Field(default="SA2.MEDIUM4", description="实例规格")
    instance_name: str = Field(default="MetaAgentPaaS-auto", description="实例名称")
    instance_count: int = Field(default=1, ge=1, le=5, description="创建数量")
    dry_run: bool = Field(default=True, description="预检模式（True不实际创建）")


class ReleaseInstanceRequest(BaseModel):
    """释放实例请求"""
    instance_id: str = Field(..., description="实例ID")
    dry_run: bool = Field(default=True, description="预检模式（True不实际释放）")


class ScheduleRequest(BaseModel):
    """调度执行请求"""
    dry_run: bool = Field(default=True, description="预检模式（True不实际执行）")


# ==============================
# 接口1：查询所有实例
# ==============================
@router.get("/instances", summary="查询所有CVM实例")
async def list_instances():
    """查询当前账号下所有云服务器实例"""
    try:
        instances = ecs_manager.list_instances()
        return {
            "code": 200,
            "msg": "success",
            "data": {
                "total": len(instances),
                "configured": ecs_manager.is_configured,
                "instances": instances,
            },
        }
    except Exception as e:
        logger.error(f"查询实例失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ==============================
# 接口2：查询实例详情
# ==============================
@router.get("/instances/{instance_id}", summary="查询实例详情")
async def get_instance(instance_id: str):
    """查询指定实例的详细信息"""
    try:
        detail = ecs_manager.get_instance_detail(instance_id)
        if not detail:
            raise HTTPException(status_code=404, detail=f"实例 {instance_id} 不存在")
        return {"code": 200, "msg": "success", "data": detail}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查询实例详情失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ==============================
# 接口3：查询监控数据
# ==============================
@router.get("/monitor/{instance_id}", summary="查询实例监控数据")
async def get_monitor(instance_id: str):
    """查询指定实例的CPU利用率等监控数据"""
    try:
        data = ecs_manager.get_monitor_data(instance_id)
        return {"code": 200, "msg": "success", "data": data}
    except Exception as e:
        logger.error(f"查询监控数据失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ==============================
# 接口4：创建实例（默认dry-run）
# ==============================
@router.post("/instances/create", summary="创建CVM实例")
async def create_instance(request: CreateInstanceRequest):
    """
    创建云服务器实例
    - dry_run=True（默认）：仅预检，不实际创建，不产生费用
    - dry_run=False：实际创建，按量付费会产生费用
    """
    try:
        result = ecs_manager.create_instance(
            params={
                "instance_type": request.instance_type,
                "instance_name": request.instance_name,
                "instance_count": request.instance_count,
            },
            dry_run=request.dry_run,
        )
        return {"code": 200, "msg": "success", "data": result}
    except Exception as e:
        logger.error(f"创建实例失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ==============================
# 接口5：释放实例（默认dry-run）
# ==============================
@router.post("/instances/release", summary="释放CVM实例")
async def release_instance(request: ReleaseInstanceRequest):
    """
    释放/销毁云服务器实例
    - dry_run=True（默认）：仅预检，不实际释放
    - dry_run=False：实际释放，实例将被删除！
    """
    try:
        result = ecs_manager.release_instance(
            instance_id=request.instance_id,
            dry_run=request.dry_run,
        )
        return {"code": 200, "msg": "success", "data": result}
    except Exception as e:
        logger.error(f"释放实例失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ==============================
# 接口6：资源调度分析
# ==============================
@router.get("/schedule/analysis", summary="资源调度分析")
async def schedule_analysis():
    """
    分析当前资源状态，生成调度建议
    仅分析，不执行任何操作
    """
    try:
        analysis = scheduler.analyze()
        return {"code": 200, "msg": "success", "data": analysis}
    except Exception as e:
        logger.error(f"调度分析失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ==============================
# 接口7：执行调度策略
# ==============================
@router.post("/schedule/execute", summary="执行资源调度")
async def schedule_execute(request: ScheduleRequest):
    """
    执行资源调度策略
    - dry_run=True（默认）：仅输出建议，不实际操作
    - dry_run=False：实际执行扩缩容（可能产生费用！）
    """
    try:
        result = scheduler.execute(dry_run=request.dry_run)
        return {"code": 200, "msg": "success", "data": result}
    except Exception as e:
        logger.error(f"调度执行失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ==============================
# 接口8：调度配置查询
# ==============================
@router.get("/schedule/config", summary="查询调度配置")
async def get_schedule_config():
    """查询当前调度策略的阈值配置"""
    return {
        "code": 200,
        "msg": "success",
        "data": {
            "scale_up_threshold": scheduler.SCALE_UP_THRESHOLD,
            "scale_down_threshold": scheduler.SCALE_DOWN_THRESHOLD,
            "min_instances": scheduler.MIN_INSTANCES,
            "max_instances": scheduler.MAX_INSTANCES,
            "description": f"CPU>{scheduler.SCALE_UP_THRESHOLD}%扩容，CPU<{scheduler.SCALE_DOWN_THRESHOLD}%缩容",
        },
    }
