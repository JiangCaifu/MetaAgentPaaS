import os
import time

import requests
from dotenv import load_dotenv
import asyncio
from langchain_core.tools import BaseTool, tool
from typing import Optional
# 复用项目现有日志配置
from utils.logger_config import setup_logger

load_dotenv()
logger = setup_logger(name="WeatherTool")


@tool
def query_weather(city: str) -> str:
    """
    用于查询指定城市的实时天气信息，辅助文旅出行推荐
    参数：city - 城市名称（如"北京"、"西安"）
    返回：包含温度、天气状况、风力的字符串
    """
    try:
        api_key = os.getenv("WEATHER_API_KEY")
        api_url = os.getenv("WEATHER_API_URL")
        if not api_key or not api_url:
            raise ValueError("天气API密钥或URL未配置")

        # 调用高德天气API（示例，可替换为其他API）
        params = {
            "key": api_key,
            "city": city,
            "extensions": "base",  # 查询实时天气
            "output": "json"
        }
        response = requests.get(api_url, params=params, timeout=10)
        response.raise_for_status()  # 抛出HTTP错误
        data = response.json()

        # 解析返回结果
        if data.get("status") != "1":
            raise Exception(f"天气查询失败：{data.get('info', '未知错误')}")
        lives = data.get("lives", [])
        if not lives:
            return f"未查询到{city}的天气信息"

        weather_info = lives[0]
        return (f"{city}实时天气：{weather_info['weather']}，温度{weather_info['temperature']}℃，"
                f"湿度{weather_info['humidity']}%，{weather_info['winddirection']}{weather_info['windpower']}级")
    except Exception as e:
        logger.error(f"天气查询工具调用失败：{str(e)}")
        return f"天气查询失败：{str(e)}"
query_weather.name = "query_weather"
query_weather.description = "用于查询指定城市的实时天气信息，参数仅传入城市名称（如北京、上海、深圳）"

# 若需兼容LangChain旧版本，可使用类继承方式定义
class WeatherTool(BaseTool):
    name: str = "query_weather"
    description: str = "用于查询指定城市的实时天气信息，参数为城市名称（如'北京'）"

    def _run(self, city: str) -> str:
        return query_weather.invoke(city)

    async def _arun(self, city: str) -> str:
        # 异步版本（适配项目FastAPI异步架构）
        return await asyncio.to_thread(query_weather, city)

if __name__ == "__main__":
    # 测试1：同步工具函数（正常场景）
    print("=== 同步函数测试（正常城市）===")
    result = query_weather.invoke("北京")
    print(result)

    # 测试2：同步类方法
    print("\n=== 同步类方法测试 ===")
    weather_tool = WeatherTool()
    result_class = weather_tool._run("上海")
    print(result_class)

    # 测试3：异常场景（无效城市/API错误）
    print("\n=== 异常场景测试 ===")

    result_error = query_weather.invoke("不存在的城市123")
    print(result_error)


    async def test_async():
        print("\n=== 异步方法测试 ===")
        weather_tool = WeatherTool()
        result_async = await weather_tool._arun("广州")
        print(result_async)

    time.sleep(1)
    # 运行异步测试
    asyncio.run(test_async())