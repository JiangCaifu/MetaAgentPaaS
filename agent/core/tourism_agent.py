import asyncio
from langchain.agents import create_react_agent, AgentExecutor
from langchain.agents.output_parsers import ReActSingleInputOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.tools import Tool
from langchain.agents import create_tool_calling_agent
from agent.tools.weather_tool import WeatherTool
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import Tool
# 导入项目现有LLM客户端（复用百炼大模型，无需重新实现）
from llm.client import qwen_client
from langchain_core.language_models import LLM
from typing import Optional, List, Any, Dict
from pydantic import Field
import asyncio
import logging
# 导入自定义工具
from agent.tools.weather_tool import query_weather
from agent.tools.scenic_tool import query_scenic_open_time
# 复用项目日志配置
from utils.logger_config import setup_logger

logger = setup_logger(name="TourismAgent")


# 1. 适配qwen_client为LangChain兼容的LLM类
class QwenLangChainLLM(LLM):
    """符合 LangChain 规范的 Qwen LLM 类（适配 ReAct Agent）"""
    # 定义类属性（用 Field 做注解，兼容 Pydantic 校验，保持和你的原有逻辑一致）
    tenant_id: str = Field(default="tenant_001", description="租户ID")

    # 【必备】实现 LangChain LLM 基类要求的 _llm_type 属性（返回 LLM 类型标识）
    @property
    def _llm_type(self) -> str:
        return "qwen-custom"  # 自定义标识，可任意命名，用于日志和溯源

    # 【必备】实现 LangChain LLM 基类要求的 _call 方法（同步调用核心逻辑，框架会自动调用）
    def _call(
            self,
            prompt: str,
            stop: Optional[List[str]] = None,
            run_manager: Optional[Any] = None,
            **kwargs
    ) -> str:
        """
        同步调用 Qwen 模型（LangChain 框架要求的核心方法）
        避免使用 asyncio.run()，改用直接调用异步方法的适配方案
        """
        try:
            # Bug修复：获取当前运行的事件循环，而非创建新循环
            loop = asyncio.get_running_loop()
            response = loop.run_until_complete(self.call_async(prompt))
            logger.info(f"【LLM调用成功】租户{self.tenant_id}，返回内容：{response[:50]}...")
            return response.strip() if response else "未获取到有效响应"
            # 【仅修复Bug】捕获"无运行事件循环"异常，回退到asyncio.run()
        except RuntimeError as e:
            if "no running event loop" in str(e):
                response = asyncio.run(self.call_async(prompt))
                logger.info(f"【LLM调用成功（兼容模式）】租户{self.tenant_id}，返回内容：{response[:50]}...")
                return response.strip() if response else "未获取到有效响应"
            else:
                raise  # 其他异常正常抛出，不兜底
        except Exception as e:
            # ===== 修复空错误信息：打印完整堆栈 =====
            import traceback
            error_stack = traceback.format_exc()
            error_msg = str(e) if str(e) else f"未知错误（类型：{type(e).__name__}）"
            logger.error(f"LLM 同步调用失败：{error_msg}\n完整堆栈：{error_stack}")
            return f"LLM 调用失败：{error_msg}"

    # 优化：修复异步调用方法（参数、返回值、变量名统一）
    async def call_async(self, prompt: str) -> str:
        """异步调用 Qwen 模型（保留原有逻辑，增加超时）"""
        try:
            # 给模型调用加超时（避免卡住）
            response = await asyncio.wait_for(
                qwen_client.generate(prompt, self.tenant_id),
                timeout=10  # 10秒超时
            )
            return str(response) if response else "未获取到有效响应"
        except asyncio.TimeoutError:
            logger.error(f"LLM 异步调用超时（10秒），租户{self.tenant_id}，prompt：{prompt[:30]}...")
            return "LLM 调用超时，请稍后重试"
        except Exception as e:
            logger.error(f"LLM 异步调用失败：{str(e)}")
            return f"LLM 调用失败：{str(e)}"



