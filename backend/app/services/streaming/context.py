"""聊天上下文

定义 Agent 运行时需要的上下文信息。
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ChatContext:
    """聊天上下文

    Attributes:
        emitter: 事件发射器（用于发送流事件）
        conversation_id: 会话 ID
        user_id: 用户 ID
        session: 数据库会话（用于工具访问数据库）
        metadata: 额外的元数据
    """

    emitter: Any = None
    conversation_id: str = ""
    user_id: str = ""
    session: Any = None
    metadata: dict[str, Any] = field(default_factory=dict)
