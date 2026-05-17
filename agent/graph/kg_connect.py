# ========================================
# 第10周任务：知识图谱检索模块（NetworkX版）
# 替代Neo4j，使用纯Python知识图谱
# ========================================
from agent.graph.kg_service import TourismKnowledgeGraph
from typing import List, Dict

class TourismKGRetriever:
    """知识图谱检索器（NetworkX版，兼容Neo4j接口风格）"""
    
    def __init__(self):
        self.kg = TourismKnowledgeGraph()
    
    def query_scenic_by_city(self, city: str) -> List[Dict]:
        """查询城市下辖景点（类Cypher风格）"""
        spots = self.kg.get_city_scenic_spots(city)
        result = []
        for spot in spots:
            result.append({
                "name": spot["name"],
                "open_time": spot["open_time"],
                "price": spot["price"],
                "desc": spot["desc"]
            })
        return result
    
    def query_traffic_by_spot(self, spot_name: str) -> List[Dict]:
        """查询景点配套交通（类Cypher风格）"""
        traffic = self.kg.get_scenic_traffic(spot_name)
        result = []
        for t in traffic:
            result.append({
                "name": f"{t['type']}{t['line']}",
                "type": t["type"],
                "line": t["line"],
                "station": t["station"]
            })
        return result
    
    def query_recommend_by_spot(self, spot_name: str) -> List[Dict]:
        """查询景点推荐联动（类Cypher风格）"""
        recommends = self.kg.get_recommend_spots(spot_name)
        result = []
        for r in recommends:
            result.append({
                "name": r["name"],
                "desc": r["desc"]
            })
        return result
    
    def query_relics_by_city(self, city: str) -> List[Dict]:
        """查询城市文物收藏（类Cypher风格）"""
        relics = self.kg.get_city_cultural_relics(city)
        result = []
        for r in relics:
            result.append({
                "spot": r["spot"],
                "relic": r["relic"],
                "era": r["era"]
            })
        return result
    
    def get_kg_context(self, user_query: str) -> str:
        """简易意图匹配获取图谱上下文"""
        ctx = ""
        city_spots = []
        
        # 识别城市
        cities = ["北京", "上海", "广州", "深圳"]
        for city in cities:
            if city in user_query:
                city_spots.append(city)
        
        # 识别景点
        spots = ["故宫", "世界之窗", "东部华侨城", "欢乐谷", "外滩", "豫园", "东方明珠"]
        target_spots = [s for s in spots if s in user_query]
        
        # 推荐/游玩意图
        if "推荐" in user_query or "游玩" in user_query or "景点" in user_query:
            for city in city_spots:
                res = self.query_scenic_by_city(city)
                if res:
                    ctx += f"【{city}景点】\n"
                    for spot in res[:3]:
                        ctx += f"- {spot['name']}：{spot['desc']}，开放时间：{spot['open_time']}，票价：{spot['price']}\n"
        
        # 交通意图
        if "怎么去" in user_query or "交通" in user_query or "乘车" in user_query:
            for spot in target_spots:
                res = self.query_traffic_by_spot(spot)
                if res:
                    ctx += f"【{spot}交通】\n"
                    for t in res:
                        ctx += f"- 可乘坐{t['type']}{t['line']}到{t['station']}\n"
        
        # 联动推荐意图
        if "一起" in user_query or "周边" in user_query or "附近" in user_query:
            for spot in target_spots:
                res = self.query_recommend_by_spot(spot)
                if res:
                    ctx += f"【{spot}推荐】\n"
                    for r in res[:2]:
                        ctx += f"- 推荐游玩：{r['name']}（{r['desc']}）\n"
        
        # 文物/历史意图
        if "文物" in user_query or "历史" in user_query or "古迹" in user_query:
            for city in city_spots:
                res = self.query_relics_by_city(city)
                if res:
                    ctx += f"【{city}文物】\n"
                    for r in res:
                        ctx += f"- {r['spot']}收藏：{r['relic']}（{r['era']}）\n"
        
        return ctx.strip()
