"""聊天流事件类型定义

遵循 langchain v1 协议风格，定义统一的事件类型。
"""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel


class StreamEventType(StrEnum):
    """流事件类型"""

    # 流级别事件
    META_START = "meta.start"  # 流开始
    ASSISTANT_FINAL = "assistant.final"  # 流结束
    ERROR = "error"  # 错误

    # LLM 调用边界
    LLM_CALL_START = "llm.call.start"
    LLM_CALL_END = "llm.call.end"

    # 增量事件
    ASSISTANT_DELTA = "assistant.delta"  # 文本增量
    ASSISTANT_REASONING_DELTA = "assistant.reasoning.delta"  # 推理增量

    # 工具调用
    TOOL_START = "tool.start"
    TOOL_END = "tool.end"

    # 技能事件
    SKILL_ACTIVATED = "skill.activated"
    SKILL_LOADED = "skill.loaded"

    # 搜索事件
    SEARCH_START = "search.start"
    SEARCH_RESULT = "search.result"
    SEARCH_END = "search.end"

    # 动态工具注入事件
    INTENT_EXTRACTED = "intent.extracted"  # LLM 提取的关键词/意图
    SEARCH_QUERY_BUILT = "search.query.built"  # 构建的检索查询
    SEARCH_RESULTS_FOUND = "search.results.found"  # 检索到的 Skill 列表
    SKILL_SUMMARIES_LOADED = "skill.summaries.loaded"  # Skill 摘要加载完成
    TOOLS_REGISTERED = "tools.registered"  # 动态工具注册完成
    AGENT_THINKING = "agent.thinking"  # Agent 思考过程
    PHASE_CHANGED = "phase.changed"  # 阶段变化事件


class StreamEvent(BaseModel):
    """流事件"""

    seq: int  # 序列号
    type: str  # 事件类型
    conversation_id: str
    message_id: str
    payload: dict[str, Any] = {}


def make_event(
    seq: int,
    type: str,
    conversation_id: str,
    message_id: str,
    payload: dict[str, Any] | None = None,
) -> StreamEvent:
    """创建流事件"""
    return StreamEvent(
        seq=seq,
        type=type,
        conversation_id=conversation_id,
        message_id=message_id,
        payload=payload or {},
    )
