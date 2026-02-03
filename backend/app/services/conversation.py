"""会话服务"""

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging import get_logger
from app.models.conversation import Conversation, Message, MessageRole
from app.schemas.conversation import ConversationCreate, MessageCreate

logger = get_logger("conversation_service")


class ConversationService:
    """会话服务"""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def create_conversation(
        self, data: ConversationCreate | None = None
    ) -> Conversation:
        """创建会话"""
        conversation = Conversation(
            title=data.title if data else None,
            metadata=data.metadata if data else {},
        )
        self._session.add(conversation)
        await self._session.flush()
        logger.info("创建会话", conversation_id=conversation.id)
        return conversation

    async def get_conversation(self, conversation_id: str) -> Conversation | None:
        """获取会话"""
        stmt = (
            select(Conversation)
            .where(Conversation.id == conversation_id)
            .options(selectinload(Conversation.messages))
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def delete_conversation(self, conversation_id: str) -> bool:
        """删除会话"""
        conversation = await self.get_conversation(conversation_id)
        if not conversation:
            return False

        await self._session.delete(conversation)
        await self._session.flush()
        logger.info("删除会话", conversation_id=conversation_id)
        return True

    async def list_conversations(
        self, page: int = 1, page_size: int = 20
    ) -> tuple[list[Conversation], int]:
        """列出会话"""
        stmt = select(Conversation)

        # 计算总数
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self._session.execute(count_stmt)).scalar() or 0

        # 分页
        stmt = stmt.order_by(Conversation.updated_at.desc())
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)

        result = await self._session.execute(stmt)
        conversations = list(result.scalars().all())

        return conversations, total

    async def add_message(
        self,
        conversation_id: str,
        role: str | MessageRole,
        content: str,
        message_id: str | None = None,
        tool_calls: list | None = None,
        latency_ms: int | None = None,
        metadata: dict | None = None,
    ) -> Message:
        """添加消息"""
        if isinstance(role, str):
            role = MessageRole(role)

        message_data = {
            "conversation_id": conversation_id,
            "role": role,
            "content": content,
            "tool_calls": tool_calls,
            "latency_ms": latency_ms,
            "metadata": metadata or {},
        }
        if message_id:
            message_data["id"] = message_id

        message = Message(**message_data)
        self._session.add(message)
        await self._session.flush()
        return message

    async def get_messages(self, conversation_id: str) -> list[Message]:
        """获取会话消息"""
        stmt = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def update_conversation_title(
        self, conversation_id: str, title: str
    ) -> Conversation | None:
        """更新会话标题"""
        conversation = await self.get_conversation(conversation_id)
        if not conversation:
            return None

        conversation.title = title
        await self._session.flush()
        return conversation
