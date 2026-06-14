# vl_client.py
# ========================================
# Qwen-VL 多模态大模型客户端
# 功能：调用百炼Qwen-VL API，实现图文混合问答
# 支持：图片URL输入、Base64图片输入
# ========================================

import os
import base64
import logging
from typing import Optional, List, Dict
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("MetaAgentPaaS.multimodal")


class QwenVLClient:
    """Qwen-VL 多模态大模型客户端（百炼API）"""

    def __init__(self):
        self.api_key = os.getenv("DASHSCOPE_API_KEY", "")
        self.model = os.getenv("QWEN_VL_MODEL", "qwen-vl-plus")
        self.is_available = bool(self.api_key.strip())

        if not self.is_available:
            logger.warning("DASHSCOPE_API_KEY未配置，多模态功能将返回模拟数据")

    async def analyze_image(
        self,
        query: str,
        image_url: Optional[str] = None,
        image_base64: Optional[str] = None,
        tenant_id: str = "default",
    ) -> Dict:
        """
        调用Qwen-VL进行图文混合问答

        :param query: 用户问题
        :param image_url: 图片URL（与image_base64二选一）
        :param image_base64: 图片Base64编码（与image_url二选一）
        :param tenant_id: 租户ID
        :return: {"answer": str, "model": str, "usage": dict}
        """
        if not self.is_available:
            return self._mock_response(query, image_url is not None or image_base64 is not None)

        if not image_url and not image_base64:
            return {"answer": "请提供图片（URL或Base64）", "model": self.model, "usage": {}}

        try:
            import dashscope
            dashscope.api_key = self.api_key

            # 构建消息内容
            content = self._build_content(query, image_url, image_base64)

            response = dashscope.MultiModalConversation.call(
                model=self.model,
                messages=[{"role": "user", "content": content}],
            )

            if response.status_code != 200:
                error_msg = getattr(response, "message", "未知错误")
                logger.error(f"【租户{tenant_id}】Qwen-VL调用失败：{error_msg}")
                return {"answer": f"多模态模型调用失败：{error_msg}", "model": self.model, "usage": {}}

            # 解析响应
            output = getattr(response, "output", {})
            choices = output.get("choices", []) if isinstance(output, dict) else getattr(output, "choices", [])

            if choices:
                message = choices[0].get("message", {}) if isinstance(choices[0], dict) else getattr(choices[0], "message", {})
                answer = message.get("content", "") if isinstance(message, dict) else getattr(message, "content", "")
                if isinstance(answer, list):
                    # qwen-vl有时返回 [{"text": "..."}] 格式
                    answer = " ".join([item.get("text", "") if isinstance(item, dict) else str(item) for item in answer])
                if not answer:
                    answer = str(message) if message else "模型未返回有效内容"
            else:
                answer = "模型未返回有效内容"

            usage = output.get("usage", {}) if isinstance(output, dict) else {}

            logger.info(f"【租户{tenant_id}】Qwen-VL调用成功，回复长度：{len(str(answer))}")
            return {"answer": answer, "model": self.model, "usage": usage}

        except ImportError:
            logger.error("dashscope未安装，请运行：pip install dashscope")
            return {"answer": "dashscope未安装", "model": self.model, "usage": {}}
        except Exception as e:
            logger.error(f"【租户{tenant_id}】Qwen-VL调用异常：{str(e)}", exc_info=True)
            return {"answer": f"多模态模型调用异常：{str(e)}", "model": self.model, "usage": {}}

    def _build_content(
        self,
        query: str,
        image_url: Optional[str],
        image_base64: Optional[str],
    ) -> List[Dict]:
        """构建Qwen-VL消息内容（图文混合格式）"""
        content = []

        # 添加图片
        if image_url:
            content.append({"image": image_url})
        elif image_base64:
            # 补全Base64前缀（如果没有的话）
            if not image_base64.startswith("data:"):
                image_base64 = f"data:image/jpeg;base64,{image_base64}"
            content.append({"image": image_base64})

        # 添加文本问题
        content.append({"text": query})

        return content

    def _mock_response(self, query: str, has_image: bool) -> Dict:
        """模拟响应（未配置API密钥时使用）"""
        if has_image:
            mock_answer = (
                "【模拟回复】我识别到这是一张图片。\n"
                f"您的问题是：{query}\n\n"
                "图片分析结果（模拟）：\n"
                "- 图片类型：文物/景点照片\n"
                "- 主要内容：这是一件珍贵的文物展品\n"
                "- 建议了解更多：可前往当地博物馆参观\n\n"
                "⚠️ 此为模拟数据，配置DASHSCOPE_API_KEY后可获取真实分析结果"
            )
        else:
            mock_answer = "请提供图片以进行图文问答"

        return {
            "answer": mock_answer,
            "model": f"{self.model}(mock)",
            "usage": {"note": "模拟数据"},
        }

    @staticmethod
    def encode_image_to_base64(file_bytes: bytes) -> str:
        """将图片字节编码为Base64字符串"""
        return base64.b64encode(file_bytes).decode("utf-8")


# 全局实例
qwen_vl_client = QwenVLClient()
