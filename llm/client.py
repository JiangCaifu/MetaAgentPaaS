from dashscope import Generation
from dashscope.api_entities.dashscope_response import GenerationResponse
from config import settings
import logging

logger = logging.getLogger("MetaAgentPaaS.llm")


class QwenClient:
    """通义千问（百炼）大模型客户端（修复None值访问错误）"""

    def __init__(self):
        # 兜底：API密钥为空时，初始化空客户端
        self.api_key = settings.DASHSCOPE_API_KEY or ""
        self.model = settings.DASHSCOPE_MODEL or "qwen-turbo"
        # 标记是否可用
        self.is_available = bool(self.api_key.strip())

    async def generate(self, prompt: str, tenant_id: str) -> str:
        """
        调用百炼大模型生成回复（全链路None值校验）
        :param prompt: 提示词
        :param tenant_id: 租户ID
        :return: 大模型回复/错误提示
        """
        # 1. 兜底：无API密钥，返回模拟回复
        if not self.is_available:
            logger.warning(f"【租户{tenant_id}】百炼API密钥未配置，返回模拟回复")
            return f"""【{tenant_id}文旅推荐】北京5A景区推荐：
1. 故宫（60元）：世界文化遗产，明清皇宫；
2. 颐和园（30元）：皇家园林，昆明湖+万寿山；
3. 八达岭长城（40元）：万里长城精华段。"""

        try:
            # 2. 调用百炼大模型（增加超时/参数校验）
            response: GenerationResponse = Generation.call(
                model=self.model,
                api_key=self.api_key,
                messages=[{"role": "user", "content": prompt}],
                result_format="text",
                timeout=10  # 新增：超时时间，避免卡死
            )
            logger.info(f"【租户{tenant_id}】百炼大模型完整响应：{response}")

            # 3. 校验response是否为None
            if response is None:
                logger.error(f"【租户{tenant_id}】百炼大模型返回空响应（密钥/网络问题）")
                return "大模型调用失败：未获取到响应（请检查API密钥/网络）"

            # 4. 校验响应状态码
            if response.status_code != 200:
                error_msg = response.message if hasattr(response, "message") else "未知错误"
                logger.error(f"【租户{tenant_id}】百炼大模型调用失败：{error_msg}（状态码：{response.status_code}）")
                return f"大模型调用失败：{error_msg}（状态码：{response.status_code}）"

            # 5. 逐层校验响应结构（避免None下标访问）
            output = getattr(response, "output", {})
            if isinstance(output, dict):
                # 直接读取text字段（百炼返回的真实结果）
                text_result = output.get("text", "") or getattr(response, "text", "")
            else:
                text_result = getattr(output, "text", "") or getattr(response, "text", "")

            # 若text有值，直接返回（优先适配当前格式）
            text_result = text_result.strip()
            if text_result:
                logger.info(f"【租户{tenant_id}】百炼大模型调用成功（text格式），回复长度：{len(text_result)}")
                return text_result
            choices = getattr(output, "choices", None)
            if isinstance(choices, list) and len(choices) > 0:
                first_choice = choices[0]
                message = getattr(first_choice, "message", None)
                if message:
                    content = getattr(message, "content", "").strip()
                    if content:
                        logger.info(f"【租户{tenant_id}】百炼大模型调用成功（choices格式）")
                        return content

            # 最终兜底
            logger.error(f"【租户{tenant_id}】百炼大模型无有效结果：{response}")
            return "大模型调用成功，但未返回有效内容"

        except Exception as e:
            logger.error(f"【租户{tenant_id}】百炼大模型调用异常：{str(e)}", exc_info=True)
            return f"大模型调用异常：{str(e)}（请检查API密钥/模型名称/账号余额）"


# 全局实例（确保不会为None）
qwen_client = QwenClient()