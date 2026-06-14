# api.py
# ========================================
# 多模态问答API路由
# 功能：图片上传、URL输入、图文混合问答
# 接口：/api/multimodal/*
# ========================================

import base64
import logging
from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from multimodal.vl_client import qwen_vl_client
from multimodal.multimodal_agent import multimodal_agent

logger = logging.getLogger("MetaAgentPaaS.multimodal.api")

router = APIRouter(prefix="/api/multimodal", tags=["多模态问答"])


# ========== 请求/响应模型 ==========

class ImageURLQueryRequest(BaseModel):
    """图片URL问答请求"""
    query: str = Field(..., description="用户问题", example="这张图片里的文物是什么朝代的？")
    image_url: str = Field(..., description="图片URL地址")
    tenant_id: str = Field(default="default", description="租户ID")


class ImageBase64QueryRequest(BaseModel):
    """Base64图片问答请求"""
    query: str = Field(..., description="用户问题", example="描述一下这张图片")
    image_base64: str = Field(..., description="图片Base64编码")
    tenant_id: str = Field(default="default", description="租户ID")


# ========== API接口 ==========

@router.post("/analyze/url", summary="图片URL问答")
async def analyze_by_url(request: ImageURLQueryRequest):
    """
    通过图片URL进行图文问答
    - 传入图片URL和问题
    - 返回图片分析结果和知识图谱补充信息
    """
    try:
        result = await multimodal_agent.analyze_relic(
            query=request.query,
            image_url=request.image_url,
            tenant_id=request.tenant_id,
        )
        return {"code": 200, "msg": "success", "data": result}
    except Exception as e:
        logger.error(f"图片URL问答失败：{str(e)}")
        raise HTTPException(status_code=500, detail=f"图片URL问答失败：{str(e)}")


@router.post("/analyze/base64", summary="Base64图片问答")
async def analyze_by_base64(request: ImageBase64QueryRequest):
    """
    通过Base64编码图片进行图文问答
    - 传入图片Base64和问题
    - 返回图片分析结果和知识图谱补充信息
    """
    try:
        result = await multimodal_agent.analyze_relic(
            query=request.query,
            image_base64=request.image_base64,
            tenant_id=request.tenant_id,
        )
        return {"code": 200, "msg": "success", "data": result}
    except Exception as e:
        logger.error(f"Base64图片问答失败：{str(e)}")
        raise HTTPException(status_code=500, detail=f"Base64图片问答失败：{str(e)}")


@router.post("/analyze/upload", summary="图片上传问答")
async def analyze_by_upload(
    query: str = "请描述这张图片的内容",
    tenant_id: str = "default",
    file: UploadFile = File(...),
):
    """
    通过上传图片文件进行图文问答
    - 上传图片文件（支持jpg/png/jpeg）
    - 返回图片分析结果和知识图谱补充信息
    """
    try:
        # 校验文件类型
        if file.content_type and not file.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="仅支持图片文件（jpg/png/jpeg）")

        # 读取文件并编码为Base64
        file_bytes = await file.read()
        if len(file_bytes) > 10 * 1024 * 1024:  # 10MB限制
            raise HTTPException(status_code=400, detail="图片文件不能超过10MB")

        image_base64 = qwen_vl_client.encode_image_to_base64(file_bytes)

        result = await multimodal_agent.analyze_relic(
            query=query,
            image_base64=image_base64,
            tenant_id=tenant_id,
        )
        return {"code": 200, "msg": "success", "data": result}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"图片上传问答失败：{str(e)}")
        raise HTTPException(status_code=500, detail=f"图片上传问答失败：{str(e)}")


@router.get("/config", summary="多模态服务配置")
async def get_multimodal_config():
    """查询多模态服务配置信息"""
    return {
        "code": 200,
        "msg": "success",
        "data": {
            "model": qwen_vl_client.model,
            "api_configured": qwen_vl_client.is_available,
            "supported_formats": ["jpg", "png", "jpeg", "webp"],
            "max_file_size": "10MB",
            "endpoints": [
                "POST /api/multimodal/analyze/url - 图片URL问答",
                "POST /api/multimodal/analyze/base64 - Base64图片问答",
                "POST /api/multimodal/analyze/upload - 图片上传问答",
                "GET /api/multimodal/config - 服务配置",
            ],
            "features": [
                "Qwen-VL多模态大模型图文理解",
                "知识图谱增强（自动检索相关景点/文物信息）",
                "支持URL/Base64/文件上传三种图片输入方式",
            ],
        },
    }
