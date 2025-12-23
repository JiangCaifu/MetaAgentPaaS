import aiohttp
from config import settings
import logging

logger = logging.getLogger("MetaAgentPaaS.tools")

class ScenicTool:
    """景点查询工具"""
    async def query_scenic(self, city: str) -> str:
        """
        异步查询城市景点信息（模拟真实API调用）
        :param city: 城市名称
        :return: 景点信息字符串
        """
        try:
            # 模拟调用外部API（替换为真实接口）
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url=settings.SCENIC_API_URL or "https://httpbin.org/get",
                    params={"city": city, "key": settings.SCENIC_API_KEY},
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    result = await response.json()
                    # 模拟构造景点数据
                    scenic_data = f"""【{city}景点信息】
1. 故宫（5A）：门票60元，推荐理由：明清皇宫，世界文化遗产；
2. 颐和园（5A）：门票30元，推荐理由：皇家园林，山水景观；
3. 八达岭长城（5A）：门票40元，推荐理由：万里长城精华段。"""
                    logger.info(f"景点查询成功（城市：{city}）")
                    return scenic_data
        except Exception as e:
            logger.error(f"景点查询失败（城市：{city}），错误：{str(e)}")
            return f"景点查询失败：{str(e)}"