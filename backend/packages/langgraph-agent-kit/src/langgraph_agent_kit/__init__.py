"""LangGraph Agent Kit - 统一的流式聊天 Agent 框架

提供统一的事件协议、上下文管理、事件发射器和流编排器。
支持工具和中间件内部推送 SSE 事件。
"""

__version__ = "0.2.0"

from langgraph_agent_kit.chat_models import (
    V0_REASONING_MODEL_REGISTRY,
    V1_REASONING_MODEL_REGISTRY,
    BaseReasoningChatModel,
    ReasoningChunk,
    SiliconFlowReasoningChatModel,
    SiliconFlowV1ChatModel,
    StandardChatModel,
    V1ChatModel,
    create_chat_model,
    is_v1_model,
)
from langgraph_agent_kit.core.context import ChatContext, DomainEmitter
from langgraph_agent_kit.core.emitter import QueueDomainEmitter
from langgraph_agent_kit.core.events import (
    AgentCompletePayload,
    AgentHandoffPayload,
    AgentRoutedPayload,
    ContextEditedPayload,
    ContextSummarizedPayload,
    ContextTrimmedPayload,
    ErrorPayload,
    LlmCallEndPayload,
    LlmCallStartPayload,
    MemoryExtractionCompletePayload,
    MemoryExtractionStartPayload,
    MemoryProfileUpdatedPayload,
    MetaStartPayload,
    ModelCallLimitExceededPayload,
    ModelFallbackPayload,
    ModelRetryFailedPayload,
    ModelRetryStartPayload,
    SkillActivatedPayload,
    SkillLoadedPayload,
    StreamEventType,
    TextDeltaPayload,
    TodoItem,
    TodosPayload,
    ToolEndPayload,
    ToolStartPayload,
)
from langgraph_agent_kit.core.stream_event import StreamEvent
from langgraph_agent_kit.helpers import (
    emit_tool_end,
    emit_tool_start,
    get_emitter_from_request,
    get_emitter_from_runtime,
)
from langgraph_agent_kit.kit import ChatStreamKit
from langgraph_agent_kit.middleware.base import BaseMiddleware, MiddlewareConfig, MiddlewareSpec
from langgraph_agent_kit.middleware.builtin import Middlewares
from langgraph_agent_kit.middleware.registry import MiddlewareRegistry
from langgraph_agent_kit.orchestrator import (
    AgentRunner,
    ContentAggregator,
    Orchestrator,
    OrchestratorHooks,
    StreamEndInfo,
    StreamStartInfo,
)
from langgraph_agent_kit.streaming.content_parser import (
    ParsedContent,
    parse_content_blocks,
    parse_content_blocks_from_chunk,
)
from langgraph_agent_kit.streaming.content_types import (
    ContentBlock,
    ImageContentBlock,
    InvalidToolCall,
    ReasoningContentBlock,
    TextContentBlock,
    ToolCallBlock,
    ToolCallChunk,
    get_block_type,
    is_image_block,
    is_reasoning_block,
    is_text_block,
    is_tool_call_block,
    is_tool_call_chunk_block,
)
from langgraph_agent_kit.streaming.orchestrator import BaseOrchestrator
from langgraph_agent_kit.streaming.response_handler import StreamingResponseHandler
from langgraph_agent_kit.streaming.sse import encode_sse, make_event, new_event_id, now_ms
from langgraph_agent_kit.tools.base import ToolConfig, ToolSpec
from langgraph_agent_kit.tools.decorators import with_tool_events
from langgraph_agent_kit.tools.registry import ToolRegistry


def create_sse_response(*args, **kwargs):
    """创建 SSE 响应（需要安装 fastapi 可选依赖）"""
    from langgraph_agent_kit.integrations.fastapi import create_sse_response as _create
    return _create(*args, **kwargs)


__all__ = [
    # Version
    "__version__",
    # Core
    "StreamEventType",
    "StreamEvent",
    "ChatContext",
    "DomainEmitter",
    "QueueDomainEmitter",
    # Payload TypedDict
    "MetaStartPayload",
    "TextDeltaPayload",
    "ToolStartPayload",
    "ToolEndPayload",
    "LlmCallStartPayload",
    "LlmCallEndPayload",
    "ErrorPayload",
    "MemoryExtractionStartPayload",
    "MemoryExtractionCompletePayload",
    "MemoryProfileUpdatedPayload",
    "TodoItem",
    "TodosPayload",
    "ContextSummarizedPayload",
    "ContextTrimmedPayload",
    "AgentRoutedPayload",
    "AgentHandoffPayload",
    "AgentCompletePayload",
    "SkillActivatedPayload",
    "SkillLoadedPayload",
    "ModelRetryStartPayload",
    "ModelRetryFailedPayload",
    "ModelFallbackPayload",
    "ModelCallLimitExceededPayload",
    "ContextEditedPayload",
    # Streaming
    "make_event",
    "encode_sse",
    "new_event_id",
    "now_ms",
    "BaseOrchestrator",
    "StreamingResponseHandler",
    # Content Parser
    "ParsedContent",
    "parse_content_blocks",
    "parse_content_blocks_from_chunk",
    # Content Types
    "ContentBlock",
    "TextContentBlock",
    "ReasoningContentBlock",
    "ToolCallBlock",
    "ToolCallChunk",
    "InvalidToolCall",
    "ImageContentBlock",
    "is_text_block",
    "is_reasoning_block",
    "is_tool_call_block",
    "is_tool_call_chunk_block",
    "is_image_block",
    "get_block_type",
    # Chat Models
    "ReasoningChunk",
    "BaseReasoningChatModel",
    "StandardChatModel",
    "SiliconFlowReasoningChatModel",
    "V1ChatModel",
    "is_v1_model",
    "SiliconFlowV1ChatModel",
    "create_chat_model",
    "V0_REASONING_MODEL_REGISTRY",
    "V1_REASONING_MODEL_REGISTRY",
    # Helpers
    "get_emitter_from_runtime",
    "get_emitter_from_request",
    "emit_tool_start",
    "emit_tool_end",
    # Middleware
    "MiddlewareSpec",
    "MiddlewareConfig",
    "BaseMiddleware",
    "MiddlewareRegistry",
    "Middlewares",
    # Tools
    "ToolSpec",
    "ToolConfig",
    "ToolRegistry",
    "with_tool_events",
    # Main
    "ChatStreamKit",
    # Orchestrator
    "Orchestrator",
    "OrchestratorHooks",
    "AgentRunner",
    "ContentAggregator",
    "StreamStartInfo",
    "StreamEndInfo",
    # Integrations
    "create_sse_response",
]
