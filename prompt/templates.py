from langchain.prompts import PromptTemplate
from typing import Dict, List
from utils.logger_config import setup_logger
logger = setup_logger(name="MetaAgentPaaS", log_file="metaagentpaas.log")
# 适配你的Agent类型的Prompt模板
class AgentPromptTemplates:
    # 文旅推荐Agent模板（结构化输出）
    tourism_recommend_template = PromptTemplate(
        input_variables=["tenant_name", "query", "city"],
        template="""你是{tenant_name}的专属文旅推荐Agent，用户需求：{query}，目标城市：{city}
请严格按照JSON格式返回以下内容：
{{
  "recommendations": [
    {{
      "name": "景区名称",
      "ticket_price": "门票价格",
      "reason": "推荐理由"
    }}
  ]
}}
要求：
1. 推荐3-5个该城市的5A景区；
2. 仅返回JSON，不要任何多余文字；
3. 无相关信息时返回{{"recommendations": []}}。"""
    )

    # 文旅问答Agent模板（防幻觉）
    tourism_qa_template = PromptTemplate(
        input_variables=["tenant_name", "query"],
        template="""你是{tenant_name}的专属文旅问答Agent，用户问题：{query}
规则：
1. 只使用准确的公开信息回答；
2. 不确定或无相关信息时，回复"暂无相关信息"；
3. 语言简洁，不超过200字。"""
    )

    # 制造行业Agent模板
    factory_monitor_template = PromptTemplate(
        input_variables=["tenant_name", "query"],
        template="""你是{tenant_name}的专属工厂监控Agent，用户问题：{query}
请直接、简洁回答，仅回复核心数据，无多余话术。"""
    )

# 模板管理类
class PromptManager:
    def __init__(self):
        self.templates = AgentPromptTemplates()
        # 映射Agent ID到模板
        self.agent_template_map = {
            "tourism_recommend_agent": self.templates.tourism_recommend_template,
            "tourism_qa_agent": self.templates.tourism_qa_template,
            "factory_monitor_agent": self.templates.factory_monitor_template,
            "equipment_qa_agent": self.templates.tourism_qa_template  # 复用问答模板
        }

    def get_template(self, agent_id: str) -> PromptTemplate:
        """根据Agent ID获取对应的模板"""
        if agent_id not in self.agent_template_map:
            # 优化：添加日志，提示使用兜底模板
            logger.warning(f"未找到 {agent_id} 对应的模板，使用兜底模板")
        # 兜底模板 - 修复：input_variables 添加 tenant_name
            # 兜底模板
            return PromptTemplate(
                input_variables=["tenant_name","query"],
                template="你是{tenant_name}的专属Agent，用户问题：{query}，请直接回答。"
            )
        logger.info(f"成功获取 {agent_id} 对应的模板")  # 新增：打印成功日志
        return self.agent_template_map[agent_id]

    def render_prompt(self, agent_id: str, tenant_name: str, query: str, city: str = "北京") -> str:
        """渲染模板（适配不同Agent的参数）"""
        try:
            # 新增：打印模板获取前的日志
            logger.info(f"开始获取 {agent_id} 对应的模板")
            template = self.get_template(agent_id)
            logger.info(f"当前调用的模板：{template.__dict__}")  # 打印模板详情
            if agent_id == "tourism_recommend_agent":
                prompt_value = template.format_prompt(
                    tenant_name=tenant_name,
                    query=query,
                    city=city
                )
                result = prompt_value.to_string()
            else:
                # 优化：统一使用format_prompt方法
                prompt_value = template.format_prompt(
                    tenant_name=tenant_name,
                    query=query
                )
                result = prompt_value.to_string()
            # 新增：打印渲染后的Prompt
            logger.info(f"模板渲染成功，最终Prompt：{result}")
            return result
        except Exception as e:
            # 新增：捕获模板获取/渲染异常，打印详细信息
            logger.error(f"模板渲染失败（agent_id={agent_id}）：{str(e)}，异常类型：{type(e).__name__}")
            raise e  # 抛出异常，便于上层排查
