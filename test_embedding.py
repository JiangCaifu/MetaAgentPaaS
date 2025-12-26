# test_embedding.py
from llm.embedding_client import BailianEmbeddingClient

if __name__ == "__main__":
    # 初始化客户端
    client = BailianEmbeddingClient()

    # ========== 测试JSON文件向量化 ==========
    # 示例1：单文本JSON文件（texts_single.json）
    # 文件内容：{"text": "故宫旧称紫禁城，是明清两代的皇家宫殿"}
    #single_vector = client.get_embedding("故宫旧称紫禁城")

    #print(f"JSON单文本向量：{single_vector[0][0:5]}...（维度：{len(single_vector)}）")

    # 示例2：多文本JSON文件（texts_batch.json）
    # 文件内容：[{"text": "故宫位于北京中轴线中心"}, {"text": "兵马俑位于陕西西安临潼区"}]
    batch_result = client.get_embedding_from_json("./raw_travel_data.json")

    print(f"JSON多文本向量结果：{batch_result}")

