"""会话压缩与归档

参考 OpenViking Session.commit() + SessionCompressor 模式：
1. 当消息数超过阈值时触发压缩
2. 用 LLM 生成对话摘要
3. 保留最近 N 条消息 + 摘要
4. 压缩后触发 KnowledgeExtractor 提取知识
"""

from datetime import datetime
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.services.conversation import ConversationService

logger = get_logger("session_compressor")

KEEP_RECENT_MESSAGES = 6


class SessionCompressor:
    """会话压缩器"""

    def __init__(self, session: AsyncSession, llm: Any = None):
        self._session = session
        self._llm = llm
        self._conversation_service = ConversationService(session)
        self._threshold = settings.SESSION_COMPRESS_THRESHOLD

    async def should_compress(self, conversation_id: str) -> bool:
        """检查是否需要压缩"""
        messages = await self._conversation_service.get_messages(conversation_id)
        return len(messages) >= self._threshold

    async def compress(self, conversation_id: str) -> str | None:
        """压缩会话：生成摘要，保留最近消息，触发知识提取。

        Returns:
            生成的摘要文本，如果不需要压缩则返回 None
        """
        messages = await self._conversation_service.get_messages(conversation_id)

        if len(messages) < self._threshold:
            return None

        # 将要归档的消息（除了最近 N 条）
        archive_messages = messages[:-KEEP_RECENT_MESSAGES]
        keep_messages = messages[-KEEP_RECENT_MESSAGES:]

        # 生成摘要
        summary = await self._generate_summary(archive_messages)

        # 获取或创建 conversation
        conversation = await self._conversation_service.get_conversation(conversation_id)
        if conversation:
            conversation.extra_metadata = conversation.extra_metadata or {}
            old_summary = conversation.extra_metadata.get("summary", "")
            if old_summary:
                summary = f"{old_summary}\n\n---\n\n{summary}"
            conversation.extra_metadata["summary"] = summary
            conversation.extra_metadata["compressed_at"] = datetime.now().isoformat()
            conversation.extra_metadata["archived_count"] = len(archive_messages)
            stats = conversation.extra_metadata.get("stats", {})
            stats["compression_count"] = stats.get("compression_count", 0) + 1
            conversation.extra_metadata["stats"] = stats

        # 标记消息为已归档（保留数据，不再参与常规查询）
        for msg in archive_messages:
            msg.is_archived = True
        await self._session.flush()

        logger.info(
            "会话压缩完成",
            conversation_id=conversation_id,
            archived=len(archive_messages),
            kept=len(keep_messages),
            summary_length=len(summary),
        )

        # 异步触发知识提取
        self._trigger_knowledge_extraction(
            conversation_id=conversation_id,
            messages=archive_messages,
        )

        return summary

    async def get_compressed_context(self, conversation_id: str) -> str:
        """获取压缩后的上下文（摘要 + 最近消息）。

        适合用于构建 system prompt 或传递给 Agent。
        """
        conversation = await self._conversation_service.get_conversation(conversation_id)
        summary = ""
        if conversation and conversation.extra_metadata:
            summary = conversation.extra_metadata.get("summary", "")

        messages = await self._conversation_service.get_messages(conversation_id)
        recent = (
            messages[-KEEP_RECENT_MESSAGES:]
            if len(messages) > KEEP_RECENT_MESSAGES
            else messages
        )

        parts = []
        if summary:
            parts.append(f"## 对话摘要\n{summary}")

        if recent:
            lines = []
            for m in recent:
                role = "用户" if m.role.value == "user" else "AI"
                lines.append(f"[{role}]: {m.content}")
            parts.append("## 近期消息\n" + "\n".join(lines))

        return "\n\n".join(parts)

    async def _generate_summary(self, messages: list) -> str:
        """用 LLM 生成对话摘要"""
        if not self._llm:
            return self._fallback_summary(messages)

        try:
            from app.prompts import render_prompt

            lines = []
            for m in messages:
                role = "用户" if m.role.value == "user" else "AI"
                lines.append(f"[{role}]: {m.content}")
            conversation_text = "\n".join(lines)

            prompt = render_prompt("compression.session_summary", {"messages": conversation_text})
            if not prompt:
                prompt = f"请对以下对话生成简洁摘要（不超过 200 字）：\n\n{conversation_text}"

            response = await self._llm.ainvoke([
                SystemMessage(content="你是对话摘要专家。"),
                HumanMessage(content=prompt),
            ])
            return str(response.content).strip()
        except Exception as e:
            logger.warning(f"LLM 摘要生成失败: {e}")
            return self._fallback_summary(messages)

    @staticmethod
    def _fallback_summary(messages: list) -> str:
        """降级摘要：提取关键消息"""
        user_msgs = [m for m in messages if m.role.value == "user"]
        if not user_msgs:
            return "（无用户消息）"

        topics = []
        for m in user_msgs[:5]:
            content = m.content[:100].replace("\n", " ")
            topics.append(f"- {content}")

        return "用户讨论了以下话题：\n" + "\n".join(topics)

    def _trigger_knowledge_extraction(
        self, conversation_id: str, messages: list
    ) -> None:
        """异步触发知识提取（不阻塞压缩流程）"""
        try:
            import asyncio

            from app.services.knowledge_extractor import extract_and_store_knowledge

            formatted = [
                {"role": m.role.value, "content": m.content}
                for m in messages
                if m.content
            ]
            if len(formatted) >= 2:
                asyncio.create_task(
                    extract_and_store_knowledge(
                        conversation_id=conversation_id,
                        messages=formatted,
                    )
                )
        except Exception as e:
            logger.warning(f"触发知识提取失败（非阻塞）: {e}")
