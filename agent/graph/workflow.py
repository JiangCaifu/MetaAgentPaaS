from langgraph.graph import StateGraph, END
from agent.graph.state import TourGraphState
from agent.graph.nodes import *
# 导入新增的多Agent节点
from agent.graph.multi_agent_nodes import intent_agent, recommendation_agent, recommendation_router

def build_tour_graph():
    w = StateGraph(TourGraphState)

    # 节点
    w.add_node("detect_intent", node_intent)
    w.add_node("extract", node_extract_entity)
    w.add_node("check", node_check_info)
    w.add_node("weather", node_weather)
    w.add_node("scenic", node_scenic)
    w.add_node("time", node_time)
    w.add_node("qa", node_qa)
    w.add_node("summary", node_summary)

    # ==============================
    # 2. 新增多Agent协作节点
    # ==============================
    w.add_node("intent_agent", intent_agent)  # 增强版意图理解Agent
    w.add_node("recommendation_agent", recommendation_agent)  # 景点推荐Agent
    w.add_node("ask_user", lambda s: {"answer": s["ask_message"]})  # 反问用户节点

    # ==============================
    # 3. 流程重构（多Agent协作流程）
    # ==============================
    # 入口：改为多Agent意图理解节点
    w.set_entry_point("intent_agent")

    # 意图理解 → 实体抽取（状态共享）
    w.add_edge("intent_agent", "extract")

    # 实体抽取 → 信息检查
    w.add_edge("extract", "check")

    # 核心：条件边（多Agent流程分支）
    w.add_conditional_edges(
        "check",
        recommendation_router,  # 路由函数（条件判断）
        {
            "recommendation_agent": "recommendation_agent",  # 走推荐Agent
            "original_flow": "original_router",  # 走原有流程
            "ask_user": "ask_user",  # 反问用户
            END: END
        }
    )
    # ==============================
    # 4. 多Agent分支流程
    # ==============================
    # 推荐Agent → 汇总回答
    w.add_edge("recommendation_agent", "summary")
    # 反问用户 → 结束
    w.add_edge("ask_user", END)

    # ==============================
    # 5. 原有流程分支（封装为子路由）

    # 路由：根据意图走不同工具
    def original_router(state: TourGraphState):
        if state.need_ask:
            return END
        if state.intent == "weather":
            return "weather"
        if state.intent == "scenic":
            return "scenic"
        if state.intent == "time":
            return "time"
        return "qa"
    # ========== 仅新增这1行：注册original_router节点（核心修复） ==========
    w.add_node("original_router", original_router)

    w.add_conditional_edges("original_router", original_router, {
        "weather": "weather",
        "scenic": "scenic",
        "time": "time",
        "qa": "qa",
        #END: END
    })

    # 工具执行完 → 汇总
    w.add_edge("weather", "summary")
    w.add_edge("scenic", "summary")
    w.add_edge("time", "summary")

    # 结束
    w.add_edge("qa", END)
    w.add_edge("summary", END)

    return w.compile()