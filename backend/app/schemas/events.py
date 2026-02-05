"""聊天流事件类型定义

使用 SDK 的核心类型，并扩展 Skill-Know 特有的事件类型。
"""

from langgraph_agent_kit import StreamEvent, make_event
from langgraph_agent_kit.core.events import StreamEventType


class BusinessEventType:
    """Skill-Know 业务特有的事件类型（作为常量使用）
    
    这些事件类型不在 SDK 中，是 Skill-Know 特有的。
    """

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


__all__ = ["StreamEventType", "BusinessEventType", "StreamEvent", "make_event"]
