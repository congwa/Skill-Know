"""会话和消息相关 schemas"""

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.conversation import MessageRole


class MessageCreate(BaseModel):
    """创建消息"""

    role: MessageRole
    content: str = Field(..., min_length=1)
    extra_metadata: dict = Field(default_factory=dict)


class MessageResponse(BaseModel):
    """消息响应"""

    id: str
    conversation_id: str
    role: MessageRole
    content: str
    tool_calls: list | None
    latency_ms: int | None
    extra_metadata: dict = Field(default_factory=dict)
    created_at: datetime

    model_config = {"from_attributes": True}


class ConversationCreate(BaseModel):
    """创建会话"""

    title: str | None = None
    extra_metadata: dict = Field(default_factory=dict)


class ConversationResponse(BaseModel):
    """会话响应"""

    id: str
    title: str | None
    extra_metadata: dict = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
    messages: list[MessageResponse] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class ConversationListResponse(BaseModel):
    """会话列表响应"""

    items: list[ConversationResponse]
    total: int
    page: int
    page_size: int
