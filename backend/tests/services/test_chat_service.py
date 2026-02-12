"""ChatService 单元测试（SDK v0.2.0）

测试 Orchestrator 集成：
- SkillKnowAgentRunner 委托
- ContentAggregator 自动聚合
- on_stream_end 落库钩子
"""

from __future__ import annotations

import asyncio
import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from langgraph_agent_kit import StreamEventType
from langgraph_agent_kit.core.context import ChatContext

# 所有 async 测试的超时（秒）
ASYNC_TIMEOUT = 10


# ==================== Fixtures ====================


class FakeAgentService:
    """模拟 AgentService，通过 emitter 发送预定义事件序列"""

    def __init__(self, events: list[tuple[str, dict[str, Any]]] | None = None):
        self._events = events or []

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
        emitter = context.emitter
        for evt_type, payload in self._events:
            await emitter.aemit(evt_type, payload)
        await emitter.aemit("__end__", None)


class FakeConversationService:
    """模拟 ConversationService"""

    def __init__(self):
        self.saved_messages: list[dict[str, Any]] = []

    async def add_message(self, **kwargs: Any) -> None:
        self.saved_messages.append(kwargs)

    async def get_conversation(self, conv_id: str) -> Any:
        return MagicMock(id=conv_id)

    async def create_conversation(self) -> Any:
        return MagicMock(id="new-conv-1")


# ==================== SkillKnowAgentRunner Tests ====================


@pytest.mark.anyio
class TestSkillKnowAgentRunner:
    """测试 AgentRunner 实现"""

    async def test_delegates_to_agent_service(self):
        """AgentRunner 应正确委托给 agent_service.chat_stream()"""
        from app.services.chat import SkillKnowAgentRunner

        mock_agent_service = AsyncMock()

        # Patch agent_service 单例
        import app.services.chat as chat_module
        original = chat_module.agent_service
        chat_module.agent_service = mock_agent_service

        try:
            runner = SkillKnowAgentRunner(
                model="fake-model",
                system_prompt="你是助手",
                session=None,
            )

            mock_context = MagicMock(spec=ChatContext)
            mock_context.conversation_id = "conv-1"

            await runner.run(message="你好", context=mock_context)

            mock_agent_service.chat_stream.assert_called_once_with(
                message="你好",
                conversation_id="conv-1",
                model="fake-model",
                system_prompt="你是助手",
                context=mock_context,
                session=None,
            )
        finally:
            chat_module.agent_service = original


# ==================== Orchestrator Integration Tests ====================


async def _run_chat_stream(
    events: list[tuple[str, dict[str, Any]]],
    message: str = "你好",
) -> tuple[list[dict], FakeConversationService]:
    """辅助：通过 Orchestrator 运行聊天流并收集事件（带超时）"""
    from langgraph_agent_kit import Orchestrator, OrchestratorHooks, StreamEndInfo
    from app.services.chat import SkillKnowAgentRunner

    conv_service = FakeConversationService()
    fake_agent_svc = FakeAgentService(events)

    # Patch agent_service
    import app.services.chat as chat_module
    original = chat_module.agent_service
    chat_module.agent_service = fake_agent_svc

    try:
        runner = SkillKnowAgentRunner(
            model="fake-model",
            system_prompt="你是助手",
            session=None,
        )

        async def on_stream_end(info: StreamEndInfo) -> None:
            agg = info.aggregator
            await conv_service.add_message(
                conversation_id=info.conversation_id,
                role="assistant",
                content=agg.full_content,
                message_id=info.assistant_message_id,
                latency_ms=info.context.response_latency_ms,
            )

        orchestrator = Orchestrator(
            agent_runner=runner,
            hooks=OrchestratorHooks(on_stream_end=on_stream_end),
        )

        collected: list[dict] = []

        async def _collect():
            async for event in orchestrator.run(
                message=message,
                conversation_id="test-conv-1",
                user_id="test-user",
                assistant_message_id="amsg-1",
                user_message_id="umsg-1",
            ):
                collected.append(
                    event.model_dump() if hasattr(event, "model_dump") else dict(event)
                )

        await asyncio.wait_for(_collect(), timeout=ASYNC_TIMEOUT)
        return collected, conv_service
    finally:
        chat_module.agent_service = original


