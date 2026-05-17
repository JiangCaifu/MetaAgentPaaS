import sys
import traceback

print("=== 诊断启动问题 ===")
print(f"Python路径: {sys.executable}")
print(f"Python版本: {sys.version}")

# 测试关键依赖
dependencies = ['fastapi', 'uvicorn', 'pydantic', 'aiohttp', 'dashscope', 'qdrant_client', 'langgraph']
print("\n=== 检查依赖 ===")
for dep in dependencies:
    try:
        __import__(dep)
        print(f"✅ {dep}")
    except ImportError as e:
        print(f"❌ {dep}: {e}")

# 测试导入main模块
print("\n=== 测试导入main模块 ===")
try:
    from main import app
    print("✅ 成功导入main模块")
except Exception as e:
    print(f"❌ 导入失败: {e}")
    traceback.print_exc()

print("\n=== 完成诊断 ===")