# 2. 定义Agent Prompt（引导Agent正确调用工具，约束输出格式）
TOURISM_AGENT_PROMPT = PromptTemplate(
    input_variables=["tenant_name", "input", "agent_scratchpad", "tools", "tool_names"],
    template="""你是{tenant_name}的专属文旅问答Agent，负责解答用户的文旅相关问题。
可用工具：
{tools}
可用工具名称列表：{tool_names}

工具调用规则：
1. 若问题需要天气信息（如"北京明天天气怎么样"），调用query_weather工具，参数为城市名称；
2. 若问题需要景点开放时间（如"故宫几点开门"），调用query_scenic_open_time工具，参数为景点名称；
3. 若不需要工具即可回答，或工具调用后无结果，**直接输出 Final Answer: 最终回答内容（无需任何Thought/Action格式）**；
4. 工具调用格式必须严格遵循（仅输出以下三行，无任何多余内容、换行或注释）：
Thought: 需要调用工具
Action: 工具名（必须从{tool_names}列表中选择）
Action Input: 参数（仅填字符串，无需引号）
5. 禁止输出假设性文本（如"假设工具返回结果为"）；最终回答需简洁、准确，仅返回给用户的内容。

用户问题：{input}
Thought: {agent_scratchpad}
Final Answer:"""  # 【最小修复】从「最终回答：」改为LangChain原生识别的Final Answer:
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

    def custom_error_handler(error: Exception,  **kwargs) -> str:
        """修复：识别纯自然语言回答场景，提取LLM有效输出"""
        error_msg = str(error)
        user_input_dict = kwargs.get("input", {})
        if not user_input_dict:
            user_input_dict = kwargs.get("run_context", {}).get("input", {})
        query = user_input_dict.get("input", "") if isinstance(user_input_dict, dict) else str(user_input_dict)

        # 场景1：混合输出错误（保留原有逻辑）
        if "both a final answer and a parse-able action" in error_msg:
            llm_output_start = error_msg.find("::") + 2
            if llm_output_start > 1:
                llm_raw_output = error_msg[llm_output_start:].strip()
                final_answer_start = llm_raw_output.find("Final Answer:")
                if final_answer_start != -1:
                    final_answer = llm_raw_output[final_answer_start + len("Final Answer:"):].strip()
                    if final_answer and "解析失败" not in final_answer:
                        return final_answer

        # 场景2：纯自然语言回答导致解析失败（新增核心修复）
        if "Could not parse LLM output" in error_msg:
            # 从错误信息中提取LLM的纯自然语言回答
            llm_output_start = error_msg.find("`") + 1
            llm_output_end = error_msg.rfind("`")
            if llm_output_start > 0 and llm_output_end > llm_output_start:
                llm_raw_answer = error_msg[llm_output_start:llm_output_end].strip()
                # 仅返回有效回答（排除空值/错误关键词）
                if llm_raw_answer and any(key in llm_raw_answer for key in ["开放时间", "门票", "免费", "全天"]):
                    return llm_raw_answer

        # 场景3：其他解析错误（通用逻辑）
        elif "开放时间" in query or "门票" in query or "景点" in query:
            return f"暂未查询到「{query}」的相关信息，建议确认景点名称后重试"
        elif "天气" in query or "温度" in query:
            return f"暂未查询到「{query}」的天气信息，建议确认城市名称后重试"

        # 通用兜底（仅当无有效回答时返回）
        return "暂无法解答你的问题，请稍后重试"

    # 创建Agent执行器（负责运行Agent循环）
    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,  # 调试模式，打印思考-行动-观察过程（便于排查工具调用问题）

        handle_parsing_errors=custom_error_handler,  # 仅返回错误提示，无固定内容
        max_iterations=3,  # 减少迭代次数，避免长时间卡住
        early_stopping_method="force",  # 全版本兼容
        return_intermediate_steps=False
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
        # Bug修复：改用异步ainvoke()替代同步invoke()，适配FastAPI异步环境
        result = await agent_executor.ainvoke({"input": user_query})
        # ========== 核心修复：优先提取所有有效回答（中间步骤 > final output） ==========
        # 1. 优先提取中间步骤中的LLM有效回答（最高优先级）
        final_answer = ""
        intermediate_steps = result.get("intermediate_steps", [])
        for step in intermediate_steps:
            # LangChain中间步骤格式：(action_object, observation_str)
            if len(step) >= 2 and isinstance(step[1], str):
                step_answer = step[1].strip()
                # 过滤错误关键词，只保留正常回答
                error_keywords = ["解析失败", "暂无法解答", "Agent stopped", "迭代上限", "参数缺失"]
                if step_answer and not any(key in step_answer for key in error_keywords):
                    final_answer = step_answer
                    break  # 找到第一个有效回答就停止，避免覆盖

        # 2. 若中间步骤无有效回答，提取final output（过滤迭代提示）
        if not final_answer:
            output = result.get("output", "").strip()
            # 彻底移除迭代上限提示文本
            iteration_prompt = "Agent stopped due to iteration limit or time limit."
            final_answer = output.replace(iteration_prompt, "").strip()
            # 兜底：若仍为空，使用原始output
            final_answer = final_answer or output

        # 3. 最终校验：确保返回非空的有效回答
        if not final_answer:
            final_answer = "暂未获取到有效信息，请稍后重试"

        return final_answer

    except Exception as e:
        error_msg = str(e) if str(e) else f"Agent调用失败（类型：{type(e).__name__}）"
        logger.error(f"文旅Agent调用失败：{error_msg}")
        return f"Agent调用异常：{error_msg}；"

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