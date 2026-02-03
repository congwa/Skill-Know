"""日志中间件

负责记录每次 LLM 调用的完整输入输出。
与 embedease-ai 保持一致。
"""

import time
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

from langchain.agents.middleware.types import AgentMiddleware, ModelRequest, ModelResponse
from langchain_core.messages import BaseMessage

from app.core.logging import get_logger

logger = get_logger("middleware.llm")


def _truncate_text(value: Any, *, limit: int = 500) -> str | None:
    if value is None:
        return None
    text = str(value)
    if len(text) <= limit:
        return text
    return text[:limit] + "..."


def _summarize_tool_calls(tool_calls: Any) -> dict[str, Any] | None:
    """将 tool_calls 压缩成可读摘要"""
    if not tool_calls:
        return None

    if isinstance(tool_calls, list):
        items: list[dict[str, Any]] = []
        for tc in tool_calls[:10]:
            item: dict[str, Any] = {}
            if isinstance(tc, dict):
                item["id"] = str(tc.get("id")) if tc.get("id") is not None else None
                item["name"] = str(tc.get("name")) if tc.get("name") is not None else None
                args = tc.get("args")
                if isinstance(args, dict):
                    item["args_keys"] = sorted(list(args.keys()))[:20]
            elif hasattr(tc, "id") or hasattr(tc, "name"):
                item["id"] = str(getattr(tc, "id", None))
                item["name"] = str(getattr(tc, "name", None))
                args = getattr(tc, "args", None)
                if isinstance(args, dict):
                    item["args_keys"] = sorted(list(args.keys()))[:20]
            items.append(item)
        return {"count": len(tool_calls), "items": items}
    return {"type": str(type(tool_calls).__name__)}


def _serialize_message(msg: BaseMessage) -> dict[str, Any]:
    """序列化消息用于日志"""
    content = getattr(msg, "content", None)
    content_text = content if isinstance(content, str) else str(content) if content is not None else ""
    
    return {
        "type": type(msg).__name__,
        "content": _truncate_text(content, limit=1200),
        "content_length": len(content_text) if content_text else 0,
        "tool_calls": _summarize_tool_calls(getattr(msg, "tool_calls", None)),
    }


def _serialize_messages(messages: list) -> list[dict[str, Any]]:
    """序列化消息列表"""
    return [_serialize_message(m) for m in messages if isinstance(m, BaseMessage)]


def _serialize_tool(tool: Any) -> dict[str, Any]:
    """序列化工具信息"""
    if isinstance(tool, dict):
        name = tool.get("name") or tool.get("function", {}).get("name") or tool.get("id")
        return {"type": "provider_dict", "name": name}
    return {
        "type": type(tool).__name__,
        "name": getattr(tool, "name", None),
        "description": _truncate_text(getattr(tool, "description", None), limit=200),
    }


class LoggingMiddleware(AgentMiddleware):
    """日志中间件
    
    记录每次 LLM 调用的输入输出、工具列表、调用耗时等信息。
    同时发送 llm.call.start 和 llm.call.end 事件到前端。
    """
    
    def __init__(self, emitter: Any = None):
        super().__init__()
        self._emitter = emitter

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelResponse:
        """记录 LLM 调用的输入输出"""
        from app.schemas.events import StreamEventType
        
        start_time = time.time()
        llm_call_id = uuid.uuid4().hex

        # 构建有效消息列表
        effective_messages: list[Any] = list(request.messages)
        if request.system_message is not None:
            effective_messages = [request.system_message, *effective_messages]

        # 记录请求信息
        request_data = {
            "llm_call_id": llm_call_id,
            "message_count": len(effective_messages),
            "tools": [_serialize_tool(t) for t in request.tools],
            "tool_count": len(request.tools),
            "tool_choice": request.tool_choice,
        }

        logger.info("🚀 LLM 调用开始", **request_data)
        
        # 发送 llm.call.start 事件到前端
        if self._emitter and hasattr(self._emitter, "aemit"):
            await self._emitter.aemit(
                StreamEventType.LLM_CALL_START.value,
                {
                    "llm_call_id": llm_call_id,
                    "message_count": len(effective_messages),
                },
            )

        try:
            response = await handler(request)
            elapsed_ms = int((time.time() - start_time) * 1000)

            # 记录响应信息
            response_data = {
                "llm_call_id": llm_call_id,
                "messages": _serialize_messages(response.result),
                "message_count": len(response.result),
                "elapsed_ms": elapsed_ms,
            }

            logger.info("✅ LLM 调用完成", **response_data)
            
            # 发送 llm.call.end 事件到前端
            if self._emitter and hasattr(self._emitter, "aemit"):
                await self._emitter.aemit(
                    StreamEventType.LLM_CALL_END.value,
                    {
                        "llm_call_id": llm_call_id,
                        "elapsed_ms": elapsed_ms,
                    },
                )
            
            return response

        except Exception as e:
            elapsed_ms = int((time.time() - start_time) * 1000)
            logger.error(
                "❌ LLM 调用失败",
                llm_call_id=llm_call_id,
                error=str(e),
                error_type=type(e).__name__,
                elapsed_ms=elapsed_ms,
                exc_info=True,
            )
            
            # 发送错误事件
            if self._emitter and hasattr(self._emitter, "aemit"):
                await self._emitter.aemit(
                    StreamEventType.LLM_CALL_END.value,
                    {
                        "llm_call_id": llm_call_id,
                        "elapsed_ms": elapsed_ms,
                        "error": str(e),
                    },
                )
            
            raise
