from agent.graph.state import TourGraphState
from llm.client import qwen_client
from agent.tools.weather_tool import query_weather
from agent.tools.scenic_tool import query_scenic_open_time
from typing import Dict

# ==============================
# 节点1：意图识别
# ==============================
async def node_intent(state: TourGraphState) -> Dict:
    # 构建历史对话上下文
    history_context = ""
    if state.history:
        history_lines = []
        for msg in state.history:
            role = "用户" if msg["role"] == "user" else "助手"
            history_lines.append(f"{role}：{msg['content']}")
        history_context = "\n【历史对话】\n" + "\n".join(history_lines) + "\n"
    prompt = f"""
{history_context}
用户问题：{state.user_query}
判断意图，只能返回一个：
weather / scenic / time / qa
"""
    intent = await qwen_client.generate(prompt, state.tenant_id)
    intent = intent.strip().lower()
    return {"intent": intent}

# ==============================
# 节点2：实体抽取（城市/景点）
# ==============================
async def node_extract_entity(state: TourGraphState) -> Dict:
    # 构建历史对话上下文
    history_context = ""
    if state.history:
        history_lines = []
        for msg in state.history:
            role = "用户" if msg["role"] == "user" else "助手"
            history_lines.append(f"{role}：{msg['content']}")
        history_context = "\n【历史对话】\n" + "\n".join(history_lines) + "\n"
    prompt = f"""
{history_context}
从用户问题抽取：
城市：直接写名字，没有填空
景点：直接写名字，没有填空
用户问题：{state.user_query}
格式：
城市=北京
景点=故宫
"""
    text = await qwen_client.generate(prompt, state.tenant_id)
    city = ""
    scenic = ""
    for line in text.splitlines():
        if "城市=" in line:
            city = line.replace("城市=", "").strip()
        if "景点=" in line:
            scenic = line.replace("景点=", "").strip()
    return {"city": city, "scenic_name": scenic}

# ==============================
# 节点3：判断是否需要反问
# ==============================
async def node_check_info(state: TourGraphState) -> Dict:
    need_ask = False
    msg = ""
    if state.intent in ["weather", "scenic"] and not state.city:
        need_ask = True
        msg = "请问你想查询哪个城市呢？"
    if state.intent == "time" and not state.scenic_name:
        need_ask = True
        msg = "请问你想查询哪个景点的开放时间？"
    return {"need_ask": need_ask, "ask_message": msg}

# ==============================
# 节点4：调用天气
# ==============================
async def node_weather(state: TourGraphState) -> Dict:
    res = query_weather(state.city or "北京")
    return {"weather_info": res}

# ==============================
# 节点5：调用景点推荐
# ==============================
async def node_scenic(state: TourGraphState) -> Dict:
    res = f"为你推荐{state.city}著名景点：故宫、天安门、颐和园、八达岭长城。"
    return {"scenic_info": res}

# ==============================
# 节点6：调用景点时间
# ==============================
async def node_time(state: TourGraphState) -> Dict:
    # 1. 先调用工具（数据库查询）
    full_scenic_name = f"{state.city}{state.scenic_name}" if (state.city and state.scenic_name) else state.scenic_name
    res = query_scenic_open_time.invoke({"scenic_name": full_scenic_name})

    # 2. 核心新增：工具查不到时，调用LLM生成结果
    if "未查询到" in res:
        # 构造LLM生成开放时间的prompt（通用模板，无硬编码）
        llm_prompt = f"""
    请回答{state.city}{state.scenic_name}的开放时间，要求：
    1. 准确、简洁；
    2. 不知道就说“暂未查询到{state.scenic_name}的开放时间信息”；
    3. 仅返回回答内容，无多余文字。
            """
        # 调用LLM生成结果
        res = await qwen_client.generate(llm_prompt, state.tenant_id)
        res = res.strip() or f"暂未查询到{state.scenic_name}的开放时间信息"

    return {"time_info": res}

# ==============================
# 节点7：普通问答
# ==============================
async def node_qa(state: TourGraphState) -> Dict:
    ans = await qwen_client.generate(state.user_query, state.tenant_id)
    return {"answer": ans}

# ==============================
# 节点8：最终汇总回答
# ==============================
async def node_summary(state: TourGraphState) -> Dict:
    parts = []
    if state.scenic_info:
        parts.append(state.scenic_info)
    if state.weather_info:
        parts.append(state.weather_info)
    if state.time_info:
        parts.append(state.time_info)
    if not parts:
        return {"answer": state.answer}
    answer = "\n".join(parts)
    return {"answer": answer}