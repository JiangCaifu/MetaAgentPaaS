from fastapi import FastAPI, HTTPException
from weather_tool import WeatherTool  # 导入你的天气工具类
import os
import asyncio
from scripts.crawl_scenic_data import crawl_scenic_data, save_scenic_data_to_json

app = FastAPI()
weather_tool = WeatherTool()
# 3. 配置 JSON 文件路径（与爬虫、后续 Agent 保持一致）
SCENIC_JSON_PATH = "db/data/scenic_spots.json"

@app.get("/weather/{city}")
async def get_weather(city: str):
    result = await weather_tool._arun(city)
    return {"city": city, "weather": result}


# 4. 核心测试接口：调用爬虫（仅实现最基础的触发逻辑，便于后续复制到 Agent 中）
@app.post("/test/crawl-scenic", summary="临时测试：触发爬虫")
async def test_crawl_scenic():
    """
    临时测试接口：仅用于验证 FastAPI 能否正常调用爬虫
    后续和 Agent 集成时，可直接复制此函数内的核心逻辑
    """
    try:
        # 核心逻辑1：调用爬虫获取数据（后续集成 Agent 时，这行直接复用）
        scenic_data = crawl_scenic_data()

        # 核心逻辑2：保存数据到 JSON 文件（后续集成 Agent 时，这行直接复用）
        save_scenic_data_to_json(scenic_data, SCENIC_JSON_PATH)

        # 返回简单测试结果（后续集成 Agent 时，可修改返回格式适配 Agent 需求）
        return {
            "status": "success",
            "message": "爬虫调用成功，数据已保存",
            "data_count": len(scenic_data),
            "file_path": SCENIC_JSON_PATH
        }
    except Exception as e:
        # 极简异常处理（后续集成 Agent 时，可适配 Agent 的日志/异常体系）
        raise HTTPException(status_code=500, detail=f"爬虫调用失败：{str(e)}")


# 5. 可选：新增一个简单查询接口，验证数据是否生成（测试用）
@app.get("/test/query-scenic", summary="临时测试：查询生成的数据")
async def test_query_scenic():
    """临时查询接口：验证数据是否正常生成（测试完可删除）"""
    if not os.path.exists(SCENIC_JSON_PATH):
        raise HTTPException(status_code=404, detail="数据文件不存在，请先调用爬取接口")
    # 直接返回文件路径（后续集成 Agent 时，可改为读取并返回数据）
    return {
        "status": "success",
        "message": "数据文件存在",
        "file_path": SCENIC_JSON_PATH,
        "file_exists": os.path.exists(SCENIC_JSON_PATH)
    }



# 运行：uvicorn test_fastapi:app --reload
# 访问：http://127.0.0.1:8000/weather/北京
if __name__ == "__main__":
    #vector_store = QdrantVectorStore()
    import uvicorn

    uvicorn.run(
        app="main:app",
        host="0.0.0.0",
        port=8000,
        reload=False
    )