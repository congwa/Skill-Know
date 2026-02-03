"""查询构建器

将意图识别结果转换为搜索查询条件。
"""

import re
from dataclasses import dataclass, field
from typing import Any

from app.core.logging import get_logger
from app.services.skill_search.intent import IntentResult

logger = get_logger("skill_search.query")


@dataclass
class QueryCondition:
    """查询条件"""
    type: str  # keyword | category | tag | regex
    pattern: str
    weight: float = 1.0
    field: str = "all"  # all | name | description | content | keywords


@dataclass
class SearchQuery:
    """搜索查询"""
    conditions: list[QueryCondition] = field(default_factory=list)
    intent: str = "search"
    limit: int = 10
    min_score: float = 0.3


class QueryBuilder:
    """查询构建器"""

    # 常见技术术语的同义词映射
    SYNONYMS = {
        "装饰器": ["decorator", "wrapper"],
        "decorator": ["装饰器", "wrapper"],
        "函数": ["function", "func", "方法"],
        "function": ["函数", "func", "方法"],
        "类": ["class", "类型"],
        "class": ["类", "类型"],
        "接口": ["interface", "api"],
        "interface": ["接口", "api"],
        "异步": ["async", "asyncio", "协程"],
        "async": ["异步", "asyncio", "协程"],
        "数据库": ["database", "db", "sql"],
        "database": ["数据库", "db", "sql"],
        "框架": ["framework"],
        "framework": ["框架"],
    }

    # 意图到分类的映射
    INTENT_CATEGORY_MAP = {
        "learn": ["教程", "入门", "基础"],
        "search": [],
        "compare": ["对比", "比较"],
        "ask": ["问答", "FAQ"],
        "create": ["模板", "示例", "代码"],
    }

    def build(self, intent_result: IntentResult) -> SearchQuery:
        """构建搜索查询

        Args:
            intent_result: 意图识别结果

        Returns:
            SearchQuery
        """
        query = SearchQuery(intent=intent_result.intent)
        conditions = []

        # 1. 从关键词构建条件
        for keyword in intent_result.keywords:
            # 主关键词
            conditions.append(QueryCondition(
                type="keyword",
                pattern=keyword,
                weight=1.0,
                field="all",
            ))

            # 添加同义词
            synonyms = self._get_synonyms(keyword)
            for syn in synonyms:
                conditions.append(QueryCondition(
                    type="keyword",
                    pattern=syn,
                    weight=0.8,
                    field="all",
                ))

        # 2. 从实体构建条件
        for entity in intent_result.entities:
            entity_type = entity.get("type", "")
            entity_value = entity.get("value", "")

            if entity_type == "language":
                conditions.append(QueryCondition(
                    type="category",
                    pattern=entity_value,
                    weight=1.2,
                    field="category",
                ))
            elif entity_type in ["framework", "tool"]:
                conditions.append(QueryCondition(
                    type="keyword",
                    pattern=entity_value,
                    weight=1.1,
                    field="name",
                ))

        # 3. 根据意图添加分类条件
        intent_categories = self.INTENT_CATEGORY_MAP.get(intent_result.intent, [])
        for cat in intent_categories:
            conditions.append(QueryCondition(
                type="tag",
                pattern=cat,
                weight=0.5,
                field="tags",
            ))

        # 4. 构建正则表达式条件（用于 grep-like 搜索）
        if intent_result.keywords:
            # 构建 OR 正则
            regex_pattern = "|".join(
                re.escape(kw) for kw in intent_result.keywords
            )
            conditions.append(QueryCondition(
                type="regex",
                pattern=regex_pattern,
                weight=0.9,
                field="content",
            ))

        query.conditions = conditions

        logger.info(
            "查询构建完成",
            condition_count=len(conditions),
            intent=intent_result.intent,
        )

        return query

    def _get_synonyms(self, keyword: str) -> list[str]:
        """获取同义词"""
        keyword_lower = keyword.lower()
        synonyms = []

        for key, values in self.SYNONYMS.items():
            if key.lower() == keyword_lower:
                synonyms.extend(values)
            elif keyword_lower in [v.lower() for v in values]:
                synonyms.append(key)

        return list(set(synonyms))[:3]  # 最多 3 个同义词

    def to_grep_pattern(self, query: SearchQuery) -> str:
        """将查询转换为 grep 模式

        Args:
            query: 搜索查询

        Returns:
            grep 兼容的正则表达式
        """
        patterns = []

        for cond in query.conditions:
            if cond.type in ["keyword", "regex"]:
                patterns.append(cond.pattern)

        if not patterns:
            return ".*"

        # 构建 OR 模式
        return "|".join(f"({p})" for p in patterns)
