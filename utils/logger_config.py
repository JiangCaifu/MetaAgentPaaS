import logging
import os
from logging.handlers import RotatingFileHandler


def setup_logger(name: str = "MetaAgentPaaS", log_file: str = "metaagentpaas.log", level: int = logging.INFO):
    """优化日志配置：按大小分割、编码utf-8、兼容原有输出"""
    # 移除原有handler（避免重复）
    logger = logging.getLogger(name)
    logger.handlers.clear()

    # 日志格式（兼容原有格式）
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # 文件handler（按大小分割，保留5个备份）
    file_handler = RotatingFileHandler(
        log_file, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)

    # 控制台handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # 配置logger
    logger.setLevel(level)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


# 全局logger实例（兼容原有代码的logger引用）
logger = setup_logger()