@pytest.mark.anyio
class TestChatServiceOrchestrator:
    """测试 Orchestrator 编排流程"""

    async def test_meta_start_emitted(self):
        """meta.start 事件应自动发送"""
        events, _ = await _run_chat_stream([])

        start_events = [e for e in events if e.get("type") == "meta.start"]
        assert len(start_events) == 1
        payload = start_events[0]["payload"]
        assert payload["user_message_id"] == "umsg-1"
        assert payload["assistant_message_id"] == "amsg-1"

    async def test_assistant_delta_forwarded(self):
        """assistant.delta 事件应正确转发"""
        domain_events = [
            (StreamEventType.ASSISTANT_DELTA.value, {"delta": "你"}),
            (StreamEventType.ASSISTANT_DELTA.value, {"delta": "好"}),
        ]
        events, _ = await _run_chat_stream(domain_events)

        deltas = [e for e in events if e.get("type") == "assistant.delta"]
        assert len(deltas) == 2
        assert deltas[0]["payload"]["delta"] == "你"
        assert deltas[1]["payload"]["delta"] == "好"

    async def test_content_aggregated_and_saved(self):
        """ContentAggregator 应聚合内容并在 on_stream_end 落库"""
        domain_events = [
            (StreamEventType.ASSISTANT_DELTA.value, {"delta": "你好"}),
            (StreamEventType.ASSISTANT_FINAL.value, {"content": "你好"}),
        ]
        _, conv_service = await _run_chat_stream(domain_events)

        assert len(conv_service.saved_messages) == 1
        saved = conv_service.saved_messages[0]
        assert saved["conversation_id"] == "test-conv-1"
        assert saved["role"] == "assistant"
        assert saved["content"] == "你好"
        assert saved["message_id"] == "amsg-1"

    async def test_reasoning_aggregated(self):
        """推理内容应被聚合"""
        domain_events = [
            (StreamEventType.ASSISTANT_REASONING_DELTA.value, {"delta": "思考..."}),
            (StreamEventType.ASSISTANT_DELTA.value, {"delta": "回复"}),
            (StreamEventType.ASSISTANT_FINAL.value, {"content": "回复", "reasoning": "思考..."}),
        ]
        events, conv_service = await _run_chat_stream(domain_events)

        # 验证 reasoning delta 被转发
        reasoning_events = [e for e in events if e.get("type") == "assistant.reasoning.delta"]
        assert len(reasoning_events) == 1

        # 验证落库
        saved = conv_service.saved_messages[0]
        assert saved["content"] == "回复"

    async def test_seq_monotonically_increasing(self):
        """事件序号应单调递增"""
        domain_events = [
            (StreamEventType.ASSISTANT_DELTA.value, {"delta": "a"}),
            (StreamEventType.ASSISTANT_DELTA.value, {"delta": "b"}),
            (StreamEventType.ASSISTANT_FINAL.value, {"content": "ab"}),
        ]
        events, _ = await _run_chat_stream(domain_events)

        seqs = [e.get("seq") for e in events if e.get("seq") is not None]
        for i in range(1, len(seqs)):
            assert seqs[i] > seqs[i - 1], f"seq 不单调递增: {seqs}"


class TestSkillKnowAgentRunnerSync:
    """同步测试"""

    def test_runner_stores_params(self):
        """AgentRunner 应保存初始化参数"""
        from app.services.chat import SkillKnowAgentRunner

        runner = SkillKnowAgentRunner(
            model="test-model",
            system_prompt="test-prompt",
            session="test-session",
        )
        assert runner._model == "test-model"
        assert runner._system_prompt == "test-prompt"
        assert runner._session == "test-session"
