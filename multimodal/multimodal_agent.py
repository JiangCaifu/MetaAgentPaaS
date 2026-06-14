# multimodal_agent.py
# ========================================
# 多模态Agent工作流
# 功能：图文混合问答，结合知识图谱增强回答质量
# 流程：图片理解 → 知识图谱检索 → 增强回答生成
# ========================================

import logging
from typing import Dict, Optional
from multimodal.vl_client import qwen_vl_client

logger = logging.getLogger("MetaAgentPaaS.multimodal.agent")


class MultimodalAgent:
    """多模态问答Agent：图片理解 + 知识图谱增强"""

    # 文物/景点相关的提示词模板
    SYSTEM_PROMPT = (
        "你是一个专业的文旅知识助手，擅长分析文物和景点图片。\n"
        "请根据图片内容和用户问题，提供专业、准确的回答。\n"
        "回答要求：\n"
        "1. 描述图片中的主要内容（文物名称、特征、年代等）\n"
        "2. 补充相关的历史文化背景\n"
        "3. 如果是景点图片，提供参观建议（开放时间、票价等）\n"
        "4. 语言简洁专业，避免编造不确定的信息"
    )

    async def analyze_relic(
        self,
        query: str,
        image_url: Optional[str] = None,
        image_base64: Optional[str] = None,
        tenant_id: str = "default",
    ) -> Dict:
        """
        文物图片问答（核心流程）

        流程：
        1. 调用Qwen-VL理解图片内容
        2. 尝试从知识图谱检索补充信息
        3. 整合返回增强结果

        :param query: 用户问题
        :param image_url: 图片URL
        :param image_base64: 图片Base64
        :param tenant_id: 租户ID
        :return: 完整分析结果
        """
        # 1. 构建增强提示词
        enhanced_query = f"{self.SYSTEM_PROMPT}\n\n用户问题：{query}"

        # 2. 调用Qwen-VL进行图文理解
        vl_result = await qwen_vl_client.analyze_image(
            query=enhanced_query,
            image_url=image_url,
            image_base64=image_base64,
            tenant_id=tenant_id,
        )

        answer = vl_result.get("answer", "")

        # 3. 尝试从知识图谱检索补充信息
        kg_supplement = self._search_kg_supplement(answer)

        # 4. 组装结果
        result = {
            "query": query,
            "vl_answer": answer,
            "kg_supplement": kg_supplement,
            "final_answer": self._merge_answer(answer, kg_supplement),
            "model": vl_result.get("model", ""),
            "has_image": image_url is not None or image_base64 is not None,
        }

        logger.info(f"【租户{tenant_id}】多模态问答完成，回答长度：{len(result['final_answer'])}")
        return result

    def _search_kg_supplement(self, vl_answer: str) -> str:
        """从知识图谱检索补充信息"""
        try:
            from agent.graph.kg_service import TourismKnowledgeGraph
            kg = TourismKnowledgeGraph()

            # 从VL回答中提取可能的景点/文物关键词
            keywords = self._extract_keywords(vl_answer)

            supplements = []
            for keyword in keywords:
                # 尝试查景点信息
                spots = kg.get_city_scenic_spots(keyword)
                if spots:
                    for spot in spots[:2]:
                        supplements.append(
                            f"- {spot.get('name', keyword)}：{spot.get('desc', '')} | "
                            f"开放时间：{spot.get('open_time', '未知')} | "
                            f"票价：{spot.get('price', '未知')}"
                        )

                # 尝试查文物信息
                relics = kg.get_city_cultural_relics(keyword)
                if relics:
                    for relic in relics[:2]:
                        supplements.append(
                            f"- 文物：{relic.get('name', keyword)}（{relic.get('dynasty', '')}）"
                        )

            if supplements:
                return "\n知识图谱补充信息：\n" + "\n".join(supplements)
            return ""

        except Exception as e:
            logger.debug(f"知识图谱补充检索失败（不影响主流程）：{e}")
            return ""

    @staticmethod
    def _extract_keywords(text: str) -> list:
        """从文本中提取可能的景点/城市关键词"""
        # 简单关键词匹配（覆盖知识图谱中的主要实体）
        city_keywords = ["北京", "上海", "深圳", "广州", "西安", "南京", "杭州", "成都"]
        scenic_keywords = [
            "故宫", "颐和园", "八达岭长城", "天坛", "明十三陵",
            "外滩", "豫园", "东方明珠", "上海博物馆",
            "世界之窗", "东部华侨城", "欢乐谷",
            "白云山", "陈家祠", "广州塔",
        ]
        relic_keywords = ["兵马俑", "青铜器", "瓷器", "书画", "文物"]

        all_keywords = city_keywords + scenic_keywords + relic_keywords
        found = [kw for kw in all_keywords if kw in text]
        return found if found else []

    @staticmethod
    def _merge_answer(vl_answer: str, kg_supplement: str) -> str:
        """合并VL回答和知识图谱补充"""
        if not kg_supplement:
            return vl_answer
        return f"{vl_answer}\n\n{kg_supplement}"


# 全局实例
multimodal_agent = MultimodalAgent()
