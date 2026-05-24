# ========================================
# 第11周任务：日志配置模块
# 配置项目日志系统
# ========================================
import logging
import logging.handlers
import os
from datetime import datetime

def setup_logging(log_level: str = "INFO") -> logging.Logger:
    """
    配置项目日志系统
    :param log_level: 日志级别 (DEBUG, INFO, WARNING, ERROR)
    :return: 配置好的日志记录器
    """
    # 创建日志目录
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # 日志文件名（按日期分割）
    current_date = datetime.now().strftime("%Y-%m-%d")
    log_file = os.path.join(log_dir, f"agent_{current_date}.log")
    
    # 设置日志级别
    level = getattr(logging, log_level.upper(), logging.INFO)
    
    # 创建日志记录器
    logger = logging.getLogger("AgentLog")
    logger.setLevel(level)
    logger.propagate = False  # 防止重复输出
    
    # 清除已存在的处理器（避免重复配置）
    if logger.handlers:
        logger.handlers.clear()
    
    # 创建格式器
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(funcName)s:%(lineno)d - %(message)s"
    )
    
    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    
    # 文件处理器（按大小分割，保留最近5个文件）
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    
    # 添加处理器
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    logger.info("✅ 日志系统初始化成功")
    logger.info(f"📝 日志级别：{log_level}")
    logger.info(f"📂 日志文件：{log_file}")
    
    return logger

class AgentLogger:
    """
    Agent专用日志记录器
    提供结构化日志记录功能
    """
    
    def __init__(self, name: str = "Agent"):
        self.logger = logging.getLogger(f"AgentLog.{name}")
    
    def log_llm_call(self, prompt: str, response: str, duration: float = 0.0, tokens: int = 0):
        """
        记录LLM调用
        :param prompt: 输入提示
        :param response: 响应内容
        :param duration: 调用耗时（秒）
        :param tokens: 消耗token数
        """
        self.logger.info(
            f"[LLM_CALL] 耗时={duration:.2f}s | tokens={tokens} | prompt_len={len(prompt)} | response_len={len(response)}"
        )
    
    def log_retrieval(self, query: str, source: str, result_count: int, duration: float = 0.0):
        """
        记录检索操作
        :param query: 查询内容
        :param source: 检索来源（knowledge_graph/vector_db）
        :param result_count: 检索结果数量
        :param duration: 检索耗时（秒）
        """
        self.logger.info(
            f"[RETRIEVAL] 来源={source} | 查询='{query[:30]}...' | 结果数={result_count} | 耗时={duration:.2f}s"
        )
    
    def log_agent_step(self, agent_name: str, step: str, input_data: dict = None, output_data: dict = None):
        """
        记录Agent执行步骤
        :param agent_name: Agent名称
        :param step: 步骤名称
        :param input_data: 输入数据
        :param output_data: 输出数据
        """
        input_str = str(input_data)[:50] if input_data else "None"
        output_str = str(output_data)[:50] if output_data else "None"
        self.logger.info(
            f"[AGENT_STEP] Agent={agent_name} | 步骤={step} | 输入={input_str} | 输出={output_str}"
        )
    
    def log_evaluation(self, metric: str, value: float, threshold: float = None):
        """
        记录评估结果
        :param metric: 评估指标名称
        :param value: 指标值
        :param threshold: 阈值（可选）
        """
        if threshold:
            status = "✅" if value >= threshold else "⚠️"
            self.logger.info(f"[EVALUATION] {status} {metric}={value:.4f} (阈值={threshold})")
        else:
            self.logger.info(f"[EVALUATION] {metric}={value:.4f}")
    
    def log_error(self, error_type: str, message: str, stack_trace: str = None):
        """
        记录错误
        :param error_type: 错误类型
        :param message: 错误消息
        :param stack_trace: 堆栈跟踪（可选）
        """
        self.logger.error(f"[ERROR] 类型={error_type} | 消息={message}")
        if stack_trace:
            self.logger.error(f"[ERROR] 堆栈:\n{stack_trace}")
    
    def log_api_request(self, endpoint: str, method: str, status_code: int, duration: float):
        """
        记录API请求
        :param endpoint: 端点路径
        :param method: HTTP方法
        :param status_code: 状态码
        :param duration: 请求耗时（秒）
        """
        self.logger.info(
            f"[API_REQUEST] {method} {endpoint} | 状态={status_code} | 耗时={duration:.2f}s"
        )

# 全局日志记录器实例
agent_logger = AgentLogger()
```

</function></seed:tool_call>