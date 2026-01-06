import json
from langchain_core.tools import tool
from typing import Optional
# 复用项目现有日志配置
from utils.logger_config import setup_logger

logger = setup_logger(name="ScenicTool")

# 加载你第4周爬取的文旅数据（假设已保存为JSON文件）
SCENIC_DATA_PATH = "db/data/scenic_spots.json"  # 对应你爬取的数据路径


def load_scenic_data() -> dict:
    """加载本地文旅数据（景点名称→开放时间映射）"""
    try:
        with open(SCENIC_DATA_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        # 构建索引：景点名称→开放时间（便于快速查询）
        scenic_index = {}
        for item in data:
            name = item.get("name")
            open_time = item.get("open_time", "未公开")
            if name:
                scenic_index[name] = open_time
        return scenic_index
    except Exception as e:
        logger.error(f"加载文旅数据失败：{str(e)}")
        return {}


@tool
def query_scenic_open_time(scenic_name: str) -> str:
    """
    用于查询指定景点的开放时间信息
    参数：scenic_name - 景点名称（如"故宫博物院"、"兵马俑"）
    返回：景点开放时间字符串
    """
    scenic_index = load_scenic_data()
    if not scenic_index:
        return "文旅数据未加载，无法查询开放时间"

    # 模糊匹配（支持用户输入近似名称）
    matched = [name for name in scenic_index.keys() if scenic_name in name]
    if not matched:
        return f"未查询到'{scenic_name}'的开放时间信息"

    # 返回匹配结果（优先第一个精确匹配）
    open_time = scenic_index[matched[0]]
    return f"{matched[0]} 开放时间：{open_time}"