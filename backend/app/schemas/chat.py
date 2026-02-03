"""聊天相关 schemas"""

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """聊天请求"""

    message: str = Field(..., min_length=1, description="用户消息")
    conversation_id: str | None = Field(default=None, description="会话 ID，不传则创建新会话")


class ChatResponse(BaseModel):
    """聊天响应（非流式）"""

    conversation_id: str
    message_id: str
    content: str
    tool_calls: list | None = None
    latency_ms: int | None = None
