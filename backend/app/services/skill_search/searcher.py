"""Skill 搜索器

执行 grep-like 搜索，找出匹配的 Skill。
"""

import re
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.skill import Skill
from app.services.skill_search.query import SearchQuery, QueryCondition

logger = get_logger("skill_search.searcher")


@dataclass
class SkillMatch:
    """Skill 匹配结果"""
    skill_id: str
    name: str
    description: str
    category: str
    score: float
    matched_by: str  # keyword | regex | category | semantic
    matched_keywords: list[str] = field(default_factory=list)
    preview: str = ""  # content 前 200 字


@dataclass
class SearchResult:
    """搜索结果"""
    matches: list[SkillMatch] = field(default_factory=list)
    total_count: int = 0
    query_time_ms: int = 0


class SkillSearcher:
    """Skill 搜索器"""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def search(self, query: SearchQuery) -> SearchResult:
        """执行搜索

        Args:
            query: 搜索查询

        Returns:
            SearchResult
        """
        import time
        start_time = time.time()

        # 获取所有启用的 Skill
        stmt = select(Skill).where(Skill.is_active == True)
        result = await self._session.execute(stmt)
        skills = result.scalars().all()

        matches = []

        for skill in skills:
            match_result = self._match_skill(skill, query)
            if match_result and match_result.score >= query.min_score:
                matches.append(match_result)

        # 按分数排序
        matches.sort(key=lambda m: m.score, reverse=True)

        # 限制数量
        matches = matches[:query.limit]

        elapsed_ms = int((time.time() - start_time) * 1000)

        logger.info(
            "Skill 搜索完成",
            total_skills=len(skills),
            matched_count=len(matches),
            query_time_ms=elapsed_ms,
        )

        return SearchResult(
            matches=matches,
            total_count=len(matches),
            query_time_ms=elapsed_ms,
        )

    def _match_skill(self, skill: Skill, query: SearchQuery) -> SkillMatch | None:
        """匹配单个 Skill

        Args:
            skill: Skill 对象
            query: 搜索查询

        Returns:
            SkillMatch 或 None
        """
        total_score = 0.0
        matched_keywords = []
        matched_by = "keyword"
        max_weight = 0.0

        # 构建搜索文本
        search_texts = {
            "name": skill.name.lower(),
            "description": (skill.description or "").lower(),
            "content": (skill.content or "").lower()[:1000],  # 只搜索前 1000 字
            "keywords": " ".join(skill.trigger_keywords or []).lower(),
            "category": skill.category.value.lower() if skill.category else "",
            "all": f"{skill.name} {skill.description or ''} {skill.content or ''}".lower(),
        }

        for cond in query.conditions:
            field_text = search_texts.get(cond.field, search_texts["all"])
            matched = False
            
            if cond.type == "keyword":
                # 关键词匹配
                pattern = cond.pattern.lower()
                if pattern in field_text:
                    matched = True
                    matched_keywords.append(cond.pattern)

            elif cond.type == "regex":
                # 正则匹配
                try:
                    if re.search(cond.pattern, field_text, re.IGNORECASE):
                        matched = True
                        matched_by = "regex"
                except re.error:
                    pass

            elif cond.type == "category":
                # 分类匹配
                if cond.pattern.lower() in search_texts["category"]:
                    matched = True
                    matched_by = "category"

            elif cond.type == "tag":
                # 标签匹配（在 content 中搜索）
                if cond.pattern.lower() in field_text:
                    matched = True

            if matched:
                total_score += cond.weight
                if cond.weight > max_weight:
                    max_weight = cond.weight

        if total_score == 0:
            return None

        # 归一化分数 (0-1)
        normalized_score = min(total_score / max(len(query.conditions), 1), 1.0)

        # 名称匹配加权
        if any(kw.lower() in search_texts["name"] for kw in matched_keywords):
            normalized_score *= 1.2

        # 限制在 0-1 范围
        normalized_score = min(normalized_score, 1.0)

        return SkillMatch(
            skill_id=skill.id,
            name=skill.name,
            description=skill.description or "",
            category=skill.category.value if skill.category else "",
            score=round(normalized_score, 3),
            matched_by=matched_by,
            matched_keywords=matched_keywords,
            preview=(skill.content or "")[:200],
        )

    async def search_by_keywords(
        self,
        keywords: list[str],
        limit: int = 10,
    ) -> list[SkillMatch]:
        """简化的关键词搜索

        Args:
            keywords: 关键词列表
            limit: 结果数量限制

        Returns:
            SkillMatch 列表
        """
        query = SearchQuery(
            conditions=[
                QueryCondition(
                    type="keyword",
                    pattern=kw,
                    weight=1.0,
                    field="all",
                )
                for kw in keywords
            ],
            limit=limit,
        )

        result = await self.search(query)
        return result.matches
