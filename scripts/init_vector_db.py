# ========================================
# 初始化向量数据库脚本
# 将tourism_doc.txt内容导入向量数据库
# ========================================
import sys
sys.path.insert(0, '.')

from db.qdrant_vector_store import QdrantVectorStore
import os

def load_tourism_docs(file_path: str) -> list:
    """加载文旅文档"""
    if not os.path.exists(file_path):
        print(f"❌ 文档文件不存在: {file_path}")
        return []
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 按章节分割文档
    sections = content.split('## ')
    documents = []
    
    for section in sections[1:]:  # 跳过第一个空元素
        lines = section.strip().split('\n')
        if not lines:
            continue
        
        title = lines[0].strip()
        content = '\n'.join(lines[1:]).strip()
        
        documents.append({
            "content": content,
            "metadata": {
                "name": title,
                "source": "tourism_doc.txt"
            }
        })
    
    return documents

def init_vector_db_with_docs():
    """初始化向量数据库并导入文档"""
    print("🚀 开始初始化向量数据库...")
    
    # 加载文档
    docs = load_tourism_docs("tourism_doc.txt")
    if not docs:
        print("❌ 没有加载到任何文档")
        return
    
    print(f"📄 加载了 {len(docs)} 个文档片段")
    
    # 初始化向量数据库（百炼Embedding返回768维向量）
    db = QdrantVectorStore(
        collection_name="test_collection",
        path="./local_qdrant_data",
        vector_dimension=768
    )
    
    # 清空现有数据（可选）
    # db.clear_collection()
    
    # 导入文档
    success_count = 0
    for i, doc in enumerate(docs):
        try:
            db.add_document(
                content=doc["content"],
                metadata=doc["metadata"]
            )
            success_count += 1
            print(f"✅ 导入文档 {i+1}/{len(docs)}: {doc['metadata']['name']}")
        except Exception as e:
            print(f"❌ 导入文档失败 {i+1}: {str(e)}")
    
    print(f"\n🎉 向量数据库初始化完成！成功导入 {success_count}/{len(docs)} 个文档")
    
    # 测试检索
    print("\n🔍 测试检索...")
    results = db.search("北京景点", top_k=3)
    print(f"检索到 {len(results)} 条结果")
    for res in results:
        print(f"  - {res.get('metadata', {}).get('name', '未知')} (相似度: {res.get('score', 0):.4f})")

if __name__ == "__main__":
    init_vector_db_with_docs()
