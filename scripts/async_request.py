import asyncio
import aiohttp
from typing import Optional, Dict
import time


# 定义异步请求转发函数（企业级规范：加类型注解+文档字符串）
async def forward_request(
        target_url: str,
        params: Optional[Dict[str, str]] = None,
        headers: Optional[Dict[str, str]] = None
) -> tuple[int, str]:
    """
    异步转发HTTP GET请求到目标URL，返回响应状态码和内容

    Args:
        target_url: 目标请求URL
        params: 请求参数（可选）
        headers: 请求头（可选）

    Returns:
        tuple: (响应状态码, 响应文本内容)

    Raises:
        aiohttp.ClientError: 请求失败时抛出异常
    """
    # 创建异步客户端会话（企业级最佳实践：复用会话，避免频繁创建连接）
    async with aiohttp.ClientSession() as session:
        try:
            # 发送异步GET请求（await挂起，等待响应但不阻塞其他任务）
            async with session.get(
                    url=target_url,
                    params=params,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30)  # 超时控制（企业级必备）
            ) as response:
                # 读取响应文本（异步操作，需要await）
                response_text = await response.text()
                # 返回状态码和内容
                return response.status, response_text
        except aiohttp.ClientError as e:
            # 异常处理（企业级必备，避免脚本崩溃）
            print(f"请求失败：{str(e)}")
            return 500, f"Request failed: {str(e)}"


# 批量请求核心函数（仅负责执行批量异步请求，职责单一）
async def batch_forward_requests(urls: list[str]) -> list[tuple[int, str]]:
    """批量异步转发请求，同时处理多个URL"""
    # 创建任务列表：把每个URL的请求封装成异步任务
    tasks = [forward_request(url) for url in urls]
    # 并发执行所有任务（asyncio.gather是核心，实现真正的并发）
    results = await asyncio.gather(*tasks)
    # 仅返回请求结果，不处理计时（职责单一）
    return results


# 封装批量请求+计时逻辑（新增函数，分离职责）
async def run_batch_test(urls: list[str]) -> tuple[list[tuple[int, str]], float]:
    """执行批量请求并返回结果+耗时"""
    start_time = time.perf_counter()  # 高精度计时，不依赖事件循环
    results = await batch_forward_requests(urls)  # 执行批量请求
    end_time = time.perf_counter()
    return results, end_time - start_time


# 主函数（程序入口）
if __name__ == "__main__":
    # 测试单个请求
    print("=== 测试单个异步请求 ===")
    test_url = "https://httpbin.org/ip"  # 公开测试接口（返回你的IP）
    # 运行异步函数（asyncio.run是启动协程的入口）
    status, result = asyncio.run(forward_request(test_url))
    print(f"状态码: {status}")
    print(f"响应内容: {result}\n")

    # 测试批量请求（对比同步版本，看耗时）
    print("=== 测试批量异步请求 ===")
    test_urls = [
        "https://httpbin.org/ip",
        "https://httpbin.org/user-agent",
        "https://httpbin.org/delay/1"  # 延迟1秒的接口
    ]
    # 调用封装的计时+批量请求函数（全程用asyncio.run驱动，无事件循环操作）
    batch_results, total_time = asyncio.run(run_batch_test(test_urls))

    # 打印批量请求结果
    for idx, (status, result) in enumerate(batch_results):
        print(f"URL {idx + 1} 状态码: {status}")
        print(f"URL {idx + 1} 内容: {result[:100]}...")  # 只打印前100字符
    print(f"\n批量异步请求耗时: {total_time:.2f}秒")