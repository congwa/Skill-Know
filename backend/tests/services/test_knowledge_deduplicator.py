"""knowledge_deduplicator.py 单元测试

测试 KnowledgeDeduplicator 的去重决策逻辑。
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.knowledge_deduplicator import (
    DedupDecision,
    DedupResult,
    KnowledgeDeduplicator,
)


class TestDeduplicatorNoSimilar:
    """无相似知识时的行为"""

    @pytest.mark.anyio
    async def test_no_similar_returns_create(self):
        """无相似知识时应直接创建"""
        mock_llm = AsyncMock()
        mock_vector_store = AsyncMock()
        mock_vector_store.search.return_value = []

        dedup = KnowledgeDeduplicator(llm=mock_llm, vector_store=mock_vector_store)
        result = await dedup.check(
            title="新技能", abstract="一个全新的技能", content="详细内容"
        )

        assert result.decision == DedupDecision.CREATE
        assert result.merge_target_uri is None
        mock_llm.ainvoke.assert_not_called()


class TestDeduplicatorWithSimilar:
    """有相似知识时的 LLM 决策测试"""

    @pytest.mark.anyio
    async def test_skip_decision(self):
        """LLM 判断为重复时应跳过"""
        mock_response = MagicMock()
        mock_response.content = '{"decision": "skip", "reason": "完全重复"}'

        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = mock_response

        mock_vector_store = AsyncMock()
        mock_vector_store.search.return_value = [
            {"uri": "sk://skills/existing", "score": 0.95, "text": "摘要"}
        ]

        dedup = KnowledgeDeduplicator(llm=mock_llm, vector_store=mock_vector_store)
        result = await dedup.check(
            title="已有技能", abstract="已有摘要", content="已有内容"
        )

        assert result.decision == DedupDecision.SKIP
        assert result.merge_target_uri is None

    @pytest.mark.anyio
    async def test_merge_decision(self):
        """LLM 判断需合并时应返回合并目标"""
        mock_response = MagicMock()
        mock_response.content = """{
            "decision": "merge",
            "reason": "新增信息可合并",
            "merge_target_index": 1,
            "merged_content": "合并后的完整内容"
        }"""

        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = mock_response

        mock_vector_store = AsyncMock()
        mock_vector_store.search.return_value = [
            {"uri": "sk://skills/target", "score": 0.75, "text": "旧摘要"}
        ]

        dedup = KnowledgeDeduplicator(llm=mock_llm, vector_store=mock_vector_store)
        result = await dedup.check(
            title="补充技能", abstract="补充摘要", content="补充内容"
        )

        assert result.decision == DedupDecision.MERGE
        assert result.merge_target_uri == "sk://skills/target"
        assert result.merged_content == "合并后的完整内容"

    @pytest.mark.anyio
    async def test_create_decision_with_similar(self):
        """即使有相似知识，LLM 判断为独立时仍应创建"""
        mock_response = MagicMock()
        mock_response.content = '{"decision": "create", "reason": "虽有相似但包含独特信息"}'

        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = mock_response

        mock_vector_store = AsyncMock()
        mock_vector_store.search.return_value = [
            {"uri": "sk://skills/different", "score": 0.5, "text": "不同摘要"}
        ]

        dedup = KnowledgeDeduplicator(llm=mock_llm, vector_store=mock_vector_store)
        result = await dedup.check(
            title="新技能", abstract="新摘要", content="新内容"
        )

        assert result.decision == DedupDecision.CREATE


class TestDeduplicatorLLMFailure:
    """LLM 失败时的降级行为"""

    @pytest.mark.anyio
    async def test_llm_failure_defaults_to_create(self):
        """LLM 调用失败时应默认创建"""
        mock_llm = AsyncMock()
        mock_llm.ainvoke.side_effect = RuntimeError("LLM offline")

        mock_vector_store = AsyncMock()
        mock_vector_store.search.return_value = [
            {"uri": "sk://skills/x", "score": 0.9, "text": "text"}
        ]

        dedup = KnowledgeDeduplicator(llm=mock_llm, vector_store=mock_vector_store)
        result = await dedup.check(
            title="test", abstract="test", content="test"
        )

        assert result.decision == DedupDecision.CREATE

    @pytest.mark.anyio
    async def test_malformed_json_defaults_to_create(self):
        """LLM 返回无效 JSON 时应默认创建"""
        mock_response = MagicMock()
        mock_response.content = "NOT JSON AT ALL"

        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = mock_response

        mock_vector_store = AsyncMock()
        mock_vector_store.search.return_value = [
            {"uri": "sk://skills/x", "score": 0.8, "text": "text"}
        ]

        dedup = KnowledgeDeduplicator(llm=mock_llm, vector_store=mock_vector_store)
        result = await dedup.check(
            title="test", abstract="test", content="test"
        )

        assert result.decision == DedupDecision.CREATE


class TestDedupResult:
    """DedupResult 数据结构测试"""

    def test_default_values(self):
        result = DedupResult(decision=DedupDecision.CREATE)
        assert result.reason == ""
        assert result.merge_target_uri is None
        assert result.merged_content is None
