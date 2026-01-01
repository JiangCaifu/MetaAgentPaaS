import os
from dotenv import load_dotenv
from langchain_text_splitters import RecursiveCharacterTextSplitter
from typing import List, Dict, Any

# 加载环境变量（如果你的 Embedding API 需要密钥）
load_dotenv()


class TextChunkProcessor:
    def __init__(
            self,
            chunk_size: int = 500,  # 每个块的最大字符数
            chunk_overlap: int = 50,  # 块之间的重叠字符数（保证上下文连贯）
            separators: List[str] = None
    ):
        # 默认分隔符：优先按段落、句子分割，避免切断语义
        self.separators = separators or ["\n\n", "\n", "。", "！", "？", "；", "，", " "]
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=self.separators,
            length_function=len  # 按字符长度计算
        )

    def split_text(self, text: str) -> List[str]:
        """
        对单段文本进行分块
        :param text: 原始文本
        :return: 分块后的文本列表
        """
        return self.text_splitter.split_text(text)

    def split_documents(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        对多文档批量分块（适用于你爬取的文旅数据集）
        :param documents: 格式 [{"id": "...", "content": "...", "metadata": {...}}]
        :return: 分块后的文档列表，包含原metadata
        """
        chunked_docs = []
        for doc in documents:
            chunks = self.split_text(doc["content"])
            for i, chunk in enumerate(chunks):
                chunked_docs.append({
                    "id": f"{doc['id']}_chunk_{i}",
                    "content": chunk,
                    "metadata": doc.get("metadata", {})  # 保留原数据的元信息（如景点名称、来源）
                })
        return chunked_docs


# ---------------- 测试代码 ----------------
if __name__ == "__main__":
    # 模拟你爬取的文旅数据
    sample_docs = [
        {
            "id": "scenic_spot_1",
            "content": "故宫博物院，旧称紫禁城，位于北京中轴线的中心，是明清两代的皇家宫殿。故宫以三大殿为中心，占地面积约72万平方米，建筑面积约15万平方米，有大小宫殿七十多座，房屋九千余间。",
            "metadata": {"name": "故宫博物院", "location": "北京", "type": "历史古迹"}
        }
    ]

    # 初始化分块器
    processor = TextChunkProcessor(chunk_size=200, chunk_overlap=30)
    # 批量分块
    chunked = processor.split_documents(sample_docs)

    # 打印结果
    for doc in chunked:
        print(f"Chunk ID: {doc['id']}")
        print(f"Content: {doc['content']}")
        print(f"Metadata: {doc['metadata']}\n")