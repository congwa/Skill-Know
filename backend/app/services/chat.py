"""聊天服务 - SDK v0.2.0 版本

使用 Orchestrator + AgentRunner + ContentAggregator 重构。
队列管理、内容聚合、错误处理均由 SDK 自动完成，
业务只需实现 AgentRunner 和 on_stream_end 钩子。
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from typing import Any

from langgraph_agent_kit import (
    Orchestrator,
    OrchestratorHooks,
    StreamEndInfo,
    StreamEvent,
)
from langgraph_agent_kit.core.context import ChatContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.chat_models import V1ChatModel
from app.core.logging import get_logger
from app.core.service import get_service
from app.schemas.events import StreamEventType
from app.services.agent.core import agent_service
from app.services.conversation import ConversationService
from app.services.prompt import PromptService
from app.services.retriever import SkillRetriever
from app.services.skill import SkillService
from app.services.system_config import SystemConfigService

logger = get_logger("chat_service")


# ==================== AgentRunner 实现 ====================


class SkillKnowAgentRunner:
    """AgentRunner 实现：委托给 agent_service.chat_stream()"""

    def __init__(
        self,
        *,
        model: Any,
        system_prompt: str,
        session: Any = None,
    ) -> None:
        self._model = model
        self._system_prompt = system_prompt
        self._session = session

    async def run(self, message: str, context: ChatContext, **kwargs: Any) -> None:
        await agent_service.chat_stream(
            message=message,
            conversation_id=context.conversation_id,
            model=self._model,
            system_prompt=self._system_prompt,
            context=context,
            session=self._session,
        )


# ==================== ChatService ====================


class ChatService:
    """聊天服务 - Skill-driven Agent"""

    def __init__(self, session: AsyncSession):
        self._session = session
        self._conversation_service = ConversationService(session)
        self._skill_service = SkillService(session)
        self._prompt_service = PromptService(session)
        self._config_service = SystemConfigService(session)

    async def _get_llm(self) -> V1ChatModel:
        """获取 LLM 实例（使用 V1 模式）"""
        config = await self._config_service.get_llm_config()
        return V1ChatModel(
            api_key=config["api_key"],
            base_url=config["base_url"],
            model=config["chat_model"],
            streaming=True,
        )

    async def _pre_retrieve(self, message: str, limit: int = 3) -> str:
        """预检索：对用户消息做快速语义检索，返回格式化的知识上下文。

        参考 OpenViking 的 RAG 注入模式：在 Agent 运行之前就将相关知识注入 system prompt，
        减少 Agent 对工具调用的依赖，降低延迟。
        """
        try:
            from app.core.config import settings
            from app.core.rerank import get_rerank_client

            vector_store = get_service().get_vector_store(self._session)
            rerank_client = (
                get_rerank_client()
                if settings.DEFAULT_SEARCH_MODE == "thinking"
                else None
            )
            retriever = SkillRetriever(
                self._session,
                vector_store=vector_store,
                rerank_client=rerank_client,
            )
            response = await retriever.retrieve(query=message, limit=limit, threshold=0.2)

            if not response.results:
                return ""

            parts = ["## 以下是与用户问题可能相关的知识库内容（自动检索）：\n"]
            for i, r in enumerate(response.results):
                content = r.overview or r.abstract or r.content[:500]
                parts.append(
                    f"### [{i+1}] {r.name}\n"
                    f"- 相关度: {r.score:.2f}\n"
                    f"- 摘要: {r.abstract}\n"
                    f"- 内容:\n{content}\n"
                )

            parts.append(
                "\n> 提示：如需更详细的信息，可以使用 get_skill_content 工具获取完整内容。"
            )
            context_str = "\n".join(parts)
            logger.info("预检索命中", count=len(response.results), query=message[:50])
            return context_str

        except Exception as e:
            logger.warning(f"预检索失败（非阻塞）: {e}")
            return ""

    async def _async_compress(self, conversation_id: str) -> None:
        """异步执行会话压缩"""
        try:
            from app.core.database import get_db_context
            from app.services.session_compressor import SessionCompressor
            from app.services.system_config import SystemConfigService

            async with get_db_context() as session:
                config_service = SystemConfigService(session)
                llm_config = await config_service.get_llm_config()
                llm = None
                if llm_config.get("api_key"):
                    from langchain_openai import ChatOpenAI

                    llm = ChatOpenAI(
                        api_key=llm_config["api_key"],
                        base_url=llm_config["base_url"],
                        model=llm_config["chat_model"],
                        temperature=0.3,
                    )
                compressor = SessionCompressor(session=session, llm=llm)
                await compressor.compress(conversation_id)
                await session.commit()
        except Exception as e:
            logger.warning(f"异步会话压缩失败: {e}")

    async def chat_stream(
        self,
        message: str,
        conversation_id: str | None = None,
    ) -> AsyncGenerator[StreamEvent, None]:
        """流式聊天 - 委托给状态机驱动的 Agent 模式"""
        async for event in self.chat_stream_with_tools(message, conversation_id):
            yield event

    async def chat_stream_with_tools(
        self,
        message: str,
        conversation_id: str | None = None,
    ) -> AsyncGenerator[StreamEvent, None]:
        """流式聊天 - 使用 SDK v0.2.0 Orchestrator

        Orchestrator 自动管理：
        - 事件队列（QueueDomainEmitter + asyncio.Queue）
        - 内容聚合（ContentAggregator: full_content, reasoning）
        - meta.start / error 事件自动发送
        - on_stream_end 钩子落库
        """
        # 创建或获取会话
        if conversation_id:
            conversation = await self._conversation_service.get_conversation(
                conversation_id
            )
            if not conversation:
                conversation = await self._conversation_service.create_conversation()
                conversation_id = conversation.id
        else:
            conversation = await self._conversation_service.create_conversation()
            conversation_id = conversation.id

        user_message_id = str(uuid.uuid4())
        assistant_message_id = str(uuid.uuid4())

        # 保存用户消息
        await self._conversation_service.add_message(
            conversation_id=conversation_id,
            role="user",
            content=message,
            message_id=user_message_id,
        )

        # 获取 LLM 和系统提示词
        llm = await self._get_llm()
        system_prompt = await self._prompt_service.get_content("system.chat") or ""

        # 预检索：在 Agent 运行前检索相关知识并注入 system prompt
        pre_retrieved_context = await self._pre_retrieve(message)
        if pre_retrieved_context:
            system_prompt = f"{system_prompt}\n\n{pre_retrieved_context}"

        # 注入会话压缩摘要（如果有）
        if conversation and conversation.extra_metadata:
            summary = conversation.extra_metadata.get("summary", "")
            if summary:
                system_prompt = f"{system_prompt}\n\n## 之前的对话摘要（已压缩）\n{summary}"

        # 构建 AgentRunner
        runner = SkillKnowAgentRunner(
            model=llm,
            system_prompt=system_prompt,
            session=self._session,
        )

        # 落库 & 日志钩子
        conversation_service = self._conversation_service
        user_msg = message

        async def on_stream_end(info: StreamEndInfo) -> None:
            agg = info.aggregator
            latency_ms = info.context.response_latency_ms
            await conversation_service.add_message(
                conversation_id=info.conversation_id,
                role="assistant",
                content=agg.full_content,
                message_id=info.assistant_message_id,
                latency_ms=latency_ms,
            )
            logger.debug(
                "已保存 assistant message (SDK v0.2)",
                message_id=info.assistant_message_id,
                content_length=len(agg.full_content),
            )

            # 更新会话统计
            try:
                conv = await conversation_service.get_conversation(info.conversation_id)
                if conv:
                    stats = conv.extra_metadata.get("stats", {}) if conv.extra_metadata else {}
                    stats["total_turns"] = stats.get("total_turns", 0) + 1
                    conv.extra_metadata = {**(conv.extra_metadata or {}), "stats": stats}
                    await self._session.flush()
            except Exception:
                pass

            # 异步提取对话知识（不阻塞响应）
            import asyncio

            from app.services.knowledge_extractor import extract_and_store_knowledge

            asyncio.create_task(
                extract_and_store_knowledge(
                    conversation_id=info.conversation_id,
                    messages=[
                        {"role": "user", "content": user_msg},
                        {"role": "assistant", "content": agg.full_content},
                    ],
                )
            )

            # 检查是否需要会话压缩
            try:
                from app.services.session_compressor import SessionCompressor

                compressor = SessionCompressor(session=self._session)
                if await compressor.should_compress(info.conversation_id):
                    asyncio.create_task(
                        self._async_compress(info.conversation_id)
                    )
            except Exception:
                pass

        async def on_error(e: Exception, conv_id: str) -> None:
            logger.exception("Agent 聊天失败 (SDK v0.2)", conversation_id=conv_id, error=str(e))

        orchestrator = Orchestrator(
            agent_runner=runner,
            hooks=OrchestratorHooks(
                on_stream_end=on_stream_end,
                on_error=on_error,
            ),
        )

        async for event in orchestrator.run(
            message=message,
            conversation_id=conversation_id,
            user_id="default_user",
            assistant_message_id=assistant_message_id,
            user_message_id=user_message_id,
            db=self._session,
        ):
            yield event

    async def chat(self, message: str, conversation_id: str | None = None) -> dict:
        """非流式聊天"""
        result = {
            "conversation_id": "",
            "message_id": "",
            "content": "",
        }

        async for event in self.chat_stream(message, conversation_id):
            if event.type == StreamEventType.META_START.value:
                result["conversation_id"] = event.conversation_id
                result["message_id"] = event.message_id
            elif event.type == StreamEventType.ASSISTANT_DELTA.value:
                result["content"] += event.payload.get("delta", "")
            elif event.type == StreamEventType.ERROR.value:
                raise Exception(event.payload.get("message", "Unknown error"))

        return result
