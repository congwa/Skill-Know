"""会话和消息数据模型"""

import uuid
from enum import Enum as PyEnum

from sqlalchemy import Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class MessageRole(str, PyEnum):
    """消息角色"""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class Conversation(Base, TimestampMixin):
    """会话模型"""

    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    # 会话标题（可选，用于展示）
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # 元数据
    extra_metadata: Mapped[dict] = mapped_column(JSON, default=dict)

    # 关联消息
    messages: Mapped[list["Message"]] = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )

    def __repr__(self) -> str:
        return f"<Conversation {self.id[:8]}>"


class Message(Base, TimestampMixin):
    """消息模型"""

    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    # 所属会话
    conversation_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # 消息角色
    role: Mapped[MessageRole] = mapped_column(
        Enum(MessageRole),
        nullable=False,
    )

    # 消息内容（Markdown 格式）
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # 工具调用信息
    tool_calls: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # 响应延迟（毫秒）
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # 额外元数据
    extra_metadata: Mapped[dict] = mapped_column(JSON, default=dict)

    # 关联
    conversation: Mapped["Conversation"] = relationship(
        "Conversation",
        back_populates="messages",
    )

    def __repr__(self) -> str:
        return f"<Message {self.role.value} {self.id[:8]}>"
