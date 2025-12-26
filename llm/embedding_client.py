import logging

logging.basicConfig(
    level=logging.DEBUG,  # 开启DEBUG级别，打印详细响应
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("MetaAgentPaaS")


import requests
import json
import logging
from typing import List, Dict, Union
import os
from dotenv import load_dotenv

# 加载日志配置
#logger = logging.getLogger("MetaAgentPaaS")
# 加载环境变量
load_dotenv()


class BailianEmbeddingClient:
    """阿里云百炼Embedding API客户端（适配JSON文件输入）"""
    BAILIAN_EMBEDDING_URL = "https://dashscope.aliyuncs.com/api/v1/services/embeddings/text-embedding/text-embedding"
    BATCH_LIMIT = 10
    VALID_MODEL = "text-embedding-v4"
    def __init__(self):
        self.api_key = os.getenv("DASHSCOPE_API_KEY")
        if not self.api_key:
            raise ValueError("未配置百炼API Key！请在.env文件中添加BAILIAN_API_KEY=你的真实密钥")
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    # ========== 保留原有方法（兼容批量向量化） ==========
    def get_embedding(self, text: str) -> List[float]:
        """
        【原有方法】获取单段文本的Embedding向量
        :param text: 待向量化的纯文本字符串
        :return: 768维向量列表
        """
        if not text or text.strip() == "":
            logger.warning("待向量化文本为空，返回空向量")
            return []

        # ===== 新增：文本长度校验（避免超限）=====
        text_clean = [t.strip() for t in text if t.strip()]
        if len(text_clean) > 8192:
            logger.warning(f"文本长度超限（{len(text_clean)}字符），自动截断为8192字符")
            text_clean = text_clean[:8192]

        try:
            payload = {
                "model": "text-embedding-v4",  # 必须指定模型名称
                "input": {
                    "texts": text_clean
                }
            }
            response = requests.post(
                url=self.BAILIAN_EMBEDDING_URL,
                headers=self.headers,
                json=payload,
                timeout=30
            )

            # ===== 新增：打印完整响应（便于排查）=====
            logger.debug(f"接口响应状态码：{response.status_code}，响应内容：{response.text}")

            response.raise_for_status()
            result = response.json()
            if "output" in result and "embeddings" in result["output"]:

                vector =  [item["embedding"] for item in response.json().get("output", {}).get("embeddings", [])]
                logger.info(f"单文本向量化成功，文本长度：{len(text)}，向量维度：{len(vector)}")
                return vector
            else:
                logger.error(f"百炼API返回格式异常：{result}")
                return []
        except requests.exceptions.HTTPError as e:
            # 打印接口返回的详细错误信息（关键！）
            error_response = response.text if 'response' in locals() else "无响应内容"
            error_msg = f"百炼Embedding接口调用失败（HTTP错误）：{e}"
            if "401" in str(e):
                error_msg += " → 请检查BAILIAN_API_KEY是否正确！"
            elif "429" in str(e):
                error_msg += " → 请求频率超限，请稍后重试！"
            elif "400" in str(e):
                error_msg += "\n→ 原因：请求体格式错误/文本超限/模型名称错误！"
            logger.error(error_msg)
            raise
        except Exception as e:
            logger.error(f"单文本向量化失败：{str(e)}")
            raise

    # ========== 新增JSON文件处理方法（核心修改） ==========
    def get_embedding_from_json(self, json_file_path: str, text_field: str = "text") -> Union[
        List[float], List[Dict[str, List[float]]]]:
        """
        从JSON文件中提取文本并生成Embedding向量
        :param json_file_path: JSON文件的绝对/相对路径（如：./data/texts.json）
        :param text_field: JSON中存储文本的字段名（默认"text"，可根据你的JSON结构调整）
        :return: 若JSON是单文本对象→返回单个向量；若JSON是多文本列表→返回[{"text": "...", "vector": [...]}]
        """
        # 1. 校验文件是否存在
        if not os.path.exists(json_file_path):
            logger.error(f"JSON文件不存在：{json_file_path}")
            raise FileNotFoundError(f"无法找到文件：{json_file_path}")

        # 2. 读取并解析JSON文件
        try:
            with open(json_file_path, "r", encoding="utf-8") as f:
                json_data = json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"JSON文件格式错误（解析失败）：{json_file_path}，错误：{str(e)}")
            raise
        except Exception as e:
            logger.error(f"读取JSON文件失败：{json_file_path}，错误：{str(e)}")
            raise

        # 3. 处理JSON数据（兼容两种常见格式）
        # 格式1：单文本对象 → {"text": "故宫是皇家宫殿", "id": 1}
        # 提取有效文本
        all_texts = []
        if isinstance(json_data, dict) and text_field in json_data:
            text = str(json_data[text_field]).strip()
            if text:
                all_texts.append({"text": text, "index": 0})

        elif isinstance(json_data, list):
            for idx, item in enumerate(json_data):
                text = str(item.get(text_field, "")).strip()
                if text:
                    all_texts.append({"text": text, "index": idx})

        if not all_texts:
            raise ValueError("JSON文件中未提取到有效文本！")

        #拆分，10条/批
        batches = [all_texts[i:i + self.BATCH_LIMIT] for i in range(0, len(all_texts), self.BATCH_LIMIT)]
        batch_result = []
        # 4. 逐批调用接口
        for batch_idx, batch in enumerate(batches):
            batch_texts = [item["text"] for item in batch]
            payload = {
                "model": self.VALID_MODEL,
                "input": {"texts": batch_texts}  # 正确字段名：input.texts
            }

            try:
                # 发送请求
                response = requests.post(
                    url=self.BAILIAN_EMBEDDING_URL,
                    headers=self.headers,
                    json=payload,
                    timeout=30,
                    verify=False
                )
                logger.debug(f"第{batch_idx + 1}批响应：{response.status_code} - {response.text}")
                response.raise_for_status()

                # 解析向量
                result = response.json()
                embeddings = result.get("output", {}).get("embeddings", [])
                for idx, item in enumerate(batch):
                    if idx < len(embeddings):
                        batch_result.append({
                            "text": item["text"],
                            "vector": embeddings[idx]["embedding"],
                            "index": item["index"],
                            "error": ""
                        })
                    else:
                        batch_result.append({
                            "text": item["text"],
                            "vector": [],
                            "index": item["index"],
                            "error": "批次响应中无该文本向量"
                        })

            except Exception as e:
                error_msg = f"第{batch_idx + 1}批调用失败：{str(e)}"
                logger.error(error_msg)
                for item in batch:
                    batch_result.append({
                        "text": item["text"],
                        "vector": [],
                        "index": item["index"],
                        "error": error_msg
                    })

        # 按原始索引排序，保证结果顺序和JSON一致
        batch_result.sort(key=lambda x: x["index"])
        logger.info(f"JSON文件向量化完成：总条数={len(all_texts)}，成功条数={len([x for x in batch_result if x['vector']])}")
        return batch_result
