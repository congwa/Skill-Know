"""意图识别服务

从用户输入中提取关键词和意图。
"""

import json
import re
from dataclasses import dataclass, field
from typing import Any

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from app.core.logging import get_logger

logger = get_logger("skill_search.intent")


@dataclass
class IntentResult:
    """意图识别结果"""
    keywords: list[str] = field(default_factory=list)
    intent: str = "search"  # learn | search | compare | ask | create
    entities: list[dict[str, Any]] = field(default_factory=list)
    raw_query: str = ""


INTENT_EXTRACTION_PROMPT = """你是一个意图识别助手。分析用户输入，提取关键词和意图。

## 输出格式
请输出 JSON 格式：
```json
{
  "keywords": ["关键词1", "关键词2"],
  "intent": "search",
  "entities": [{"type": "language", "value": "Python"}]
}
```

## 意图类型
- learn: 学习某个概念或技术
- search: 搜索特定信息
- compare: 比较多个选项
- ask: 提问具体问题
- create: 创建或生成内容

## 实体类型
- language: 编程语言
- framework: 框架
- tool: 工具
- concept: 概念
- topic: 主题

## 关键词提取规则
1. 提取核心名词和技术术语
2. 保留原文关键词，不要翻译
3. 同时提取中英文关键词
4. 移除停用词（的、了、是、等）

只输出 JSON，不要其他内容。"""


class IntentExtractor:
    """意图提取器"""

    def __init__(self, llm: ChatOpenAI | None = None):
        self._llm = llm
        self._use_llm = llm is not None

    async def extract(self, user_message: str) -> IntentResult:
        """提取意图和关键词

        Args:
            user_message: 用户消息

        Returns:
            IntentResult
        """
        result = IntentResult(raw_query=user_message)

        # 基础关键词提取（无需 LLM）
        result.keywords = self._extract_keywords_basic(user_message)
        result.intent = self._detect_intent_basic(user_message)

        # 如果有 LLM，使用 LLM 增强
        if self._use_llm and self._llm:
            try:
                llm_result = await self._extract_with_llm(user_message)
                if llm_result:
                    # 合并关键词（去重）
                    all_keywords = list(dict.fromkeys(
                        result.keywords + llm_result.get("keywords", [])
                    ))
                    result.keywords = all_keywords
                    result.intent = llm_result.get("intent", result.intent)
                    result.entities = llm_result.get("entities", [])
            except Exception as e:
                logger.warning(f"LLM 意图提取失败，使用基础提取: {e}")

        logger.info(
            "意图提取完成",
            keywords=result.keywords,
            intent=result.intent,
            entities=result.entities,
        )

        return result

    def _extract_keywords_basic(self, text: str) -> list[str]:
        """基础关键词提取（无需 LLM）"""
        # 移除标点符号
        text = re.sub(r'[^\w\s\u4e00-\u9fff]', ' ', text)

        # 停用词
        stopwords = {
            '的', '了', '是', '在', '我', '有', '和', '就', '不', '人', '都',
            '一', '个', '上', '也', '很', '到', '说', '要', '去', '你', '会',
            '着', '没有', '看', '好', '自己', '这', '那', '什么', '怎么', '如何',
            'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
            'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
            'would', 'could', 'should', 'may', 'might', 'must', 'shall',
            'can', 'need', 'dare', 'ought', 'used', 'to', 'of', 'in', 'for',
            'on', 'with', 'at', 'by', 'from', 'about', 'as', 'into', 'through',
            'during', 'before', 'after', 'above', 'below', 'between', 'under',
            'again', 'further', 'then', 'once', 'here', 'there', 'when',
            'where', 'why', 'how', 'all', 'each', 'few', 'more', 'most',
            'other', 'some', 'such', 'no', 'nor', 'not', 'only', 'own',
            'same', 'so', 'than', 'too', 'very', 's', 't', 'just', 'don',
            'now', 'i', 'me', 'my', 'myself', 'we', 'our', 'ours', 'you',
            'your', 'he', 'him', 'his', 'she', 'her', 'it', 'its', 'they',
            'them', 'their', 'what', 'which', 'who', 'whom', 'this', 'that',
            '想', '请', '帮', '告诉', '介绍', '了解', '学习', '使用',
        }

        # 分词
        words = text.split()

        # 过滤
        keywords = []
        for word in words:
            word = word.strip()
            if len(word) < 2:
                continue
            if word.lower() in stopwords:
                continue
            keywords.append(word)

        return keywords[:10]  # 最多 10 个关键词

    def _detect_intent_basic(self, text: str) -> str:
        """基础意图检测"""
        text_lower = text.lower()

        # 学习意图
        if any(kw in text_lower for kw in ['学习', '了解', '入门', 'learn', '教程', '怎么用']):
            return "learn"

        # 比较意图
        if any(kw in text_lower for kw in ['比较', '对比', 'vs', '区别', '哪个好', 'compare']):
            return "compare"

        # 创建意图
        if any(kw in text_lower for kw in ['创建', '生成', '写', '实现', 'create', 'build', 'make']):
            return "create"

        # 提问意图
        if any(kw in text_lower for kw in ['为什么', '怎么', '如何', 'why', 'how', 'what']):
            return "ask"

        # 默认搜索
        return "search"

    async def _extract_with_llm(self, user_message: str) -> dict[str, Any] | None:
        """使用 LLM 提取意图"""
        if not self._llm:
            return None

        messages = [
            SystemMessage(content=INTENT_EXTRACTION_PROMPT),
            HumanMessage(content=user_message),
        ]

        response = await self._llm.ainvoke(messages)
        content = str(response.content).strip()

        # 提取 JSON
        json_match = re.search(r'\{[^{}]*\}', content, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

        return None
