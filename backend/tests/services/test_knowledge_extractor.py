"""knowledge_extractor.py 单元测试

测试 KnowledgeExtractor 的知识提取逻辑。
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.knowledge_extractor import (
    CandidateKnowledge,
    KnowledgeCategory,
    KnowledgeExtractor,
)


class TestKnowledgeExtractorWithMockLLM:
    """使用模拟 LLM 测试提取逻辑"""

    @pytest.mark.anyio
    async def test_extracts_faq_knowledge(self):
        """应正确提取 FAQ 类型知识"""
        mock_response = MagicMock()
        mock_response.content = """{
            "knowledge": [
                {
                    "category": "faq",
                    "title": "Python 列表推导式",
                    "abstract": "列表推导式是 Python 中创建列表的简洁语法",
                    "content": "列表推导式语法: [expr for item in iterable]",
                    "keywords": ["python", "列表推导式"]
                }
            ]
        }"""

        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = mock_response

        extractor = KnowledgeExtractor(llm=mock_llm)
        messages = [
            {"role": "user", "content": "Python 列表推导式怎么用？"},
            {"role": "assistant", "content": "列表推导式语法: [expr for item in iterable]"},
        ]
        candidates = await extractor.extract(messages, "conv-123")

        assert len(candidates) == 1
        assert candidates[0].category == KnowledgeCategory.FAQ
        assert candidates[0].title == "Python 列表推导式"
        assert candidates[0].source_conversation_id == "conv-123"

    @pytest.mark.anyio
    async def test_extracts_multiple_knowledge(self):
        """应能提取多条知识"""
        mock_response = MagicMock()
        mock_response.content = """{
            "knowledge": [
                {
                    "category": "faq",
                    "title": "知识点1",
                    "abstract": "摘要1",
                    "content": "内容1",
                    "keywords": ["k1"]
                },
                {
                    "category": "correction",
                    "title": "知识点2",
                    "abstract": "摘要2",
                    "content": "内容2",
                    "keywords": ["k2"]
                }
            ]
        }"""

        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = mock_response

        extractor = KnowledgeExtractor(llm=mock_llm)
        candidates = await extractor.extract([
            {"role": "user", "content": "问题"},
            {"role": "assistant", "content": "回答"},
        ])

        assert len(candidates) == 2
        assert candidates[1].category == KnowledgeCategory.CORRECTION

    @pytest.mark.anyio
    async def test_empty_conversation_returns_empty(self):
        """对话太短时不应提取"""
        mock_llm = AsyncMock()
        extractor = KnowledgeExtractor(llm=mock_llm)

        candidates = await extractor.extract([{"role": "user", "content": "hi"}])

        assert candidates == []
        mock_llm.ainvoke.assert_not_called()

    @pytest.mark.anyio
    async def test_no_knowledge_returns_empty(self):
        """LLM 判断无知识时返回空列表"""
        mock_response = MagicMock()
        mock_response.content = '{"knowledge": []}'

        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = mock_response

        extractor = KnowledgeExtractor(llm=mock_llm)
        candidates = await extractor.extract([
            {"role": "user", "content": "你好"},
            {"role": "assistant", "content": "你好！有什么可以帮你的？"},
        ])

        assert candidates == []


class TestKnowledgeExtractorFailure:
    """LLM 失败时的降级行为"""

    @pytest.mark.anyio
    async def test_llm_failure_returns_empty(self):
        """LLM 调用失败时应返回空列表"""
        mock_llm = AsyncMock()
        mock_llm.ainvoke.side_effect = RuntimeError("LLM offline")

        extractor = KnowledgeExtractor(llm=mock_llm)
        candidates = await extractor.extract([
            {"role": "user", "content": "问题"},
            {"role": "assistant", "content": "回答"},
        ])

        assert candidates == []

    @pytest.mark.anyio
    async def test_malformed_json_returns_empty(self):
        """LLM 返回无效 JSON 时应返回空列表"""
        mock_response = MagicMock()
        mock_response.content = "NOT JSON"

        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = mock_response

        extractor = KnowledgeExtractor(llm=mock_llm)
        candidates = await extractor.extract([
            {"role": "user", "content": "问题"},
            {"role": "assistant", "content": "回答"},
        ])

        assert candidates == []

    @pytest.mark.anyio
    async def test_skips_items_without_title(self):
        """缺少标题的知识项应被跳过"""
        mock_response = MagicMock()
        mock_response.content = """{
            "knowledge": [
                {"category": "faq", "title": "", "abstract": "", "content": "content"},
                {"category": "faq", "title": "有标题", "abstract": "", "content": "content2"}
            ]
        }"""

        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = mock_response

        extractor = KnowledgeExtractor(llm=mock_llm)
        candidates = await extractor.extract([
            {"role": "user", "content": "问题"},
            {"role": "assistant", "content": "回答"},
        ])

        assert len(candidates) == 1
        assert candidates[0].title == "有标题"


class TestCandidateKnowledge:
    """CandidateKnowledge 数据结构测试"""

    def test_default_values(self):
        ck = CandidateKnowledge(
            category=KnowledgeCategory.FAQ,
            title="test",
            abstract="",
            content="content",
        )
        assert ck.source_conversation_id == ""
        assert ck.keywords == []
