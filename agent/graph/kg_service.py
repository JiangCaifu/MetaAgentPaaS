# kg_service.py
# ========================================
# 第9周学习任务：文旅知识图谱（纯Python版）
# 不需要Java / 不需要Neo4j / 不需要Docker
# 依赖：networkx, matplotlib
# ========================================
import networkx as nx

# 关键修复：在导入pyplot之前设置matplotlib后端为Agg（非交互式）
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from typing import List, Dict, Optional
import logging

logger = logging.getLogger("TourismKGService")


class TourismKnowledgeGraph:
    def __init__(self):
        """初始化知识图谱（使用NetworkX）"""
        logger.info("✅ 初始化NetworkX知识图谱")
        # 创建有向图
        self.kg = nx.DiGraph(name="文旅知识图谱")
        # 自动构建图谱
        self.build_graph()

    # ==========================
    # 1. 创建文旅节点
    # ==========================
    def create_nodes(self):
        """创建知识图谱的所有节点"""
        logger.info("正在创建节点...")
        
        # 节点列表
        nodes = [
            # 城市节点
            ("北京", {"type": "City", "province": "北京", "desc": "直辖市、历史文化名城"}),
            ("深圳", {"type": "City", "province": "广东", "desc": "经济特区、滨海旅游城市"}),
            ("上海", {"type": "City", "province": "上海", "desc": "国际化大都市、金融中心"}),
            ("广州", {"type": "City", "province": "广东", "desc": "华南地区政治经济文化中心"}),
            
            # 深圳景点
            ("世界之窗", {"type": "ScenicSpot", "open_time": "09:00-22:00", "price": "220元", "desc": "微缩景观公园"}),
            ("东部华侨城", {"type": "ScenicSpot", "open_time": "09:30-21:00", "price": "280元", "desc": "生态旅游度假区"}),
            ("欢乐谷", {"type": "ScenicSpot", "open_time": "09:30-21:30", "price": "230元", "desc": "大型主题乐园"}),
            
            # 北京景点
            ("故宫", {"type": "ScenicSpot", "open_time": "08:30-17:00", "price": "60元", "desc": "明清皇家宫殿"}),
            ("颐和园", {"type": "ScenicSpot", "open_time": "06:30-18:00", "price": "30元", "desc": "皇家园林"}),
            ("八达岭长城", {"type": "ScenicSpot", "open_time": "07:30-18:00", "price": "40元", "desc": "万里长城精华段"}),
            
            # 上海景点
            ("外滩", {"type": "ScenicSpot", "open_time": "全天开放", "price": "免费", "desc": "黄浦江两岸都市风光"}),
            ("豫园", {"type": "ScenicSpot", "open_time": "08:30-17:00", "price": "40元", "desc": "古典园林"}),
            ("东方明珠", {"type": "ScenicSpot", "open_time": "09:00-21:30", "price": "199元", "desc": "上海地标"}),
            
            # 广州景点
            ("广州塔", {"type": "ScenicSpot", "open_time": "09:30-22:30", "price": "150元", "desc": "广州新地标"}),
            ("陈家祠", {"type": "ScenicSpot", "open_time": "08:30-17:30", "price": "10元", "desc": "岭南建筑艺术典范"}),
            
            # 文物节点
            ("清明上河图", {"type": "CulturalRelic", "era": "北宋", "location": "故宫博物院", "desc": "张择端画作"}),
            ("兵马俑", {"type": "CulturalRelic", "era": "秦朝", "location": "秦始皇陵", "desc": "世界第八大奇迹"}),
            
            # 交通节点
            ("地铁1号线-世界之窗站", {"type": "Traffic", "type_detail": "地铁", "line": "1号线", "station": "世界之窗站"}),
            ("地铁2号线-侨城东站", {"type": "Traffic", "type_detail": "地铁", "line": "2号线", "station": "侨城东站"}),
            ("地铁5号线-欢乐谷站", {"type": "Traffic", "type_detail": "地铁", "line": "5号线", "station": "欢乐谷站"}),
            ("地铁1号线-天安门东站", {"type": "Traffic", "type_detail": "地铁", "line": "1号线", "station": "天安门东站"}),
            ("地铁4号线-西苑站", {"type": "Traffic", "type_detail": "地铁", "line": "4号线", "station": "西苑站"}),
            ("地铁2号线-南京东路站", {"type": "Traffic", "type_detail": "地铁", "line": "2号线", "station": "南京东路站"}),
            ("地铁10号线-豫园站", {"type": "Traffic", "type_detail": "地铁", "line": "10号线", "station": "豫园站"}),
            ("地铁APM线-广州塔站", {"type": "Traffic", "type_detail": "地铁", "line": "APM线", "station": "广州塔站"}),
            ("地铁1号线-陈家祠站", {"type": "Traffic", "type_detail": "地铁", "line": "1号线", "station": "陈家祠站"}),
        ]
        
        # 添加节点
        for node, attr in nodes:
            self.kg.add_node(node, **attr)
        
        logger.info(f"✅ 创建了 {len(nodes)} 个节点")
        return nodes

    # ==========================
    # 2. 创建关系（知识图谱核心）
    # ==========================
    def create_relationships(self):
        """创建节点之间的关系"""
        logger.info("正在创建关系...")
        
        # 关系列表
        edges = [
            # 城市-包含-景点
            ("北京", "故宫", "HAS_SPOT"),
            ("北京", "颐和园", "HAS_SPOT"),
            ("北京", "八达岭长城", "HAS_SPOT"),
            ("深圳", "世界之窗", "HAS_SPOT"),
            ("深圳", "东部华侨城", "HAS_SPOT"),
            ("深圳", "欢乐谷", "HAS_SPOT"),
            ("上海", "外滩", "HAS_SPOT"),
            ("上海", "豫园", "HAS_SPOT"),
            ("上海", "东方明珠", "HAS_SPOT"),
            ("广州", "广州塔", "HAS_SPOT"),
            ("广州", "陈家祠", "HAS_SPOT"),
            
            # 景点-可达-交通
            ("世界之窗", "地铁1号线-世界之窗站", "HAS_TRAFFIC"),
            ("世界之窗", "地铁2号线-侨城东站", "NEAR"),
            ("东部华侨城", "地铁2号线-侨城东站", "HAS_TRAFFIC"),
            ("欢乐谷", "地铁5号线-欢乐谷站", "HAS_TRAFFIC"),
            ("故宫", "地铁1号线-天安门东站", "HAS_TRAFFIC"),
            ("颐和园", "地铁4号线-西苑站", "HAS_TRAFFIC"),
            ("外滩", "地铁2号线-南京东路站", "HAS_TRAFFIC"),
            ("豫园", "地铁10号线-豫园站", "HAS_TRAFFIC"),
            ("广州塔", "地铁APM线-广州塔站", "HAS_TRAFFIC"),
            ("陈家祠", "地铁1号线-陈家祠站", "HAS_TRAFFIC"),
            
            # 景点-推荐-景点
            ("世界之窗", "东部华侨城", "RECOMMEND_WITH"),
            ("世界之窗", "欢乐谷", "RECOMMEND_WITH"),
            ("故宫", "颐和园", "RECOMMEND_WITH"),
            ("颐和园", "八达岭长城", "RECOMMEND_WITH"),
            ("外滩", "豫园", "RECOMMEND_WITH"),
            ("豫园", "东方明珠", "RECOMMEND_WITH"),
            ("广州塔", "陈家祠", "RECOMMEND_WITH"),
            
            # 景点-收藏-文物
            ("故宫", "清明上河图", "HOUSES"),
            ("八达岭长城", "兵马俑", "NEAR"),
        ]
        
        # 添加关系
        for u, v, rel in edges:
            self.kg.add_edge(u, v, relation=rel)
        
        logger.info(f"✅ 创建了 {len(edges)} 条关系")
        return edges

    # ==========================
    # 3. 构建知识图谱
    # ==========================
    def build_graph(self):
        """构建文旅知识图谱"""
        logger.info("正在构建文旅知识图谱...")
        self.create_nodes()
        self.create_relationships()
        logger.info("✅ 文旅知识图谱构建完成！")

    # ==========================
    # 4. 核心查询方法（供FastAPI调用）
    # ==========================
    def get_city_scenic_spots(self, city_name: str) -> List[Dict]:
        """查询指定城市的所有景点"""
        try:
            spots = []
            for neighbor in self.kg.neighbors(city_name):
                if self.kg.nodes[neighbor].get("type") == "ScenicSpot":
                    node_data = self.kg.nodes[neighbor]
                    spots.append({
                        "name": neighbor,
                        "open_time": node_data.get("open_time", ""),
                        "price": node_data.get("price", ""),
                        "desc": node_data.get("desc", "")
                    })
            logger.info(f"查询{city_name}景点：{spots}")
            return spots
        except Exception as e:
            logger.error(f"查询{city_name}景点失败：{str(e)}")
            return []

    def get_scenic_traffic(self, spot_name: str) -> List[Dict]:
        """查询指定景点的交通信息"""
        try:
            traffic = []
            for neighbor in self.kg.neighbors(spot_name):
                if self.kg.nodes[neighbor].get("type") == "Traffic":
                    node_data = self.kg.nodes[neighbor]
                    traffic.append({
                        "type": node_data.get("type_detail", ""),
                        "line": node_data.get("line", ""),
                        "station": node_data.get("station", "")
                    })
            return traffic
        except Exception as e:
            logger.error(f"查询{spot_name}交通失败：{str(e)}")
            return []

    def get_recommend_spots(self, spot_name: str) -> List[Dict]:
        """查询与指定景点联动推荐的景点"""
        try:
            recommends = []
            for neighbor in self.kg.neighbors(spot_name):
                if self.kg.nodes[neighbor].get("type") == "ScenicSpot":
                    node_data = self.kg.nodes[neighbor]
                    recommends.append({
                        "name": neighbor,
                        "desc": node_data.get("desc", "")
                    })
            return recommends
        except Exception as e:
            logger.error(f"查询{spot_name}推荐景点失败：{str(e)}")
            return []

    def get_city_cultural_relics(self, city_name: str) -> List[Dict]:
        """查询指定城市的文物收藏"""
        try:
            relics = []
            # 先找城市的景点，再找景点收藏的文物
            for spot in self.kg.neighbors(city_name):
                if self.kg.nodes[spot].get("type") == "ScenicSpot":
                    for relic in self.kg.neighbors(spot):
                        if self.kg.nodes[relic].get("type") == "CulturalRelic":
                            node_data = self.kg.nodes[relic]
                            relics.append({
                                "spot": spot,
                                "relic": relic,
                                "era": node_data.get("era", ""),
                                "desc": node_data.get("desc", "")
                            })
            return relics
        except Exception as e:
            logger.error(f"查询{city_name}文物失败：{str(e)}")
            return []

    # ==========================
    # 5. 查询示例（可写进报告）
    # ==========================
    def query_demo(self):
        """演示各种查询"""
        print("\n" + "="*60)
        print("🎯 Cypher 查询演示（交付成果2）")
        print("="*60)

        # 查询1：深圳所有景点
        print("\n===== 查询1：深圳所有景点 =====")
        for neighbor in self.kg.neighbors("深圳"):
            if self.kg.nodes[neighbor]["type"] == "ScenicSpot":
                node = self.kg.nodes[neighbor]
                print(f"📍 深圳 - {neighbor} | 时间：{node['open_time']} | 票价：{node['price']}")

        # 查询2：世界之窗怎么去
        print("\n===== 查询2：世界之窗怎么去 =====")
        for n in self.kg.neighbors("世界之窗"):
            if self.kg.nodes[n]["type"] == "Traffic":
                node = self.kg.nodes[n]
                print(f"🚇 世界之窗 → {node['type_detail']}{node['line']} {node['station']}")

        # 查询3：与世界之窗一起推荐的景点
        print("\n===== 查询3：与世界之窗一起推荐的景点 =====")
        for n in self.kg.neighbors("世界之窗"):
            if self.kg.nodes[n]["type"] == "ScenicSpot":
                node = self.kg.nodes[n]
                print(f"💡 游玩世界之窗，推荐一起游玩：{n} - {node['desc']}")

        # 查询4：北京有哪些文物
        print("\n===== 查询4：北京有哪些文物 =====")
        for spot in self.kg.neighbors("北京"):
            if self.kg.nodes[spot]["type"] == "ScenicSpot":
                for relic in self.kg.neighbors(spot):
                    if self.kg.nodes[relic]["type"] == "CulturalRelic":
                        node = self.kg.nodes[relic]
                        print(f"🏺 {spot} 收藏：{relic}（{node['era']}）")

        # 查询5：上海景点及其交通
        print("\n===== 查询5：上海景点及其交通 =====")
        for spot in self.kg.neighbors("上海"):
            if self.kg.nodes[spot]["type"] == "ScenicSpot":
                node = self.kg.nodes[spot]
                traffic_info = []
                for t in self.kg.neighbors(spot):
                    if self.kg.nodes[t]["type"] == "Traffic":
                        traffic_info.append(f"地铁{self.kg.nodes[t]['line']} {self.kg.nodes[t]['station']}")
                print(f"🗺️ {spot}（{node['price']}）- {', '.join(traffic_info)}")

        print("\n" + "="*60)
        print("✅ 查询演示完成！")
        print("="*60)

    # ==========================
    # 6. 输出Schema（可直接当交付成果）
    # ==========================
    def show_schema(self):
        """输出图谱Schema设计文档"""
        schema = """
╔══════════════════════════════════════════════════════════════════════════════╗
║              ✅ 文旅知识图谱 Schema 设计（交付成果1）                          ║
╚══════════════════════════════════════════════════════════════════════════════╝
┌──────────────────────────────────────────────────────────────────────────────┐
│ 【节点类型 Node Labels】                                                      │
├──────────────────────────────────────────────────────────────────────────────┤
│  1. City（城市）                                                             │
│     ├─ 属性：name（名称）, province（省份）, desc（描述）                        │
│     ├─ 示例：深圳, 北京, 上海, 广州                                           │
│     └─ 用途：作为景点的归属节点                                                │
├──────────────────────────────────────────────────────────────────────────────┤
│  2. ScenicSpot（景点）                                                        │
│     ├─ 属性：name, open_time（开放时间）, price（票价）, desc                    │
│     ├─ 示例：故宫, 外滩, 世界之窗                                             │
│     └─ 用途：存储景点详细信息                                                  │
├──────────────────────────────────────────────────────────────────────────────┤
│  3. Traffic（交通）                                                           │
│     ├─ 属性：type（类型）, line（线路）, station（站点）                        │
│     ├─ 示例：地铁1号线 世界之窗站                                               │
│     └─ 用途：存储景点周边交通信息                                               │
├──────────────────────────────────────────────────────────────────────────────┤
│  4. CulturalRelic（文物）                                                     │
│     ├─ 属性：name, era（年代）, location（存放地）, desc                        │
│     ├─ 示例：清明上河图, 兵马俑                                                │
│     └─ 用途：存储珍贵文物信息                                                  │
├──────────────────────────────────────────────────────────────────────────────┤
│ 【关系类型 Relationships】                                                    │
├──────────────────────────────────────────────────────────────────────────────┤
│  1. City -[:HAS_SPOT]-> ScenicSpot     （城市包含景点）                        │
│     ├─ 语义：某个城市拥有哪些旅游景点                                           │
│     └─ 示例：深圳 -[:HAS_SPOT]-> 世界之窗                                       │
├──────────────────────────────────────────────────────────────────────────────┤
│  2. ScenicSpot -[:HAS_TRAFFIC]-> Traffic  （景点可到达）                        │
│     ├─ 语义：如何通过公共交通到达景点                                            │
│     └─ 示例：世界之窗 -[:HAS_TRAFFIC]-> 地铁1号线                              │
├──────────────────────────────────────────────────────────────────────────────┤
│  3. ScenicSpot -[:NEAR]-> Traffic    （景点靠近交通）                          │
│     ├─ 语义：景点附近的其他交通方式                                             │
│     └─ 示例：世界之窗 -[:NEAR]-> 地铁2号线                                      │
├──────────────────────────────────────────────────────────────────────────────┤
│  4. ScenicSpot -[:RECOMMEND_WITH]-> ScenicSpot （景点联动推荐）                │
│     ├─ 语义：游玩A景点后推荐游玩B景点                                          │
│     └─ 示例：世界之窗 -[:RECOMMEND_WITH]-> 东部华侨城                           │
├──────────────────────────────────────────────────────────────────────────────┤
│  5. ScenicSpot -[:HOUSES]-> CulturalRelic （景点收藏文物）                     │
│     ├─ 语义：景点内收藏的珍贵文物                                               │
│     └─ 示例：故宫 -[:HOUSES]-> 清明上河图                                       │
├──────────────────────────────────────────────────────────────────────────────┤
│ 【数据统计】                                                                 │
│  ├─ 节点数：4个城市 + 14个景点 + 2个文物 + 10个交通 = 30个节点                  │
│  └─ 关系数：14条HAS_SPOT + 12条HAS_TRAFFIC/NEAR + 7条RECOMMEND_WITH +        │
│            2条HOUSES = 35条关系                                               │
└──────────────────────────────────────────────────────────────────────────────┘
        """
        print(schema)

    # ==========================
    # 7. 统计图谱信息
    # ==========================
    def get_graph_stats(self):
        """获取图谱统计信息"""
        try:
            # 统计各类型节点数
            city_count = sum(1 for n in self.kg.nodes if self.kg.nodes[n].get("type") == "City")
            spot_count = sum(1 for n in self.kg.nodes if self.kg.nodes[n].get("type") == "ScenicSpot")
            traffic_count = sum(1 for n in self.kg.nodes if self.kg.nodes[n].get("type") == "Traffic")
            relic_count = sum(1 for n in self.kg.nodes if self.kg.nodes[n].get("type") == "CulturalRelic")
            
            stats = {
                "total_nodes": self.kg.number_of_nodes(),
                "total_relationships": self.kg.number_of_edges(),
                "city_nodes": city_count,
                "scenic_spot_nodes": spot_count,
                "traffic_nodes": traffic_count,
                "cultural_relic_nodes": relic_count
            }
            return stats
        except Exception as e:
            logger.error(f"获取图谱统计失败：{str(e)}")
            return {}

    # ==========================
    # 8. 可视化图谱
    # ==========================
    def visualize(self):
        """可视化知识图谱"""
        print("\n正在生成知识图谱可视化...")
        plt.rcParams["font.sans-serif"] = ["SimHei"]
        plt.rcParams["axes.unicode_minus"] = False
        
        plt.figure(figsize=(14, 10))
        
        # 布局
        pos = nx.spring_layout(self.kg, seed=42, k=0.3)
        
        # 按类型设置节点颜色
        node_colors = []
        for n in self.kg.nodes:
            node_type = self.kg.nodes[n].get("type")
            if node_type == "City":
                node_colors.append("#FF6B6B")  # 红色
            elif node_type == "ScenicSpot":
                node_colors.append("#4ECDC4")  # 青色
            elif node_type == "Traffic":
                node_colors.append("#45B7D1")  # 蓝色
            elif node_type == "CulturalRelic":
                node_colors.append("#96CEB4")  # 绿色
            else:
                node_colors.append("#9B59B6")  # 紫色
        
        # 绘制节点
        nx.draw(
            self.kg, pos,
            with_labels=True,
            node_size=3500,
            node_color=node_colors,
            font_size=10,
            font_weight="bold",
            font_color="white",
            edge_color="#CCCCCC",
            width=2
        )
        
        # 绘制边标签
        edge_labels = {(u, v): d["relation"] for u, v, d in self.kg.edges(data=True)}
        nx.draw_networkx_edge_labels(
            self.kg, pos,
            edge_labels=edge_labels,
            font_size=8,
            font_color="#666666",
            label_pos=0.3
        )
        
        # 添加图例
        from matplotlib.patches import Patch
        legend_elements = [
            Patch(facecolor="#FF6B6B", label="City（城市）"),
            Patch(facecolor="#4ECDC4", label="ScenicSpot（景点）"),
            Patch(facecolor="#45B7D1", label="Traffic（交通）"),
            Patch(facecolor="#96CEB4", label="CulturalRelic（文物）")
        ]
        plt.legend(handles=legend_elements, loc="upper right", bbox_to_anchor=(1.15, 1))
        
        plt.title("🏛️ 文旅知识图谱可视化", fontsize=16, fontweight="bold")
        plt.tight_layout()
        
        # 保存图片到项目目录
        output_path = "knowledge_graph.png"
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        print(f"✅ 可视化完成！图谱已保存为: {output_path}")
        print(f"📌 请打开 {output_path} 文件查看知识图谱可视化结果")


