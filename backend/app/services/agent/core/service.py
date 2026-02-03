"""Agent 服务

管理 Agent 生命周期和聊天流程编排。
"""

import asyncio
from typing import Any

from langchain_core.messages import HumanMessage
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph.state import CompiledStateGraph

from app.core.logging import get_logger
from app.schemas.events import StreamEventType
from app.services.agent.core.factory import build_agent
from app.services.agent.streams import StreamingResponseHandler
from app.services.streaming.context import ChatContext

logger = get_logger("agent.service")


class AgentService:
    """Agent 服务 - 管理 Agent 生命周期"""

    _instance: "AgentService | None" = None
    _agent: CompiledStateGraph | None = None
    _checkpointer: BaseCheckpointSaver | None = None
    _init_lock: asyncio.Lock | None = None

    def __new__(cls) -> "AgentService":
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._agent = None
            cls._instance._checkpointer = None
            cls._instance._init_lock = asyncio.Lock()
        return cls._instance

    async def _get_checkpointer(self) -> BaseCheckpointSaver:
        """获取 checkpointer"""
        if self._checkpointer is not None:
            return self._checkpointer

        from langgraph.checkpoint.memory import MemorySaver

        self._checkpointer = MemorySaver()
        return self._checkpointer

    async def close(self) -> None:
        """关闭连接"""
        self._checkpointer = None
        self._agent = None

    async def get_agent(
        self,
        model: Any,
        system_prompt: str,
        session: Any = None,
        emitter: Any = None,
    ) -> CompiledStateGraph:
        """获取 Agent 实例

        Args:
            model: LLM 模型实例
            system_prompt: 系统提示词
            session: 数据库会话
            emitter: 事件发射器

        Returns:
            编译后的 Agent 图
        """
        # 获取 checkpointer
        checkpointer = await self._get_checkpointer()

        # 构建 Agent
        agent = await build_agent(
            model=model,
            system_prompt=system_prompt,
            checkpointer=checkpointer,
            session=session,
            emitter=emitter,
        )

        return agent

    async def chat_stream(
        self,
        *,
        message: str,
        conversation_id: str,
        model: Any,
        system_prompt: str,
        context: ChatContext,
        session: Any = None,
    ) -> None:
        """执行聊天流，将事件写入 context.emitter

        Args:
            message: 用户消息
            conversation_id: 会话 ID
            model: LLM 模型实例
            system_prompt: 系统提示词
            context: 聊天上下文
            session: 数据库会话
        """
        emitter = getattr(context, "emitter", None)
        if emitter is None or not hasattr(emitter, "aemit"):
            raise RuntimeError("chat_stream 需要 context.emitter.aemit()")

        try:
            # 获取 Agent
            agent = await self.get_agent(
                model=model,
                system_prompt=system_prompt,
                session=session,
                emitter=emitter,
            )
        except Exception as e:
            error_msg = "智能助手初始化失败，请稍后再试"
            logger.error("Agent 构建失败", error=str(e), conversation_id=conversation_id)
            try:
                await emitter.aemit(
                    StreamEventType.ERROR.value,
                    {"message": error_msg, "detail": str(e), "code": "agent_init_failed"},
                )
                await emitter.aemit("__end__", None)
            except Exception:
                pass
            return

        # 使用流响应处理器
        handler = StreamingResponseHandler(
            emitter=emitter,
            model=model,
            conversation_id=conversation_id,
        )

        # 准备 Agent 输入
        agent_input = {"messages": [HumanMessage(content=message)]}
        agent_config: dict[str, Any] = {"configurable": {"thread_id": conversation_id}}

        try:
            async for item in agent.astream(
                agent_input,
                config=agent_config,
                context=context,
                stream_mode="messages",
            ):
                msg = item[0] if isinstance(item, (tuple, list)) and item else item
                await handler.handle_message(msg)

            await handler.finalize()

        except Exception as e:
            logger.exception("chat_stream 失败", error=str(e), conversation_id=conversation_id)
            try:
                await emitter.aemit(StreamEventType.ERROR.value, {"message": str(e)})
            except Exception:
                pass
        finally:
            try:
                await emitter.aemit("__end__", None)
            except Exception:
                pass


# 全局单例
agent_service = AgentService()
