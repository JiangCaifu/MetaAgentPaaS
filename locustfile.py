# locustfile.py
# ========================================
# Locust 性能压测脚本
# 功能：测试文旅问答API的并发性能和缓存效果
# 使用：locust -f locustfile.py --host=http://localhost:8000
# ========================================

import json
import random
from locust import HttpUser, task, between, events


# 测试数据集
TOURISM_QUERIES = [
    "北京有什么好玩的地方？",
    "上海有哪些景点？",
    "深圳有什么好玩的？",
    "广州必去景点推荐",
    "故宫几点开门？",
    "颐和园开放时间",
    "八达岭长城怎么去？",
    "外滩在哪里？",
    "世界之窗门票多少钱？",
    "北京天气怎么样？",
    "上海今天天气如何？",
    "推荐北京的景点",
    "广州有什么文物？",
    "深圳东部华侨城怎么去？",
    "故宫周边有什么推荐的？",
]

CITY_NAMES = ["北京", "上海", "深圳", "广州"]

SPOT_NAMES = ["故宫", "颐和园", "八达岭长城", "外滩", "世界之窗"]


class TourismAPIUser(HttpUser):
    """模拟文旅API用户"""

    # 请求间隔1-3秒（模拟真实用户行为）
    wait_time = between(1, 3)

    @task(5)
    def tourism_query(self):
        """核心接口：文旅问答（权重最高）"""
        query = random.choice(TOURISM_QUERIES)
        self.client.post(
            "/api/tourism/query",
            json={
                "user_query": query,
                "tenant_id": "tenant_001",
                "tenant_name": "文旅助手",
            },
            name="/api/tourism/query",
        )

    @task(3)
    def kg_city_spots(self):
        """知识图谱：查询城市景点"""
        city = random.choice(CITY_NAMES)
        self.client.get(
            f"/api/kg/city/{city}",
            name="/api/kg/city/{city}",
        )

    @task(2)
    def kg_scenic_traffic(self):
        """知识图谱：查询景点交通"""
        spot = random.choice(SPOT_NAMES)
        self.client.get(
            f"/api/kg/scenic/{spot}/traffic",
            name="/api/kg/scenic/{spot}/traffic",
        )

    @task(1)
    def health_check(self):
        """健康检查"""
        self.client.get("/health", name="/health")

    @task(1)
    def cache_stats(self):
        """缓存统计"""
        self.client.get("/api/cache/stats", name="/api/cache/stats")


class CacheHitUser(HttpUser):
    """缓存命中率测试：重复查询相同问题"""

    wait_time = between(0.5, 1.5)

    def on_start(self):
        """每个用户启动时固定一个查询，反复请求测试缓存"""
        self.fixed_query = random.choice(TOURISM_QUERIES)

    @task
    def repeated_query(self):
        """重复查询同一问题，测试缓存命中率"""
        self.client.post(
            "/api/tourism/query",
            json={
                "user_query": self.fixed_query,
                "tenant_id": "tenant_001",
                "tenant_name": "文旅助手",
            },
            name="/api/tourism/query [cache-test]",
        )


# 压测结果统计
@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """压测结束时输出摘要"""
    print("\n" + "=" * 60)
    print("压测结束，请查看以下关键指标：")
    print("=" * 60)
    print("1. 缓存统计：curl http://localhost:8000/api/cache/stats")
    print("2. 服务健康：curl http://localhost:8000/health")
    print("3. Locust报告：浏览器打开 http://localhost:8089")
    print("=" * 60)
