from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

class TourGraphState(BaseModel):
    # 输入
    user_query: str = ""
    tenant_id: str = ""
    tenant_name: str = ""

    # 多轮状态
    conversation_id: str = ""
    history: List[Dict] = Field(default_factory=list)

    # 推理中间结果
    intent: str = ""          # weather / scenic / time / qa
    city: str = ""            # 自动抽取
    scenic_name: str = ""     # 自动抽取
    need_ask: bool = False    # 是否需要反问用户
    ask_message: str = ""     # 反问内容

    # 工具结果
    weather_info: str = ""
    scenic_info: str = ""
    time_info: str = ""

    # 最终输出
    answer: str = ""
    error: Optional[str] = None