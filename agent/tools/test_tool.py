from fastapi import FastAPI
from weather_tool import WeatherTool  # 导入你的天气工具类
import asyncio

app = FastAPI()
weather_tool = WeatherTool()

@app.get("/weather/{city}")
async def get_weather(city: str):
    result = await weather_tool._arun(city)
    return {"city": city, "weather": result}

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