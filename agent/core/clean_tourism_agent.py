# clean_tourism_agent.py（完全干净，无旧残留）
import asyncio
from langchain.agents import create_react_agent, AgentExecutor
from langchain_core.prompts import PromptTemplate
from langchain_core.tools import Tool

# 仅导入必要的工具函数和 LLM 客户端（确保工具函数无旧依赖）
from agent.tools.weather_tool import query_weather
from agent.tools.scenic_tool import query_scenic_open_time
from llm.client import qwen_client

# 1. 定义干净的 PromptTemplate（无任何 tool_names 相关变量）
CLEAN_TOURISM_PROMPT = PromptTemplate(
    input_variables=["tenant_name", "input", "agent_scratchpad", "tools"],
    template="""你是{tenant_name}的专属文旅问答Agent，负责解答用户的文旅相关问题，严格按照以下规则执行：

可用工具列表：
{tools}

工具调用规则：
1.  仅当需要获取实时天气或景点开放时间时，才调用对应工具；
2.  调用天气工具（query_weather）时，参数仅传入城市名称（如"北京"，无需多余内容）；
3.  调用景点开放时间工具（query_scenic_open_time）时，参数仅传入景点完整名称（如"故宫博物院"）；
4.  若不需要工具即可直接回答用户问题，无需调用任何工具，直接返回简洁、准确的回答；
5.  工具调用后的思考过程记录在 agent_scratchpad 中，最终回答仅返回用户需要的内容，不包含思考、工具调用过程。

用户当前问题：{input}

思考过程：{agent_scratchpad}

最终回答："""
)

# 2. 适配 qwen_client 为 LangChain 兼容 LLM（干净版本，无额外逻辑）
class CleanQwenLangChainLLM:
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id

    def __call__(self, prompt: str) -> str:
        """同步调用，无任何额外校验，直接调用 qwen_client"""
        """同步调用：内部转发给异步方法，避免嵌套循环"""
        try:
            import asyncio
            # 关键：用 asyncio.run() 仅在无活跃循环时使用（非 FastAPI 环境）
            # FastAPI 环境下，优先使用异步方法 call_async
            return asyncio.run(self.call_async(prompt))
        except RuntimeError:
            # 已有活跃循环（FastAPI），直接返回异步方法结果（需配合外部异步调用）
            return "请使用异步方法 call_async 调用（FastAPI 环境）"

    async def call_async(self, prompt: str) -> str:
        """异步调用：直接调用 qwen_client.generate()，利用 FastAPI 全局循环"""
        try:
            import inspect
            from llm.client import qwen_client

            print("===== 验证 qwen_client.generate 是否被劫持 =====")
            print(f"方法地址：{qwen_client.generate}")
            print(f"方法源码片段：\n{inspect.getsource(qwen_client.generate)[:200]}...")

            # 关键：直接异步调用，无需手动创建循环（利用 FastAPI 已有全局循环）
            response = await qwen_client.generate(prompt, self.tenant_id)
            return response
        except Exception as e:
            return f"LLM 调用失败：{str(e)}"
# 3. 创建干净的 ReAct Agent（无旧依赖）
def create_clean_tourism_agent(tenant_id: str, tenant_name: str) -> AgentExecutor:
    """

    :param tenant_id:
    :param tenant_name:
    :return:
    # 显式注册工具
    tools = [
        Tool(
            name="query_weather",
            func=query_weather,
            description="用于查询指定城市的实时天气信息，参数仅传入城市名称（如北京、上海）"
        ),
        Tool(
            name="query_scenic_open_time",
            func=query_scenic_open_time,
            description="用于查询指定景点的开放时间和门票价格，参数仅传入景点完整名称（如故宫博物院）"
        )
    ]

    # 填充租户名称，无其他额外处理
    prompt = CLEAN_TOURISM_PROMPT.partial(tenant_name=tenant_name)

    # 创建 Agent
    llm = CleanQwenLangChainLLM(tenant_id=tenant_id)
    agent = create_react_agent(llm=llm, tools=tools, prompt=prompt)

    # 创建 Agent 执行器
    return AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        handle_parsing_errors="无法解析工具调用格式，请直接回答用户问题",
        max_iterations=5
    )
    """


    """极简空函数，无任何依赖，无任何逻辑"""
    print("===== 空函数扩展：第一步，手动拼接 Prompt =====")
    prompt_template = """你是{tenant_name}的专属文旅问答Agent，直接回答用户问题，无需调用任何工具。
    用户当前问题：{{input}}
    思考过程：{{agent_scratchpad}}
    最终回答："""
    filled_prompt = prompt_template.format(tenant_name=tenant_name)

    print("===== 空函数扩展：第二步，创建 LLM 实例 =====")
    llm = CleanQwenLangChainLLM(tenant_id=tenant_id)

    print("===== Prompt 拼接 + LLM 实例创建成功 =====")
    # 返回 Prompt 和 LLM 实例（供后续调用）
    return (filled_prompt, llm)


# 4. 干净的异步调用函数（无旧逻辑）
async def call_clean_tourism_agent(tenant_id: str, tenant_name: str, user_query: str) -> str:
    """

    :param tenant_id:
    :param tenant_name:
    :param user_query:
    :return:
        try:
        print("===== 步骤 1：进入 call_clean_tourism_agent 函数 =====")
        if not user_query:
            return "用户查询内容不能为空"

        print("===== 步骤 2：开始创建干净 Agent 执行器 =====")
        agent_executor = create_clean_tourism_agent(tenant_id, tenant_name)

        print("===== 步骤 3：Agent 执行器创建成功，准备调用 invoke() =====")
        print(f"Agent 执行器信息：{agent_executor}")
        result = await asyncio.to_thread(
            agent_executor.invoke,
            {"input": user_query}
        )
        print("===== 步骤 5：invoke() 调用成功，返回结果 =====")
        return result.get("output", "Agent 未返回有效结果")
    except Exception as e:
        print(f"===== 流程中断，异常信息：{str(e)} =====")
        return f"干净 Agent 调用失败：{str(e)}"
    """
    try:
        print("===== 步骤 1：进入 call_clean_tourism_agent 函数 ======")
        if not user_query:
            return "用户查询内容不能为空"

        print("===== 步骤 2：开始创建干净 Agent 执行器 ======")
        filled_prompt, llm = create_clean_tourism_agent(tenant_id, tenant_name)

        print("===== 步骤 3：拼接完整查询 Prompt（填充用户问题）======")
        # 手动填充用户问题（替代 Agent 的 input 变量）
        final_prompt = filled_prompt.replace("{{input}}", user_query).replace("{{agent_scratchpad}}", "无需复杂思考，直接回答。")

        print("===== 步骤 4：调用 LLM 异步方法，获取回答 ======")
        # 关键：调用异步方法 call_async，直接 await，无循环嵌套
        llm_result = await llm.call_async(final_prompt)

        print("===== 步骤 5：LLM 调用成功，返回结果 ======")
        return f"LLM 回答结果：\n{llm_result}"
    except Exception as e:
        print(f"===== 流程中断，异常信息：{str(e)} ======")
        return f"干净 Agent 调用失败：{str(e)}"