import json
import os
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
        # 新增：动态获取工具脚本所在目录，拼接绝对路径（彻底避免相对路径问题）
        # 步骤1：获取当前工具脚本的绝对目录
        TOOL_DIR = os.path.dirname(os.path.abspath(__file__))
        # 步骤2：拼接JSON文件的绝对路径（向上追溯到项目根目录→db/data/）
        # 若工具脚本在 agent/tools/ 下，需用 ../.. 回到项目根目录，根据实际目录调整
        ABSOLUTE_JSON_PATH = os.path.join(TOOL_DIR, "../../db/data/scenic_spots.json")
        # 步骤3：规范化路径（解决../的歧义，避免路径错误）
        ABSOLUTE_JSON_PATH = os.path.normpath(ABSOLUTE_JSON_PATH)
        with open(ABSOLUTE_JSON_PATH, "r", encoding="utf-8") as f:
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
query_scenic_open_time.name = "query_scenic_open_time"
query_scenic_open_time.description = "用于查询指定景点的开放时间和门票价格，参数仅传入景点完整名称（如故宫博物院、兵马俑）"

if __name__ == "__main__":
    print("=== 文旅景点开放时间查询工具验证 ===")

    # 测试场景1：精确匹配（存在的景点）
    print("\n1. 精确匹配测试（故宫博物院）")
    result1 = query_scenic_open_time.invoke({"scenic_name": "故宫博物院"})
    print(result1)

    # 测试场景2：模糊匹配（支持近似名称）
    print("\n2. 模糊匹配测试（兵马俑）")
    result2 = query_scenic_open_time.invoke({"scenic_name": "兵马俑"})
    print(result2)

    # 测试场景3：模糊匹配（简称匹配）
    print("\n3. 简称模糊匹配测试（黄山）")
    result3 = query_scenic_open_time.invoke({"scenic_name": "黄山"})
    print(result3)

    # 测试场景4：不存在的景点（异常场景）
    print("\n4. 异常场景测试（未知景点123）")
    result4 = query_scenic_open_time.invoke({"scenic_name": "未知景点123"})
    print(result4)

    # 测试场景5：数据加载失败（可选：删除scenic_spots.json后测试）
    # print("\n5. 数据加载失败测试（需手动删除JSON文件）")
    # result5 = query_scenic_open_time.invoke({"scenic_name": "颐和园"})
    # print(result5)