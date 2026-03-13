"""intent_analyzer.py 单元测试

测试 IntentAnalyzer 的意图分析和查询拆解逻辑。
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.intent_analyzer import IntentAnalyzer, QueryPlan, SearchQuery


class TestIntentAnalyzerFallback:
    """测试 LLM 不可用时的降级行为"""

    @pytest.mark.anyio
    async def test_fallback_returns_single_query(self):
        """LLM 失败时降级为单条原始查询"""
        bad_llm = AsyncMock()
        bad_llm.ainvoke.side_effect = RuntimeError("LLM offline")

        analyzer = IntentAnalyzer(llm=bad_llm)
        plan = await analyzer.analyze("如何使用 Python 进行数据分析")

        assert plan.needs_retrieval is True
        assert len(plan.queries) == 1
        assert plan.queries[0].query == "如何使用 Python 进行数据分析"
        assert plan.queries[0].priority == 1

    @pytest.mark.anyio
    async def test_fallback_preserves_original_message(self):
        """降级模式应保留原始消息"""
        bad_llm = AsyncMock()
        bad_llm.ainvoke.side_effect = Exception("fail")

        analyzer = IntentAnalyzer(llm=bad_llm)
        plan = await analyzer.analyze("测试消息")

        assert plan.queries[0].query == "测试消息"


class TestIntentAnalyzerWithMockLLM:
    """使用模拟 LLM 测试正常分析流程"""

    @pytest.mark.anyio
    async def test_parses_multi_query_response(self):
        """应正确解析 LLM 返回的多条子查询"""
        mock_response = MagicMock()
        mock_response.content = """{
            "needs_retrieval": true,
            "reasoning": "用户问了两个问题",
            "queries": [
                {"query": "Python 数据分析", "intent": "学习", "priority": 1},
                {"query": "Pandas 使用方法", "intent": "搜索", "priority": 2}
            ]
        }"""

        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = mock_response

        analyzer = IntentAnalyzer(llm=mock_llm)
        plan = await analyzer.analyze("如何使用 Python 进行数据分析，Pandas 怎么用")

        assert plan.needs_retrieval is True
        assert len(plan.queries) == 2
        assert plan.queries[0].query == "Python 数据分析"
        assert plan.queries[0].priority == 1
        assert plan.queries[1].query == "Pandas 使用方法"

    @pytest.mark.anyio
    async def test_no_retrieval_needed(self):
        """闲聊时 needs_retrieval 应为 False"""
        mock_response = MagicMock()
        mock_response.content = """{
            "needs_retrieval": false,
            "reasoning": "这是一个打招呼",
            "queries": []
        }"""

        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = mock_response

        analyzer = IntentAnalyzer(llm=mock_llm)
        plan = await analyzer.analyze("你好")

        assert plan.needs_retrieval is False

    @pytest.mark.anyio
    async def test_handles_malformed_json(self):
        """LLM 返回格式错误时降级"""
        mock_response = MagicMock()
        mock_response.content = "这不是 JSON"

        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = mock_response

        analyzer = IntentAnalyzer(llm=mock_llm)
        plan = await analyzer.analyze("测试查询")

        assert plan.needs_retrieval is True
        assert len(plan.queries) == 1

    @pytest.mark.anyio
    async def test_history_included_in_prompt(self):
        """对话历史应被包含在 prompt 中"""
        mock_response = MagicMock()
        mock_response.content = '{"needs_retrieval": true, "reasoning": "", "queries": [{"query": "test", "priority": 1}]}'

        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = mock_response

        analyzer = IntentAnalyzer(llm=mock_llm)
        history = [
            {"role": "user", "content": "之前的问题"},
            {"role": "assistant", "content": "之前的回答"},
        ]
        await analyzer.analyze("当前问题", history=history)

        call_args = mock_llm.ainvoke.call_args[0][0]
        prompt_text = call_args[1].content
        assert "之前的问题" in prompt_text
        assert "当前问题" in prompt_text


class TestIntentAnalyzerContextType:
    """测试 context_type 解析"""

    @pytest.mark.anyio
    async def test_parses_context_type(self):
        """应正确解析 context_type 字段"""
        mock_response = MagicMock()
        mock_response.content = """{
            "needs_retrieval": true,
            "reasoning": "需要检索技能",
            "queries": [
                {"query": "Python 教程", "intent": "学习", "priority": 1, "context_type": "skill"},
                {"query": "API 文档", "intent": "查看", "priority": 2, "context_type": "document"}
            ]
        }"""

        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = mock_response

        analyzer = IntentAnalyzer(llm=mock_llm)
        plan = await analyzer.analyze("找 Python 教程和 API 文档")

        assert len(plan.queries) == 2
        assert plan.queries[0].context_type == "skill"
        assert plan.queries[1].context_type == "document"

    @pytest.mark.anyio
    async def test_empty_context_type_defaults(self):
        """context_type 为空时应为空字符串"""
        mock_response = MagicMock()
        mock_response.content = '{"needs_retrieval": true, "reasoning": "", "queries": [{"query": "test", "priority": 1}]}'

        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = mock_response

        analyzer = IntentAnalyzer(llm=mock_llm)
        plan = await analyzer.analyze("test")

        assert plan.queries[0].context_type == ""


class TestQueryPlan:
    """QueryPlan 数据结构测试"""

    def test_default_values(self):
        plan = QueryPlan()
        assert plan.needs_retrieval is True
        assert plan.queries == []
        assert plan.reasoning == ""

    def test_search_query_defaults(self):
        sq = SearchQuery(query="test")
        assert sq.priority == 3
        assert sq.intent == ""
        assert sq.context_type == ""
