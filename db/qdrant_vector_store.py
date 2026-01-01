import os
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, PointStruct
from typing import List, Dict, Any
from db.text_chunking import TextChunkProcessor  # 导入上面的分块器
from llm.embedding_client import BailianEmbeddingClient
import json

load_dotenv()


# ---------------- 替换为你已实现的 Embedding 函数 ----------------
def your_embedding_function(texts: List[str]) :
    """
    调用你已完成的 Embedding API，生成文本向量
    :param texts: 分块后的文本列表
    :return: 向量列表，每个向量维度需和 Qdrant 集合配置一致
    """
    # 此处替换为你的实际 Embedding API 调用代码
    # 示例（伪代码）：
    # import requests
    # api_key = os.getenv("EMBEDDING_API_KEY")
    # response = requests.post(
    #     url="https://your-embedding-api.com/embeddings",
    #     headers={"Authorization": f"Bearer {api_key}"},
    #     json={"texts": texts}
    # )
    # return response.json()["embeddings"]
    try:
        client = BailianEmbeddingClient()
        json_str = json.dumps(sample_docs, ensure_ascii=False, indent=2)
        response = client.get_embedding_from_json(json_str)
        return response
    except Exception as e:
        raise Exception(f"向量化失败：{str(e)}")


class QdrantVectorStore:
    def __init__(
            self,
            collection_name: str = "meta_agent_paas_cultural_tourism",
            vector_dimension: int = 768,  # 根据你的 Embedding 模型调整（如通义是 768）
            distance: Distance = Distance.COSINE  # 向量相似度计算方式：余弦相似度
    ):
        # 连接本地 Qdrant 服务
        #self.client = QdrantClient(host="localhost", port=6333)   #本地有Qdrant服务启动时连接服务
        self.client = QdrantClient(path="./local_qdrant_data") # path 参数：指定本地存储数据的目录（会自动创建）
        self.collection_name = collection_name
        self.vector_dimension = vector_dimension
        self.distance = distance
        # 初始化分块器
        self.chunk_processor = TextChunkProcessor()
        # 创建集合（如果不存在）
        self._create_collection()

    def _create_collection(self):
        """创建 Qdrant 集合，定义向量维度和距离度量方式"""
        if not self.client.collection_exists(collection_name=self.collection_name):
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.vector_dimension,
                    distance=self.distance
                )
            )
            print(f"集合 {self.collection_name} 创建成功")
        else:
            print(f"集合 {self.collection_name} 已存在")

    def add_documents(self, documents: List[Dict[str, Any]]):
        """
        分块 → 生成向量 → 入库
        :param documents: 原始文档列表，格式 [{"id": "...", "content": "...", "metadata": {...}}]
        """
        # 1. 文本分块
        chunked_docs = self.chunk_processor.split_documents(documents)
        print(f"分块完成，共生成 {len(chunked_docs)} 个文本块")

        # 2. 批量生成向量
        texts = [doc["content"] for doc in chunked_docs]
        vectors = your_embedding_function(texts)
        print(f"向量生成完成，向量维度 {self.vector_dimension}")

        # 3. 构造 Qdrant 数据点并入库
        points = []
        for doc, vector in zip(chunked_docs, vectors):
            points.append(
                PointStruct(
                    id=doc["id"],  # 唯一 ID
                    vector=vector,  # 向量数据
                    payload={  # 附加元数据（用于检索后展示）
                        "content": doc["content"],
                        "metadata": doc["metadata"]
                    }
                )
            )

        # 批量插入 Qdrant
        self.client.upsert(
            collection_name=self.collection_name,
            points=points
        )
        print(f"成功入库 {len(points)} 个向量数据点")

    def search(self, query_text: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        语义检索：输入查询文本 → 生成向量 → 检索相似文本块
        :param query_text: 查询语句（如“北京的历史古迹有哪些”）
        :param top_k: 返回最相似的 top_k 个结果
        :return: 检索结果列表，包含相似度、文本内容、元数据
        """
        # 1. 生成查询向量
        query_vector = your_embedding_function([query_text])[0]

        # 2. Qdrant 向量检索
        search_result = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            limit=top_k,
            with_payload=True  # 返回 payload 中的内容和元数据
        )

        # 3. 格式化结果
        formatted_results = []
        for res in search_result:
            formatted_results.append({
                "score": res.score,  # 相似度分数（余弦相似度 0-1）
                "content": res.payload["content"],
                "metadata": res.payload["metadata"]
            })
        return formatted_results


# ---------------- 测试代码 ----------------
if __name__ == "__main__":
    # 初始化向量库
    vector_store = QdrantVectorStore()

    # 模拟原始文旅数据
    sample_docs = [
        {
            "id": "scenic_spot_1",
            "content": "故宫博物院，旧称紫禁城，位于北京中轴线的中心，是明清两代的皇家宫殿。故宫以三大殿为中心，占地面积约72万平方米，建筑面积约15万平方米，有大小宫殿七十多座，房屋九千余间。",
            "metadata": {"name": "故宫博物院", "location": "北京", "type": "历史古迹"}
        },
        {
            "id": "scenic_spot_2",
            "content": "兵马俑，即秦始皇兵马俑，位于陕西省西安市临潼区，是秦始皇陵的陪葬坑。兵马俑被誉为世界第八大奇迹，是中国古代辉煌文明的一张金字名片。",
            "metadata": {"name": "兵马俑", "location": "西安", "type": "历史古迹"}
        }
    ]

    # 向量入库
    vector_store.add_documents(sample_docs)

    # 测试检索
    query = "北京有什么历史古迹？"
    results = vector_store.search(query, top_k=2)
    print("\n检索结果：")
    for i, res in enumerate(results):
        print(f"Rank {i + 1} | Score: {res['score']:.4f}")
        print(f"Content: {res['content']}")
        print(f"Metadata: {res['metadata']}\n")