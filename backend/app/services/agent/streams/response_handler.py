"""流响应处理器 - 解析 Agent 流输出，发射事件

使用方式：
    from app.services.agent.streams import StreamingResponseHandler

    # 传入 model，自动检测版本
    handler = StreamingResponseHandler(emitter=context.emitter, model=model)

    async for msg in agent.astream(...):
        await handler.handle_message(msg)
    result = await handler.finalize()

职责：
    1. 解析 AIMessageChunk/AIMessage/ToolMessage
    2. 按块类型分流：text → 正文增量，reasoning → 推理增量
    3. 发射对应的事件到 emitter
    4. 汇总最终结果

版本自动检测：
    - 根据 model 的 _chat_model_version 属性自动判断
    - v1 模型：使用 parse_content_blocks() 从 content_blocks 提取
    - v0 模型：使用 model.extract_reasoning() 从自定义属性提取
    - 无 model 时默认使用 v1
"""

import json
from dataclasses import dataclass, field
from typing import Any

from langchain_core.messages import AIMessage, AIMessageChunk, ToolMessage

from app.core.logging import get_logger
from app.schemas.events import StreamEventType

logger = get_logger("streams.handler")


@dataclass
class StreamingResponseHandler:
    """流响应处理器（根据 model 自动检测版本）

    Attributes:
        emitter: 事件发射器（需要有 aemit 方法）
        model: LLM 模型实例（用于版本检测和 v0 模式的 extract_reasoning）
        conversation_id: 会话 ID（用于日志）
    """

    emitter: Any
    model: Any = None
    conversation_id: str = ""

    # 内部状态
    full_content: str = field(default="", init=False)
    full_reasoning: str = field(default="", init=False)
    seen_tool_ids: set[str] = field(default_factory=set, init=False)

    # 统计
    content_events: int = field(default=0, init=False)
    reasoning_events: int = field(default=0, init=False)
    reasoning_chars: int = field(default=0, init=False)

    async def handle_message(self, msg: Any) -> None:
        """处理单条消息（核心分发逻辑）

        Args:
            msg: LangChain 消息对象
        """
        # 调试：记录收到的消息类型（临时使用 info 级别便于调试）
        msg_type = type(msg).__name__
        content_preview = getattr(msg, 'content', None)
        if content_preview and isinstance(content_preview, str):
            content_preview = content_preview[:100]
        elif content_preview and isinstance(content_preview, list):
            content_preview = f"list[{len(content_preview)}]"
        logger.info(f"📨 收到消息: type={msg_type}, content={content_preview}")
        
        if isinstance(msg, AIMessageChunk):
            await self._handle_ai_chunk(msg)
        elif isinstance(msg, AIMessage):
            await self._handle_ai_message(msg)
        elif isinstance(msg, ToolMessage):
            await self._handle_tool_message(msg)
        else:
            logger.debug(f"⚠️ 未处理的消息类型: {msg_type}")

    def _is_v1_model(self) -> bool:
        """检测是否使用 v1 模式"""
        from app.core.chat_models import is_v1_model
        return is_v1_model(self.model)

    async def _handle_ai_chunk(self, msg: AIMessageChunk) -> None:
        """处理 AI 增量消息"""
        is_v1 = self._is_v1_model()
        logger.info(f"🔍 模型版本检测: is_v1={is_v1}, model_type={type(self.model).__name__}")
        if is_v1:
            await self._handle_ai_chunk_v1(msg)
        else:
            await self._handle_ai_chunk_v0(msg)

    async def _handle_ai_chunk_v1(self, msg: AIMessageChunk) -> None:
        """v1：使用 content_blocks 解析"""
        from app.core.chat_models import parse_content_blocks

        parsed = parse_content_blocks(msg)

        # 文本增量
        text_delta = parsed.text
        if text_delta:
            self.full_content += text_delta
            self.content_events += 1
            # 记录流输出（仅前100字符，避免日志过长）
            if self.content_events <= 3 or self.content_events % 10 == 0:
                logger.debug(f"📝 流输出 #{self.content_events}: {text_delta[:100]}..." if len(text_delta) > 100 else f"📝 流输出 #{self.content_events}: {text_delta}")
            await self.emitter.aemit(
                StreamEventType.ASSISTANT_DELTA.value,
                {"delta": text_delta},
            )

        # 推理增量
        reasoning_delta = parsed.reasoning
        if reasoning_delta:
            self.full_reasoning += reasoning_delta
            self.reasoning_chars += len(reasoning_delta)
            self.reasoning_events += 1
            await self.emitter.aemit(
                StreamEventType.ASSISTANT_REASONING_DELTA.value,
                {"delta": reasoning_delta},
            )

    async def _handle_ai_chunk_v0(self, msg: AIMessageChunk) -> None:
        """v0：使用 model.extract_reasoning() 解析"""
        # 正文增量
        delta = msg.content or ""
        logger.info(f"🔧 v0处理: delta类型={type(delta).__name__}, 内容={delta[:50] if isinstance(delta, str) else delta}")
        if isinstance(delta, list):
            delta = "".join(str(x) for x in delta)
        if isinstance(delta, str) and delta:
            self.full_content += delta
            self.content_events += 1
            # 记录流输出
            logger.info(f"📝 发送delta #{self.content_events}: {delta[:50]}...")
            await self.emitter.aemit(
                StreamEventType.ASSISTANT_DELTA.value,
                {"delta": delta},
            )

        # 推理增量（通过多态接口提取）
        if self.model and hasattr(self.model, "extract_reasoning"):
            reasoning_chunk = self.model.extract_reasoning(msg)
            if reasoning_chunk and reasoning_chunk.delta:
                self.full_reasoning += reasoning_chunk.delta
                self.reasoning_chars += len(reasoning_chunk.delta)
                self.reasoning_events += 1
                await self.emitter.aemit(
                    StreamEventType.ASSISTANT_REASONING_DELTA.value,
                    {"delta": reasoning_chunk.delta},
                )

    async def _handle_ai_message(self, msg: AIMessage) -> None:
        """处理完整 AI 消息（兜底场景）"""
        if self._is_v1_model():
            await self._handle_ai_message_v1(msg)
        else:
            await self._handle_ai_message_v0(msg)

    async def _handle_ai_message_v1(self, msg: AIMessage) -> None:
        """v1：使用 content_blocks 解析（兜底）"""
        from app.core.chat_models import parse_content_blocks

        parsed = parse_content_blocks(msg)

        # 兜底：如果之前没有收到任何 content chunk
        if self.content_events == 0:
            text_delta = parsed.text
            if text_delta:
                self.full_content += text_delta
                self.content_events += 1
                await self.emitter.aemit(
                    StreamEventType.ASSISTANT_DELTA.value,
                    {"delta": text_delta},
                )

        # 兜底：从完整 AIMessage 提取推理
        if self.reasoning_events == 0:
            reasoning_delta = parsed.reasoning
            if reasoning_delta:
                self.full_reasoning += reasoning_delta
                self.reasoning_chars += len(reasoning_delta)
                self.reasoning_events += 1
                await self.emitter.aemit(
                    StreamEventType.ASSISTANT_REASONING_DELTA.value,
                    {"delta": reasoning_delta},
                )

    async def _handle_ai_message_v0(self, msg: AIMessage) -> None:
        """v0：使用 model.extract_reasoning() 解析（兜底）"""
        # 兜底：如果之前没有收到任何 content chunk
        if self.content_events == 0:
            delta = msg.content or ""
            if isinstance(delta, list):
                delta = "".join(str(x) for x in delta)
            if isinstance(delta, str) and delta:
                self.full_content += delta
                self.content_events += 1
                await self.emitter.aemit(
                    StreamEventType.ASSISTANT_DELTA.value,
                    {"delta": delta},
                )

        # 兜底：从完整 AIMessage 提取推理
        if self.reasoning_events == 0 and self.model and hasattr(self.model, "extract_reasoning"):
            reasoning_chunk = self.model.extract_reasoning(msg)
            if reasoning_chunk and reasoning_chunk.delta:
                self.full_reasoning += reasoning_chunk.delta
                self.reasoning_chars += len(reasoning_chunk.delta)
                self.reasoning_events += 1
                await self.emitter.aemit(
                    StreamEventType.ASSISTANT_REASONING_DELTA.value,
                    {"delta": reasoning_chunk.delta},
                )

    async def _handle_tool_message(self, msg: ToolMessage) -> None:
        """处理工具消息"""
        # 去重
        msg_id = getattr(msg, "id", None)
        if isinstance(msg_id, str) and msg_id in self.seen_tool_ids:
            return
        if isinstance(msg_id, str):
            self.seen_tool_ids.add(msg_id)

        content = msg.content
        try:
            parsed_data: Any
            if isinstance(content, str):
                parsed_data = json.loads(content)
            elif isinstance(content, (list, dict)):
                parsed_data = content
            else:
                return
        except Exception:
            pass

    async def finalize(self) -> dict[str, Any]:
        """发送最终事件，返回汇总数据

        Returns:
            包含 content、reasoning 的字典
        """
        # 兜底：仅当"全程没有任何 content delta"时，才把 reasoning 兜底成 content（避免混流）
        if self.content_events == 0 and self.full_reasoning.strip():
            logger.warning(
                "检测到 content 全程为空，兜底将 reasoning 作为 content 输出",
                conversation_id=self.conversation_id,
                content_len=len(self.full_content),
                reasoning_len=len(self.full_reasoning),
            )
            self.full_content = self.full_reasoning
            self.full_reasoning = ""

        result = {
            "content": self.full_content,
            "reasoning": self.full_reasoning if self.full_reasoning else None,
        }

        await self.emitter.aemit(StreamEventType.ASSISTANT_FINAL.value, result)

        logger.info(
            "✅ 流处理完成",
            conversation_id=self.conversation_id,
            content_events=self.content_events,
            reasoning_events=self.reasoning_events,
            reasoning_chars=self.reasoning_chars,
        )

        return result

    def get_stats(self) -> dict[str, int]:
        """获取统计信息

        Returns:
            统计字典
        """
        return {
            "content_events": self.content_events,
            "reasoning_events": self.reasoning_events,
            "reasoning_chars": self.reasoning_chars,
        }
