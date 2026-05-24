# ========================================
# 第11周任务：FastAPI日志中间件
# 记录所有API请求和响应
# ========================================
import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from agent.utils.logging_config import agent_logger

class LogMiddleware(BaseHTTPMiddleware):
    """
    FastAPI日志中间件
    记录所有HTTP请求和响应
    """
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # 记录请求信息
        agent_logger.log_api_request(
            endpoint=str(request.url.path),
            method=request.method,
            status_code=0,  # 先设为0，后面更新
            duration=0.0    # 先设为0，后面更新
        )
        
        # 执行请求
        response = await call_next(request)
        
        # 计算耗时
        duration = time.time() - start_time
        
        # 更新日志记录
        agent_logger.log_api_request(
            endpoint=str(request.url.path),
            method=request.method,
            status_code=response.status_code,
            duration=duration
        )
        
        return response
