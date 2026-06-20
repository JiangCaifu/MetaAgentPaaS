# cache_api.py
# ========================================
# 缓存管理API路由
# 功能：缓存统计、手动清理、配置查询
# ========================================

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from cache.redis_client import redis_cache
import logging

logger = logging.getLogger("MetaAgentPaaS.cache.api")

router = APIRouter(prefix="/api/cache", tags=["缓存管理"])


class CacheClearRequest(BaseModel):
    """缓存清理请求"""
    pattern: str = Field(default="*", description="要清理的缓存键模式，如 cache:tourism:*")


@router.get("/stats", summary="缓存统计信息")
async def get_cache_stats():
    """获取缓存命中率、键数量等统计信息"""
    try:
        stats = redis_cache.get_stats()
        return {"code": 200, "msg": "success", "data": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取缓存统计失败：{str(e)}")


@router.post("/clear", summary="清理缓存")
async def clear_cache(request: CacheClearRequest):
    """按模式清理缓存，默认清空全部"""
    try:
        if request.pattern == "*":
            success = redis_cache.clear_all()
            return {
                "code": 200,
                "msg": "success" if success else "failed",
                "data": {"action": "clear_all", "success": success},
            }
        else:
            count = redis_cache.delete_pattern(request.pattern)
            return {
                "code": 200,
                "msg": "success",
                "data": {"action": "clear_pattern", "pattern": request.pattern, "deleted": count},
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清理缓存失败：{str(e)}")


@router.get("/config", summary="缓存配置信息")
async def get_cache_config():
    """获取缓存配置信息"""
    from cache.redis_client import REDIS_HOST, REDIS_PORT, DEFAULT_TTL

    return {
        "code": 200,
        "msg": "success",
        "data": {
            "backend": "redis" if redis_cache.is_available else "memory",
            "redis_host": REDIS_HOST,
            "redis_port": REDIS_PORT,
            "default_ttl": DEFAULT_TTL,
            "cache_prefixes": {
                "tourism_query": "cache:tourism:query",
                "kg_city": "cache:kg:city",
                "kg_scenic": "cache:kg:scenic",
                "weather": "cache:weather",
            },
            "description": "高频查询结果缓存，减少重复计算和API调用",
        },
    }


@router.get("/health", summary="缓存健康检查")
async def cache_health():
    """检查Redis连接状态"""
    return {
        "code": 200,
        "msg": "success",
        "data": {
            "redis_available": redis_cache.is_available,
            "backend": "redis" if redis_cache.is_available else "memory_fallback",
        },
    }