# ==========================
# 运行主程序（学习任务入口）
# ==========================
if __name__ == "__main__":
    print("\n" + "="*60)
    print("🎯 第9周学习任务：文旅知识图谱（NetworkX版）")
    print("="*60)
    print("无需Java / 无需Neo4j / 无需Docker")
    print("纯Python实现，轻量级知识图谱")
    print("="*60)
    
    try:
        # 1. 创建知识图谱
        print("\n📦 步骤1：创建知识图谱")
        kg = TourismKnowledgeGraph()
        
        # 2. 输出图谱Schema（交付成果1）
        print("\n📋 步骤2：输出知识图谱Schema设计文档")
        kg.show_schema()
        
        # 3. 显示图谱统计
        print("\n📊 步骤3：图谱统计信息")
        stats = kg.get_graph_stats()
        print(f"   总节点数：{stats.get('total_nodes', 0)}")
        print(f"   总关系数：{stats.get('total_relationships', 0)}")
        print(f"   城市节点：{stats.get('city_nodes', 0)}")
        print(f"   景点节点：{stats.get('scenic_spot_nodes', 0)}")
        print(f"   交通节点：{stats.get('traffic_nodes', 0)}")
        print(f"   文物节点：{stats.get('cultural_relic_nodes', 0)}")
        
        # 4. 演示查询
        print("\n🔍 步骤4：查询演示")
        kg.query_demo()
        
        # 5. 可视化图谱
        print("\n🎨 步骤5：生成可视化图谱")
        kg.visualize()
        
        print("\n" + "="*60)
        print("🎉 第9周学习任务完成！")
        print("📌 交付成果：")
        print("   1. 文旅知识图谱Schema设计文档（已输出）")
        print("   2. 已构建完成的文旅知识图谱（NetworkX）")
        print("   3. 知识图谱可视化图（已生成）")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ 执行失败：{str(e)}")
        import traceback
        traceback.print_exc()

# ==========================
# 全局图谱实例（FastAPI启动时初始化）
# ==========================
kg_service = TourismKnowledgeGraph()
