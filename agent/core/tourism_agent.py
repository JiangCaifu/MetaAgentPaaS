import asyncio
from langchain.agents import create_react_agent, AgentExecutor
from langchain_core.prompts import PromptTemplate
from langchain_core.tools import Tool
from langchain.agents import create_tool_calling_agent
from agent.tools.weather_tool import WeatherTool
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import Tool
# 导入项目现有LLM客户端（复用百炼大模型，无需重新实现）
from llm.client import qwen_client
# 导入自定义工具
from agent.tools.weather_tool import query_weather
from agent.tools.scenic_tool import query_scenic_open_time
# 复用项目日志配置
from utils.logger_config import setup_logger

logger = setup_logger(name="TourismAgent")


# 1. 适配qwen_client为LangChain兼容的LLM类
class QwenLangChainLLM:
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id

    def __call__(self, prompt: str) -> str:
        """同步调用（适配LangChain Agent默认同步逻辑）"""
        try:
            # 修复：避免手动创建新循环，转发给异步方法，兼容 FastAPI 已有循环
            # 非 FastAPI 环境（单独测试）用 asyncio.run，FastAPI 环境用 await（由外部异步调用）
            return asyncio.run(self.call_async(prompt))
        except RuntimeError as e:
            if "another loop is running" in str(e):
                logger.warning("已有活跃事件循环，建议使用异步方法 call_async 调用")
                return "请使用异步方法调用该 LLM（FastAPI 环境）"
            else:
                logger.error(f"LLM 调用失败：{str(e)}")
                return f"LLM 调用失败：{str(e)}"

    async def call_async(self, input: dict) -> dict:
        """异步调用（适配项目FastAPI异步架构）"""
        try:
            # 关键修复：直接 await 调用 qwen_client.generate()，利用 FastAPI 全局循环
            response = await qwen_client.generate(prompt, self.tenant_id)
            return response
        except Exception as e:
            logger.error(f"LLM 异步调用失败：{str(e)}")
            return f"LLM 调用失败：{str(e)}"


# 2. 定义Agent Prompt（引导Agent正确调用工具，约束输出格式）
TOURISM_AGENT_PROMPT = PromptTemplate(
    input_variables=["tenant_name", "input", "agent_scratchpad", "tools"],
    template="""你是{tenant_name}的专属文旅问答Agent，负责解答用户的文旅相关问题。
可用工具：
{tools}

工具调用规则：
1. 若问题需要天气信息（如"北京明天天气怎么样"），调用query_weather工具，参数为城市名称；
2. 若问题需要景点开放时间（如"故宫几点开门"），调用query_scenic_open_time工具，参数为景点名称；
3. 若不需要工具即可回答（如"故宫是什么"），直接生成回答，无需调用工具；
4. 工具调用格式必须严格遵循：Action: 工具名\nAction Input: 参数\nObservation: 工具返回结果\n
5. 思考过程请记录在agent_scratchpad中，最终回答需简洁、准确，仅返回给用户的内容，不要包含思考过程。

用户问题：{input}
思考过程：{agent_scratchpad}
最终回答："""
)


# 3. 初始化文旅Agent
def create_tourism_agent(tenant_id: str, tenant_name: str) -> AgentExecutor:
    """
    创建文旅问答Agent（带工具调用能力）
    参数：tenant_id - 租户ID，tenant_name - 租户名称
    返回：LangChain AgentExecutor实例
    """
    # 注册工具（将自定义工具包装为LangChain Tool）
    tools = [
        Tool(
            name=query_weather.name,
            func=query_weather,
            description=query_weather.description
        ),
        Tool(
            name=query_scenic_open_time.name,
            func=query_scenic_open_time,
            description=query_scenic_open_time.description
        )
    ]
    # ====================== 新增：格式化工具变量（关键修复） ======================
    # 1. 格式化 tools 字符串（匹配你模板中的 {tools} 占位符，易读格式）
    formatted_tools = []
    for tool in tools:
        tool_info = f"工具名：{tool.name}\n   描述：{tool.description}"
        formatted_tools.append(tool_info)
    # 拼接成最终字符串，对应模板中的 {tools}
    tools_str = "\n\n".join(formatted_tools)

    # 2. 提取 tool_names 字符串（满足LangChain ReAct框架隐含要求，逗号分隔）
    tool_names_str = ", ".join([tool.name for tool in tools])
    # 适配租户信息到Prompt
    prompt = TOURISM_AGENT_PROMPT.partial(tenant_name=tenant_name,
        tools=tools_str,  # 填充模板中的 {tools}
        tool_names=tool_names_str  # 处理框架隐含的 {tool_names} 要求##
     )

    # 创建Agent（ReAct模式）
    llm = QwenLangChainLLM(tenant_id=tenant_id)
    agent = create_react_agent(llm=llm, tools=tools, prompt=prompt)

    # 创建Agent执行器（负责运行Agent循环）
    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,  # 调试模式，打印思考-行动-观察过程（便于排查工具调用问题）
        handle_parsing_errors="无法解析工具调用，请重新尝试并继续",  # 解析错误兜底
        max_iterations=5  # 限制最大迭代次数，避免无限循环
    )
    return agent_executor


# 4. 封装Agent调用函数（适配项目现有异步架构）
async def call_tourism_agent(tenant_id: str, tenant_name: str, user_query: str) -> str:
    """异步调用文旅Agent，返回最终回答"""
    try:
        # 验证输入参数，避免空值报错
        if not user_query:
            return "用户查询内容不能为空"
        agent_executor = create_tourism_agent(tenant_id, tenant_name)
        # 异步运行Agent（若Agent是同步的，用asyncio.to_thread包装）
        result = await asyncio.to_thread(
            agent_executor.invoke,
            {"input": user_query}
        )
        return result.get("output", "Agent未返回有效结果")
    except Exception as e:
        logger.error(f"文旅Agent调用失败：{str(e)}")
        return f"Agent调用失败：{str(e)}"
if __name__ == "__main__":
    # 1. 包装工具（两种方式都可）
    tools = [
        # 方式1：用装饰器的tool
        query_weather,
        # 方式2：用类式工具
        WeatherTool()
    ]

    # 2. 简单提示词（测试用，无需LLM）
    prompt = ChatPromptTemplate.from_messages([
        ("user", "{input}"),
        ("assistant", "{agent_scratchpad}")
    ])

    # 3. 模拟Agent调用（或用真实LLM，如OpenAI）
    # 这里简化测试：直接调用工具，验证参数传递
    print("\n=== LangChain工具调用测试 ===")
    # 直接调用工具（模拟Agent逻辑）
    tool_result = tools[0].invoke({"city": "深圳"})
    print(tool_result)