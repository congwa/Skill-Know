"""分层检索器

参考 OpenViking HierarchicalRetriever，实现基于三层内容的渐进式检索：
1. 先搜 L0 (abstract) 快速定位候选
2. 按需加载 L1 (overview) 精细筛选
3. 最终返回 L2 (detail) 完整内容

支持向量语义检索和文本降级检索。
检索结果经过 hotness_score 时间衰减 + 频次热度重排。
"""

from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.scoring import blend_scores
from app.core.vector_store import VectorStore
from app.models.skill import Skill

logger = get_logger("retriever")

HOTNESS_ALPHA = 0.2
MAX_RELATIONS = 5


@dataclass
class RetrievalResult:
    """检索结果"""
    uri: str
    skill_id: str
    name: str
    description: str
    category: str
    abstract: str
    overview: str
    content: str
    score: float
    active_count: int = 0
    matched_by: str = "semantic"
    relations: list[dict[str, str]] = field(default_factory=list)


@dataclass
class RetrievalResponse:
    """检索响应"""
    results: list[RetrievalResult] = field(default_factory=list)
    total: int = 0
    query: str = ""


class SkillRetriever:
    """分层技能检索器

    同时支持向量语义检索和关键词文本检索，可自动降级。
    """

    def __init__(
        self,
        session: AsyncSession,
        vector_store: VectorStore | None = None,
        rerank_client: Any = None,
    ):
        self._session = session
        self._vector_store = vector_store
        self._rerank_client = rerank_client

    async def retrieve(
        self,
        query: str,
        limit: int | None = None,
        threshold: float = 0.1,
        use_semantic: bool = True,
        context_type: str | None = None,
    ) -> RetrievalResponse:
        """执行分层检索

        Args:
            query: 查询文本
            limit: 最大返回数量
            threshold: 最低相似度阈值
            use_semantic: 是否使用语义检索
            context_type: 上下文类型过滤 (skill/document/knowledge)
        """
        if limit is None:
            from app.core.config import settings
            limit = settings.DEFAULT_SEARCH_LIMIT

        results: list[RetrievalResult] = []
        search_type = context_type or "skill"

        # Step 1: L0 向量搜索（宽检索，扩大候选集）
        if use_semantic and self._vector_store:
            try:
                l0_candidates = await self._vector_store.search(
                    query=query,
                    context_type=search_type,
                    level=0,
                    limit=limit * 3,
                    threshold=threshold,
                )
                if l0_candidates:
                    results = await self._enrich_results(l0_candidates, limit * 3)

                    # Step 2: L1 Rerank — 用 L1 内容精细筛选
                    if results and len(results) > limit:
                        results = await self._rerank_with_l1(query, results, limit)
                    elif results:
                        results = results[:limit]

                    if results:
                        logger.info(
                            "分层检索完成",
                            l0_count=len(l0_candidates),
                            final_count=len(results),
                        )
                        return RetrievalResponse(
                            results=results, total=len(results), query=query
                        )
            except Exception as e:
                logger.warning(f"语义检索失败，降级到文本检索: {e}")

        # Step 3: 降级到文本检索
        results = await self._text_search(query, limit)

        return RetrievalResponse(results=results, total=len(results), query=query)

    async def _enrich_results(
        self, vector_results: list[dict[str, Any]], limit: int
    ) -> list[RetrievalResult]:
        """将向量检索结果关联到完整 Skill 数据，并附带第一层知识关联"""
        results: list[RetrievalResult] = []
        skill_ids = [r["meta"].get("skill_id") for r in vector_results if r.get("meta")]
        skill_ids = [sid for sid in skill_ids if sid]

        if not skill_ids:
            return results

        stmt = select(Skill).where(Skill.id.in_(skill_ids), Skill.is_active.is_(True))
        db_result = await self._session.execute(stmt)
        skill_map = {s.id: s for s in db_result.scalars().all()}

        # 批量获取关联信息
        uri_list = [vr["uri"] for vr in vector_results if vr.get("uri")]
        relations_map = await self._load_relations(uri_list)

        for vr in vector_results:
            skill_id = vr.get("meta", {}).get("skill_id")
            skill = skill_map.get(skill_id) if skill_id else None
            if not skill:
                continue

            final_score = blend_scores(
                semantic_score=vr["score"],
                active_count=getattr(skill, "active_count", 0) or vr.get("active_count", 0),
                updated_at=getattr(skill, "updated_at", None),
                alpha=HOTNESS_ALPHA,
            )

            results.append(RetrievalResult(
                uri=vr["uri"],
                skill_id=skill.id,
                name=skill.name,
                description=skill.description or "",
                category=skill.category.value if skill.category else "",
                abstract=skill.abstract or "",
                overview=skill.overview or "",
                content=skill.content or "",
                score=round(final_score, 4),
                active_count=getattr(skill, "active_count", 0) or vr.get("active_count", 0),
                matched_by="semantic",
                relations=relations_map.get(vr["uri"], []),
            ))

        results.sort(key=lambda r: r.score, reverse=True)
        final = results[:limit]

        # 更新检索命中的 Skill 活跃度
        await self._update_activity_batch([r.uri for r in final if r.uri])

        return final

    async def _update_activity_batch(self, uris: list[str]) -> None:
        """批量更新活跃度"""
        if not uris or not self._vector_store:
            return
        try:
            for uri in uris:
                await self._vector_store.update_activity(uri)
        except Exception as e:
            logger.warning(f"批量更新活跃度失败（非阻塞）: {e}")

    async def _rerank_with_l1(
        self, query: str, candidates: list[RetrievalResult], limit: int
    ) -> list[RetrievalResult]:
        """使用 L1 (overview) 内容进行更精确的重排序。

        两种模式:
        - thinking: 使用 Rerank 模型重排（如果可用）
        - fast: 使用向量相似度重排（默认）
        """
        SCORE_PROPAGATION_ALPHA = 0.5

        # Thinking mode: 尝试用 Rerank 模型重排
        if self._rerank_client:
            try:
                documents = [
                    (c.overview or c.abstract or c.content[:500])
                    for c in candidates
                ]
                rerank_results = await self._rerank_client.rerank(
                    query=query, documents=documents, top_n=limit
                )
                if rerank_results:
                    reranked = []
                    for rr in rerank_results:
                        if rr.index < len(candidates):
                            c = candidates[rr.index]
                            c.score = round(
                                SCORE_PROPAGATION_ALPHA * rr.score
                                + (1 - SCORE_PROPAGATION_ALPHA) * c.score,
                                4,
                            )
                            c.matched_by = "semantic+rerank_model"
                            reranked.append(c)
                    return reranked
            except Exception as e:
                logger.warning(f"Rerank 模型重排失败，降级到向量重排: {e}")

        if not self._vector_store:
            return candidates[:limit]

        embed_cache: dict[str, list[float] | None] = {}

        async def _cached_embed(text: str) -> list[float] | None:
            if text not in embed_cache:
                embed_cache[text] = await self._vector_store.embed(text)
            return embed_cache[text]

        query_vector = await _cached_embed(query)
        if not query_vector:
            return candidates[:limit]

        reranked = []
        for candidate in candidates:
            l1_text = candidate.overview or candidate.abstract
            if not l1_text:
                reranked.append(candidate)
                continue

            l1_vector = await _cached_embed(l1_text)
            if l1_vector:
                from app.core.vector_store import cosine_similarity
                l1_score = cosine_similarity(query_vector, l1_vector)
                final_score = SCORE_PROPAGATION_ALPHA * l1_score + (1 - SCORE_PROPAGATION_ALPHA) * candidate.score
                candidate.score = round(final_score, 4)
                candidate.matched_by = "semantic+rerank"

            reranked.append(candidate)

        reranked.sort(key=lambda r: r.score, reverse=True)
        return reranked[:limit]

    async def _load_relations(self, uris: list[str]) -> dict[str, list[dict[str, str]]]:
        """批量加载 URI 的第一层关联，并附带关联 Skill 的 L0 摘要"""
        if not uris:
            return {}
        try:
            from app.models.context_relation import ContextRelation

            stmt = select(ContextRelation).where(ContextRelation.source_uri.in_(uris))
            result = await self._session.execute(stmt)
            relations = result.scalars().all()

            mapping: dict[str, list[dict[str, str]]] = {}
            related_uris: set[str] = set()

            for rel in relations:
                related_uris.add(rel.target_uri)

            related_abstracts: dict[str, str] = {}
            if related_uris:
                skill_uris = [u for u in related_uris if "/skills/" in u]
                if skill_uris:
                    stmt = select(Skill).where(
                        Skill.uri.in_(skill_uris),
                        Skill.is_active.is_(True),
                    )
                    result = await self._session.execute(stmt)
                    for s in result.scalars().all():
                        if s.uri:
                            related_abstracts[s.uri] = s.abstract or s.description or ""

            for rel in relations:
                items = mapping.setdefault(rel.source_uri, [])
                if len(items) >= MAX_RELATIONS:
                    continue
                items.append({
                    "target_uri": rel.target_uri,
                    "relation_type": rel.relation_type,
                    "reason": rel.reason or "",
                    "abstract": related_abstracts.get(rel.target_uri, ""),
                })
            return mapping
        except Exception as e:
            logger.warning(f"加载关联信息失败（非阻塞）: {e}")
            return {}

    async def _text_search(self, query: str, limit: int) -> list[RetrievalResult]:
        """文本降级检索（关键词匹配）"""
        stmt = select(Skill).where(
            Skill.is_active.is_(True),
            or_(
                Skill.name.ilike(f"%{query}%"),
                Skill.description.ilike(f"%{query}%"),
                Skill.abstract.ilike(f"%{query}%"),
                Skill.content.ilike(f"%{query}%"),
            ),
        ).order_by(Skill.priority).limit(limit)

        result = await self._session.execute(stmt)
        skills = result.scalars().all()

        return [
            RetrievalResult(
                uri=skill.uri or "",
                skill_id=skill.id,
                name=skill.name,
                description=skill.description or "",
                category=skill.category.value if skill.category else "",
                abstract=skill.abstract or "",
                overview=skill.overview or "",
                content=skill.content or "",
                score=self._calc_text_score(query, skill),
                active_count=0,
                matched_by="keyword",
            )
            for skill in skills
        ]

    @staticmethod
    def _calc_text_score(query: str, skill: Skill) -> float:
        """计算文本匹配分数"""
        score = 0.0
        query_lower = query.lower()
        name_lower = skill.name.lower()

        if query_lower in name_lower:
            score += 0.5
        if query_lower in (skill.description or "").lower():
            score += 0.3
        if query_lower in (skill.abstract or "").lower():
            score += 0.2
        if query_lower in (skill.content or "").lower()[:500]:
            score += 0.1

        return min(score, 1.0)
