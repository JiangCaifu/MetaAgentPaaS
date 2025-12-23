from dotenv import load_dotenv
import os
import logging

# 加载.env文件（优先项目根目录）
load_dotenv(dotenv_path=".env", override=True)
logger = logging.getLogger("MetaAgentPaaS.config")


class Settings:
    def __init__(self):
        # 百炼配置（兜底空字符串，避免None）
        self.DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "")
        self.DASHSCOPE_MODEL = os.getenv("DASHSCOPE_MODEL", "qwen-turbo")

        # 验证配置
        self.validate()

    # 验证密钥（仅警告，不终止服务）
    def validate(self):
        if not self.DASHSCOPE_API_KEY:
            if not self.DASHSCOPE_API_KEY.strip():
                logger.warning("⚠️ 未配置DASHSCOPE_API_KEY（.env文件中添加DASHSCOPE_API_KEY=你的密钥）")
            else:
                logger.info("✅ 百炼API密钥配置成功")


# 全局配置实例
settings = Settings()
settings.validate()