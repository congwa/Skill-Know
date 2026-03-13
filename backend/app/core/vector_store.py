"""轻量级向量存储

使用 SQLite 存储向量嵌入，支持通过 Embedding API 生成向量并进行余弦相似度检索。
初期使用 numpy 计算相似度，后续可替换为专业向量数据库。
"""

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context import Context, ContextLevel
from app.core.logging import get_logger
from app.models.vector_index import VectorIndex

logger = get_logger("vector_store")


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """计算余弦相似度（纯 Python，无 numpy 依赖）"""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


class VectorStore:
    """向量存储

    管理向量嵌入的存储和检索，支持通过外部 Embedder 生成向量。
    """

    def __init__(self, session: AsyncSession, embedder: Any = None, backend: Any = None):
        self._session = session
        self._embedder = embedder
        if backend is None:
            from app.core.vector_backends import create_backend

            backend = create_backend("sqlite", session=session)
        self._backend = backend

    async def set_embedder(self, embedder: Any) -> None:
        self._embedder = embedder

    async def index_context(self, context: Context, level: ContextLevel = ContextLevel.ABSTRACT) -> None:
        """将 Context 索引到向量存储"""
        text = context.get_level_content(level)
        if not text:
            return

        vector = await self._embed(text)

        from app.core.vector_backends.base import VectorRecord

        record = VectorRecord(
            id="",
            uri=context.uri,
            text=text,
            vector=vector,
            context_type=context.context_type.value if context.context_type else "unknown",
            level=level.value,
            meta=context.meta,
            active_count=context.active_count,
        )
        await self._backend.upsert(record)
        logger.info("向量索引完成", uri=context.uri, level=level.value, has_vector=vector is not None)

    async def search(
        self,
        query: str,
        context_type: str | None = None,
        level: int = 0,
        limit: int = 10,
        threshold: float = 0.0,
    ) -> list[dict[str, Any]]:
        """语义检索"""
        query_vector = await self._embed(query)

        if query_vector:
            records = await self._backend.query(
                vector=query_vector,
                context_type=context_type,
                level=level,
                limit=limit,
                threshold=threshold,
            )
        else:
            records = await self._backend.text_query(
                text=query,
                context_type=context_type,
                level=level,
                limit=limit,
                threshold=threshold,
            )

        return [
            {
                "uri": r.uri,
                "context_type": r.context_type,
                "level": r.level,
                "text": r.text,
                "score": r.score,
                "meta": r.meta,
                "active_count": r.active_count,
            }
            for r in records
        ]

    async def update_activity(self, uri: str) -> None:
        """更新活跃度"""
        await self._backend.update_activity(uri)

    async def get_stale_entries(
        self,
        days: int | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """获取长期未使用的知识条目

        Args:
            days: 超过多少天未访问视为 stale
            limit: 最大返回数量

        Returns:
            stale 条目列表
        """
        from app.core.config import settings

        if days is None:
            days = settings.KNOWLEDGE_DECAY_DAYS
        if not settings.ENABLE_KNOWLEDGE_DECAY:
            return []

        from datetime import datetime, timedelta, timezone

        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        stmt = (
            select(VectorIndex)
            .where(
                VectorIndex.level == 0,
                VectorIndex.updated_at < cutoff,
            )
            .order_by(VectorIndex.active_count)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        records = result.scalars().all()

        return [
            {
                "uri": r.uri,
                "context_type": r.context_type,
                "text": r.text[:200],
                "active_count": r.active_count,
                "updated_at": r.updated_at.isoformat() if r.updated_at else None,
            }
            for r in records
        ]

    async def get_activity_stats(self) -> dict[str, Any]:
        """获取知识活跃度统计"""
        from sqlalchemy import func

        stmt = select(
            func.count(VectorIndex.id).label("total"),
            func.avg(VectorIndex.active_count).label("avg_active"),
            func.max(VectorIndex.active_count).label("max_active"),
        ).where(VectorIndex.level == 0)

        result = await self._session.execute(stmt)
        row = result.one()

        return {
            "total_entries": row.total or 0,
            "avg_active_count": round(float(row.avg_active or 0), 1),
            "max_active_count": row.max_active or 0,
        }

    async def embed(self, text: str) -> list[float] | None:
        """生成文本向量嵌入（公有接口）"""
        return await self._embed(text)

    async def _embed(self, text: str) -> list[float] | None:
        """生成文本向量嵌入（带重试）"""
        if not self._embedder:
            return None
        try:
            from app.core.retry import async_retry

            async def _do_embed() -> list[float]:
                if hasattr(self._embedder, "aembed_query"):
                    return await self._embedder.aembed_query(text)
                elif hasattr(self._embedder, "embed_query"):
                    return self._embedder.embed_query(text)
                raise ValueError("embedder has no embed_query method")

            return await async_retry(_do_embed, max_retries=2, base_delay=0.5)
        except Exception as e:
            logger.warning(f"向量嵌入生成失败: {e}")
        return None

    @staticmethod
    def _text_similarity(query: str, text: str) -> float:
        """基于关键词的文本相似度降级方案"""
        if not query or not text:
            return 0.0
        query_words = set(query.lower().split())
        text_lower = text.lower()
        matched = sum(1 for w in query_words if w in text_lower)
        return matched / max(len(query_words), 1)
