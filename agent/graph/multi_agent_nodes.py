from agent.graph.state import TourGraphState
from langgraph.graph import END
from llm.client import qwen_client
from agent.core.tourism_agent import create_tourism_agent, call_tourism_agent
from typing import Dict, Literal
import logging
from utils.logger_config import setup_logger
from agent.graph.kg_service import TourismKnowledgeGraph

# 懒加载知识图谱服务
_kg_service = None

def get_kg_service():
    """获取知识图谱服务实例（懒加载）"""
    global _kg_service
    if _kg_service is None:
        try:
            _kg_service = TourismKnowledgeGraph()
            logger.info("✅ 知识图谱服务初始化成功（NetworkX版）")
        except Exception as e:
            logger.warning(f"⚠️ 知识图谱服务初始化失败：{str(e)}")
            _kg_service = None
    return _kg_service

logger = setup_logger(name="MultiAgentNodes")


# ==============================
# Agent1：增强版意图理解Agent（复用原有意图识别逻辑，适配多Agent协作）
# ==============================
async def intent_agent(state: TourGraphState) -> Dict:
    """
    多Agent协作中的意图理解Agent
    功能：精准识别用户是否有景点推荐需求，为下游推荐Agent提供决策依据
    """
    # 复用原有意图识别逻辑，同时增强景点推荐意图判断
    history_context = ""
    if state.history:
        history_lines = []
        for msg in state.history:
            # ========== 新增：容错处理（核心修复） ==========
            # 1. 跳过空消息/格式错误的消息
            if not isinstance(msg, dict):
                continue
            # 2. 检查是否有role和content字段，没有则跳过
            if "role" not in msg or "content" not in msg:
                continue
            role = "用户" if msg["role"] == "user" else "助手"
            history_lines.append(f"{role}：{msg['content']}")
        history_context = "\n【历史对话】\n" + "\n".join(history_lines) + "\n"

    prompt = f"""
{history_context}
用户问题：{state.user_query}
请完成以下任务：
1. 基础意图分类（返回：weather / scenic / time / qa）
2. 景点推荐子意图判断：如果是scenic意图，进一步判断是否是「景点推荐」需求（是/否）
输出格式：
基础意图=xxx
推荐需求=xxx
"""
    try:
        # 调用现有LLM客户端
        result = await qwen_client.generate(prompt, state.tenant_id)
        result = result.strip()

        # 解析结果
        base_intent = ""
        need_recommend = False
        for line in result.splitlines():
            if "基础意图=" in line:
                base_intent = line.replace("基础意图=", "").strip()
            if "推荐需求=" in line:
                need_recommend = line.replace("推荐需求=", "").strip() == "是"

        # 更新状态（支持多Agent共享）
        return {
            "intent": base_intent,
            "need_ask": False,  # 重置反问状态
            "need_recommend": need_recommend  # 新增推荐需求标识（多Agent共享）
        }
    except Exception as e:
        logger.error(f"意图理解Agent执行失败：{str(e)}")
        return {
            "intent": "qa",
            "need_ask": False,
            "need_recommend": False,
            "error": f"意图理解Agent执行失败：{str(e)}"
        }


# ==============================
# Agent2：景点推荐Agent（复用原有Agent层能力，专注景点推荐）
# ==============================
async def recommendation_agent(state: TourGraphState) -> Dict:
    """
    多Agent协作中的景点推荐Agent
    功能：基于用户意图和实体信息，生成精准的景点推荐结果
    优先使用知识图谱结构化数据，无数据时降级为LLM推荐
    """
    try:
        # 1. 验证必要信息（城市不能为空）
        if not state.city:
            return {
                "need_ask": True,
                "ask_message": "请问你想查询哪个城市的景点推荐呢？",
                "scenic_info": "",
                "answer": ""
            }

        # 2. 优先从知识图谱查询结构化数据（核心逻辑）
        kg = get_kg_service()
        kg_spots = kg.get_city_scenic_spots(state.city) if kg else []

        # 3. 图谱有数据 → 融合结构化数据生成推荐
        if kg_spots:
            spot_lines = []
            for spot in kg_spots[:5]:  # 取前5个核心景点
                # 查询该景点的交通信息（容错处理）
                traffic = kg.get_scenic_traffic(spot["name"]) if kg else []
                traffic_str = ""
                if traffic:
                    traffic_str = " | 交通：" + "；".join(
                        [f"{t['type']}{t['line']} {t['station']}" for t in traffic]
                    )

                # 拼接单景点信息（结构化）
                spot_lines.append(
                    f"- {spot['name']}：{spot['desc']} | 开放时间：{spot['open_time']} | 票价：{spot['price']}{traffic_str}"
                )

            # 查询推荐联动景点（容错：避免索引越界）
            recommend_spots = kg.get_recommend_spots(spot_lines[0].split('：')[0][2:]) if (kg and spot_lines) else []
            tip_spot = recommend_spots[0]['name'] if recommend_spots else "同类型特色景点"

            # 生成最终推荐结果（去除多余缩进）
            scenic_info = f"""为你推荐{state.city}的核心景点（数据来自文旅知识图谱）：
{chr(10).join(spot_lines)}

小贴士：{spot_lines[0].split('：')[0][2:]}周边还推荐游玩{tip_spot}哦！"""

            return {
                "scenic_info": scenic_info,
                "answer": scenic_info,  # 同步到answer字段，确保响应返回
                "need_ask": False,
                "ask_message": ""
            }

        # 4. 图谱无数据 → 降级为原有LLM推荐逻辑
        else:
            recommend_query = f"为我推荐{state.city}的著名景点，要求简洁实用，列出3-5个核心景点并简要说明特色"
            agent_answer = await call_tourism_agent(
                tenant_id=state.tenant_id,
                tenant_name=state.tenant_name,
                user_query=recommend_query
            )
            return {
                "scenic_info": agent_answer,
                "answer": agent_answer,
                "need_ask": False,
                "ask_message": ""
            }

    except Exception as e:
        logger.error(f"景点推荐Agent执行失败：{str(e)}")
        return {
            "scenic_info": f"景点推荐失败：{str(e)}",
            "answer": f"景点推荐失败：{str(e)}",
            "error": f"景点推荐Agent执行失败：{str(e)}",
            "need_ask": False,
            "ask_message": ""
        }


# ==============================
# 多Agent流程分支路由（条件边实现）
# ==============================
def recommendation_router(state: TourGraphState) -> Literal["recommendation_agent", "original_flow", "ask_user", END]:
    """
    多Agent流程条件路由函数
    决定流程走向：景点推荐Agent / 原有流程 / 反问用户 / 结束
    """
    # 1. 需要反问用户 → 结束流程（等待用户补充信息）
    if state.need_ask:
        return "ask_user"

    # 2. 是景点推荐需求 → 走推荐Agent
    if state.intent == "scenic" and getattr(state, "need_recommend", False):
        return "recommendation_agent"

    # 3. 其他意图 → 走原有流程
    return "original_flow"