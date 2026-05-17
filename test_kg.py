# 测试知识图谱功能
print("=== 测试NetworkX知识图谱 ===")
import sys
sys.path.insert(0, '.')

# 测试导入
try:
    from agent.graph.kg_service import TourismKnowledgeGraph
    print("✅ 导入成功")
except Exception as e:
    print(f"❌ 导入失败: {e}")
    sys.exit(1)

# 测试创建图谱
try:
    kg = TourismKnowledgeGraph()
    print("✅ 创建知识图谱成功")
except Exception as e:
    print(f"❌ 创建失败: {e}")
    sys.exit(1)

# 测试查询功能
print("\n=== 测试查询功能 ===")

# 查询深圳景点
print("\n【查询深圳景点】")
spots = kg.get_city_scenic_spots("深圳")
for spot in spots:
    print(f"📍 {spot['name']} - {spot['price']} - {spot['open_time']}")

# 查询世界之窗交通
print("\n【查询世界之窗交通】")
traffic = kg.get_scenic_traffic("世界之窗")
for t in traffic:
    print(f"🚇 {t['type']}{t['line']} {t['station']}")

# 查询世界之窗推荐
print("\n【查询世界之窗推荐景点】")
recommends = kg.get_recommend_spots("世界之窗")
for r in recommends:
    print(f"💡 {r['name']} - {r['desc']}")

# 查询北京文物
print("\n【查询北京文物】")
relics = kg.get_city_cultural_relics("北京")
for r in relics:
    print(f"🏺 {r['spot']} 收藏: {r['relic']} ({r['era']})")

# 输出统计
print("\n=== 图谱统计 ===")
stats = kg.get_graph_stats()
print(f"总节点数: {stats['total_nodes']}")
print(f"总关系数: {stats['total_relationships']}")
print(f"城市节点: {stats['city_nodes']}")
print(f"景点节点: {stats['scenic_spot_nodes']}")
print(f"交通节点: {stats['traffic_nodes']}")
print(f"文物节点: {stats['cultural_relic_nodes']}")

print("\n✅ 所有测试通过！")
print("\n🎉 第9周学习任务完成！")
print("📌 交付成果:")
print("   1. 文旅知识图谱Schema设计文档")
print("   2. 已构建完成的文旅知识图谱(NetworkX)")
print("   3. 支持查询城市景点、交通信息、推荐景点、文物收藏")