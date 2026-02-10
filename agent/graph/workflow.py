from langgraph.graph import StateGraph, END
from agent.graph.state import TourGraphState
from agent.graph.nodes import *

def build_tour_graph():
    w = StateGraph(TourGraphState)

    # 节点
    w.add_node("intent", node_intent)
    w.add_node("extract", node_extract_entity)
    w.add_node("check", node_check_info)
    w.add_node("weather", node_weather)
    w.add_node("scenic", node_scenic)
    w.add_node("time", node_time)
    w.add_node("qa", node_qa)
    w.add_node("summary", node_summary)

    # 入口
    w.set_entry_point("intent")

    # 流程
    w.add_edge("intent", "extract")
    w.add_edge("extract", "check")

    # 路由：根据意图走不同工具
    def router(state: TourGraphState):
        if state.need_ask:
            return END
        if state.intent == "weather":
            return "weather"
        if state.intent == "scenic":
            return "scenic"
        if state.intent == "time":
            return "time"
        return "qa"

    w.add_conditional_edges("check", router, {
        "weather": "weather",
        "scenic": "scenic",
        "time": "time",
        "qa": "qa",
        END: END
    })

    # 工具执行完 → 汇总
    w.add_edge("weather", "summary")
    w.add_edge("scenic", "summary")
    w.add_edge("time", "summary")

    # 结束
    w.add_edge("qa", END)
    w.add_edge("summary", END)

    return w.compile()