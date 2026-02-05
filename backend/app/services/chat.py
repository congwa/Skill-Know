"""聊天服务

实现基于 Skill-driven 的聊天功能，支持渐进式加载和流式响应。
"""

import asyncio
import time
import uuid
from collections.abc import AsyncGenerator
from typing import Any

from langchain_core.messages import HumanMessage, AIMessage
from sqlalchemy.ext.asyncio import AsyncSession

from langgraph_agent_kit import QueueDomainEmitter, make_event

from app.core.chat_models import V1ChatModel
from app.core.logging import get_logger
from app.schemas.events import StreamEventType, StreamEvent
from app.services.conversation import ConversationService
from app.services.skill import SkillService
from app.services.prompt import PromptService
from app.services.system_config import SystemConfigService
from app.services.agent.core import agent_service
from app.services.agent.streams import StreamingResponseHandler
from app.services.streaming.context import ChatContext

logger = get_logger("chat_service")


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
        """流式聊天 - 使用 LangGraph Agent
        
        使用 create_agent + agent.astream 处理消息流，
        工具调用由 LangGraph 内部处理。
        """
        seq = 0

        def next_seq() -> int:
            nonlocal seq
            seq += 1
            return seq

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

        # 发送开始事件
        yield make_event(
            seq=next_seq(),
            type=StreamEventType.META_START.value,
            conversation_id=conversation_id,
            message_id=assistant_message_id,
            payload={
                "user_message_id": user_message_id,
                "assistant_message_id": assistant_message_id,
                "mode": "agent",
            },
        )

        try:
            start_time = time.time()

            # 获取 LLM
            llm = await self._get_llm()

            # 获取系统提示词
            system_prompt = await self._prompt_service.get_content("system.chat") or ""

            # 使用 SDK 的 QueueDomainEmitter
            loop = asyncio.get_running_loop()
            domain_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=10000)
            emitter = QueueDomainEmitter(queue=domain_queue, loop=loop)

            # 创建上下文
            context = ChatContext(
                emitter=emitter,
                conversation_id=conversation_id,
                user_id="default_user",
                assistant_message_id=assistant_message_id,
                db=self._session,
            )

            # 获取 Agent
            agent = await agent_service.get_agent(
                model=llm,
                system_prompt=system_prompt,
                session=self._session,
                emitter=emitter,
            )

            # 使用 SDK 流响应处理器
            handler = StreamingResponseHandler(
                emitter=emitter,
                conversation_id=conversation_id,
            )

            # 准备 Agent 输入
            agent_input = {"messages": [HumanMessage(content=message)]}
            agent_config: dict[str, Any] = {"configurable": {"thread_id": conversation_id}}

            full_content = ""

            # 创建 Agent 流任务
            async def run_agent_stream():
                stream_item_count = 0
                try:
                    async for item in agent.astream(
                        agent_input,
                        config=agent_config,
                        context=context,
                        stream_mode="messages",
                    ):
                        stream_item_count += 1
                        msg = item[0] if isinstance(item, (tuple, list)) and item else item
                        logger.info(f"🔄 流消息 #{stream_item_count}: type={type(msg).__name__}")
                        await handler.handle_message(msg)
                    
                    logger.info(f"✅ 流处理完成, 共 {stream_item_count} 条消息")
                    await handler.finalize()
                finally:
                    # 发送结束标记
                    await domain_queue.put({"type": "__end__", "payload": None})

            # 启动 Agent 流任务
            producer_task = asyncio.create_task(run_agent_stream())

            # 从队列消费事件并 yield
            while True:
                evt = await domain_queue.get()
                evt_type = evt.get("type")
                if evt_type == "__end__":
                    break

                payload = evt.get("payload", {})
                
                # 收集最终内容
                if evt_type == StreamEventType.ASSISTANT_DELTA.value:
                    delta = payload.get("delta", "")
                    if delta:
                        full_content += delta
                elif evt_type == StreamEventType.ASSISTANT_FINAL.value:
                    full_content = payload.get("content") or full_content

                yield make_event(
                    seq=next_seq(),
                    conversation_id=conversation_id,
                    message_id=assistant_message_id,
                    type=evt_type,
                    payload=payload,
                )

            await producer_task

            elapsed_ms = int((time.time() - start_time) * 1000)

            # 保存助手消息
            await self._conversation_service.add_message(
                conversation_id=conversation_id,
                role="assistant",
                content=full_content,
                message_id=assistant_message_id,
                latency_ms=elapsed_ms,
            )

        except Exception as e:
            logger.exception("Agent 聊天失败", conversation_id=conversation_id, error=str(e))
            yield make_event(
                seq=next_seq(),
                type=StreamEventType.ERROR.value,
                conversation_id=conversation_id,
                message_id=assistant_message_id,
                payload={"message": str(e)},
            )

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
