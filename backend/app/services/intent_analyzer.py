"""查询意图分析与重写

参考 OpenViking IntentAnalyzer，利用 LLM 将用户的自然语言输入拆解为
多个精确的检索子查询 (SearchQuery)，解决大段提问直接搜向量库效果差的问题。

核心流程:
  1. 收集对话历史 + 当前提问
  2. LLM 分析意图，判断是否需要检索
  3. 拆解为多条带优先级的 SearchQuery
  4. 调用方按 priority 并行/循环检索，合并结果
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.core.logging import get_logger

logger = get_logger("intent_analyzer")


@dataclass
class SearchQuery:
    """单条检索子查询"""
    query: str
    intent: str = ""
    priority: int = 3  # 1(最高) ~ 5(最低)
    context_type: str = ""  # skill / document / knowledge（空表示不限）


@dataclass
class QueryPlan:
    """意图分析生成的查询计划"""
    needs_retrieval: bool = True
    queries: list[SearchQuery] = field(default_factory=list)
    reasoning: str = ""
    session_context: str = ""


INTENT_ANALYSIS_PROMPT = """你是 Skill-Know 智能知识库的查询意图分析器。
你的任务是分析用户在对话中的真实意图，然后将其拆解为一组精确的检索查询。

## 输入信息
- 对话摘要: 之前的对话背景（可能为空）
- 近期消息: 最近几轮对话
- 当前消息: 用户最新的输入

## 输出要求
输出 JSON 格式:
```json
{
  "needs_retrieval": true,
  "reasoning": "简要分析用户意图和拆解逻辑",
  "queries": [
    {
      "query": "精确的检索关键词或短语",
      "intent": "该子查询的目的",
      "priority": 1,
      "context_type": "skill"
    }
  ]
}
```

## 规则
1. `needs_retrieval`: 如果是闲聊/打招呼/不需要知识库的问题，设为 false
2. `queries`: 将复杂问题拆解为 1-4 条独立的精确检索子查询
   - 每条查询应该是简短精确的关键词或短语（不要用完整句子）
   - priority: 1=核心关键信息, 2=重要补充, 3=扩展参考
   - context_type: "skill"（技能知识）, "document"（原始文档）, "knowledge"（提取的知识点）, ""（不限）
3. 如果问题包含多个子话题（如 "X怎么用，还有Y和Z的区别"），拆为独立子查询
4. 如果问题很简单直接，只需一条查询
5. 保留原始语言（中文问题用中文关键词，英文问题用英文关键词）

只输出 JSON，不要其他内容。"""


class IntentAnalyzer:
    """查询意图分析器

    利用 LLM 和对话上下文将用户输入拆解为多条精确检索子查询。
    """

    def __init__(self, llm: Any, max_recent_messages: int = 5):
        self._llm = llm
        self._max_recent = max_recent_messages

    async def analyze(
        self,
        current_message: str,
        history: list[dict[str, str]] | None = None,
        summary: str = "",
    ) -> QueryPlan:
        """分析用户意图并生成查询计划。

        Args:
            current_message: 当前用户消息
            history: 近期消息列表 [{"role": "user"/"assistant", "content": "..."}]
            summary: 对话摘要（可选）

        Returns:
            QueryPlan 包含拆解后的子查询列表
        """
        prompt = self._build_prompt(current_message, history, summary)

        try:
            from app.prompts import render_prompt

            system_prompt = render_prompt("retrieval.intent_analysis", {
                "summary": summary or "无",
                "recent_messages": self._format_history(history),
                "current_message": current_message,
            })
            if not system_prompt:
                system_prompt = INTENT_ANALYSIS_PROMPT
            response = await self._llm.ainvoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=prompt),
            ])
            parsed = self._parse_response(str(response.content))
        except Exception as e:
            logger.warning(f"LLM 意图分析失败，降级到基础拆解: {e}")
            parsed = None

        if parsed is None:
            return self._fallback_plan(current_message)

        queries = [
            SearchQuery(
                query=q.get("query", ""),
                intent=q.get("intent", ""),
                priority=q.get("priority", 3),
                context_type=q.get("context_type", ""),
            )
            for q in parsed.get("queries", [])
            if q.get("query")
        ]

        plan = QueryPlan(
            needs_retrieval=parsed.get("needs_retrieval", True),
            queries=queries or [SearchQuery(query=current_message, priority=1)],
            reasoning=parsed.get("reasoning", ""),
            session_context=self._build_session_context(summary, current_message),
        )

        logger.info(
            "意图分析完成",
            needs_retrieval=plan.needs_retrieval,
            query_count=len(plan.queries),
            reasoning=plan.reasoning[:120],
        )
        for i, q in enumerate(plan.queries):
            logger.info(f"  [{i+1}] priority={q.priority} query=\"{q.query}\"")

        return plan

    def _format_history(self, history: list[dict[str, str]] | None) -> str:
        if not history:
            return "无"
        recent = history[-self._max_recent:]
        return "\n".join(f"[{m['role']}]: {m['content']}" for m in recent if m.get("content"))

    def _build_prompt(
        self,
        current_message: str,
        history: list[dict[str, str]] | None,
        summary: str,
    ) -> str:
        parts: list[str] = []

        parts.append(f"## 对话摘要\n{summary or '无'}")

        if history:
            recent = history[-self._max_recent:]
            lines = [f"[{m['role']}]: {m['content']}" for m in recent if m.get("content")]
            parts.append("## 近期消息\n" + "\n".join(lines))
        else:
            parts.append("## 近期消息\n无")

        parts.append(f"## 当前消息\n{current_message}")

        return "\n\n".join(parts)

    @staticmethod
    def _parse_response(content: str) -> dict[str, Any] | None:
        content = content.strip()
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        return None

    @staticmethod
    def _fallback_plan(message: str) -> QueryPlan:
        """LLM 不可用时的降级策略：直接将原始消息作为单条查询。"""
        return QueryPlan(
            needs_retrieval=True,
            queries=[SearchQuery(query=message, intent="direct_search", priority=1)],
            reasoning="fallback: LLM unavailable",
            session_context=message[:100],
        )

    @staticmethod
    def _build_session_context(summary: str, current_message: str) -> str:
        parts = []
        if summary:
            parts.append(f"摘要: {summary[:100]}")
        if current_message:
            parts.append(f"当前: {current_message[:100]}")
        return " | ".join(parts) if parts else ""
