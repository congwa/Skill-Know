"""聊天服务 - SDK v0.2.0 版本

使用 Orchestrator + AgentRunner + ContentAggregator 重构。
队列管理、内容聚合、错误处理均由 SDK 自动完成，
业务只需实现 AgentRunner 和 on_stream_end 钩子。
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from typing import Any

from langchain_core.messages import HumanMessage, AIMessage
from sqlalchemy.ext.asyncio import AsyncSession

from langgraph_agent_kit import (
    StreamEvent,
    Orchestrator,
    OrchestratorHooks,
    StreamEndInfo,
)
from langgraph_agent_kit.core.context import ChatContext

from app.core.chat_models import V1ChatModel
from app.core.logging import get_logger
from app.schemas.events import StreamEventType
from app.services.conversation import ConversationService
from app.services.skill import SkillService
from app.services.prompt import PromptService
from app.services.system_config import SystemConfigService
from app.services.agent.core import agent_service

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

    async def _build_messages(
        self,
        conversation_id: str,
        user_message: str,
        skill_context: str = "",
    ) -> list:
        """构建消息列表
        
        Args:
            conversation_id: 会话 ID
            user_message: 用户消息
            skill_context: 匹配的 Skill 内容（渐进式加载）
        """
        messages = []

        # 系统提示词
        system_prompt = await self._prompt_service.get_content("system.chat")
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))

        # 注入匹配的 Skill 内容（渐进式加载的核心）
        if skill_context:
            messages.append(SystemMessage(content=skill_context))

        # 历史消息
        history = await self._conversation_service.get_messages(conversation_id)
        for msg in history:
            if msg.role.value == "user":
                messages.append(HumanMessage(content=msg.content))
            elif msg.role.value == "assistant":
                messages.append(AIMessage(content=msg.content))

        # 当前用户消息
        messages.append(HumanMessage(content=user_message))

        return messages

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

        # 构建 AgentRunner
        runner = SkillKnowAgentRunner(
            model=llm,
            system_prompt=system_prompt,
            session=self._session,
        )

        # 落库 & 日志钩子
        conversation_service = self._conversation_service

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
