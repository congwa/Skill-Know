"""SQLite 向量后端实现

将现有 VectorStore 的 SQLite/VectorIndex 逻辑迁移为 VectorBackend 接口实现。
"""

import json

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.vector_backends.base import VectorBackend, VectorRecord

logger = get_logger("vector_backend.sqlite")


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _text_similarity(query: str, text: str) -> float:
    if not query or not text:
        return 0.0
    query_words = set(query.lower().split())
    text_lower = text.lower()
    matched = sum(1 for w in query_words if w in text_lower)
    return matched / max(len(query_words), 1)


class SQLiteVectorBackend(VectorBackend):
    """基于 SQLite 的向量后端"""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def upsert(self, record: VectorRecord) -> None:
        from app.models.vector_index import VectorIndex

        existing = await self._session.execute(
            select(VectorIndex).where(
                VectorIndex.uri == record.uri,
                VectorIndex.level == record.level,
            )
        )
        row = existing.scalar_one_or_none()

        vector_json = json.dumps(record.vector) if record.vector else None

        if row:
            row.text = record.text
            row.vector_json = vector_json
            row.vector_dim = len(record.vector) if record.vector else 0
            row.context_type = record.context_type
            row.meta = record.meta
            row.active_count = record.active_count
        else:
            row = VectorIndex(
                uri=record.uri,
                context_type=record.context_type,
                level=record.level,
                text=record.text,
                vector_json=vector_json,
                vector_dim=len(record.vector) if record.vector else 0,
                meta=record.meta,
                active_count=record.active_count,
            )
            self._session.add(row)

        await self._session.flush()

    async def query(
        self,
        vector: list[float],
        context_type: str | None = None,
        level: int = 0,
        limit: int = 10,
        threshold: float = 0.0,
    ) -> list[VectorRecord]:
        from app.models.vector_index import VectorIndex

        stmt = select(VectorIndex).where(VectorIndex.level == level)
        if context_type:
            stmt = stmt.where(VectorIndex.context_type == context_type)

        result = await self._session.execute(stmt)
        records = result.scalars().all()

        scored: list[VectorRecord] = []
        for row in records:
            if row.vector_json:
                row_vector = json.loads(row.vector_json)
                score = _cosine_similarity(vector, row_vector)
            else:
                score = 0.0

            if score >= threshold:
                scored.append(VectorRecord(
                    id=row.id,
                    uri=row.uri,
                    text=row.text,
                    vector=None,
                    context_type=row.context_type,
                    level=row.level,
                    meta=row.meta or {},
                    active_count=row.active_count,
                    score=score,
                ))

        scored.sort(key=lambda r: r.score, reverse=True)
        return scored[:limit]

    async def text_query(
        self,
        text: str,
        context_type: str | None = None,
        level: int = 0,
        limit: int = 10,
        threshold: float = 0.0,
    ) -> list[VectorRecord]:
        from app.models.vector_index import VectorIndex

        stmt = select(VectorIndex).where(VectorIndex.level == level)
        if context_type:
            stmt = stmt.where(VectorIndex.context_type == context_type)

        result = await self._session.execute(stmt)
        records = result.scalars().all()

        scored: list[VectorRecord] = []
        for row in records:
            score = _text_similarity(text, row.text)
            if score >= threshold:
                scored.append(VectorRecord(
                    id=row.id,
                    uri=row.uri,
                    text=row.text,
                    context_type=row.context_type,
                    level=row.level,
                    meta=row.meta or {},
                    active_count=row.active_count,
                    score=score,
                ))

        scored.sort(key=lambda r: r.score, reverse=True)
        return scored[:limit]

    async def delete(self, uri: str, level: int | None = None) -> int:
        from app.models.vector_index import VectorIndex

        stmt = delete(VectorIndex).where(VectorIndex.uri == uri)
        if level is not None:
            stmt = stmt.where(VectorIndex.level == level)

        result = await self._session.execute(stmt)
        await self._session.flush()
        return result.rowcount

    async def update_activity(self, uri: str) -> None:
        from app.models.vector_index import VectorIndex

        await self._session.execute(
            update(VectorIndex)
            .where(VectorIndex.uri == uri)
            .values(active_count=VectorIndex.active_count + 1)
        )
        await self._session.flush()

    async def count(self, context_type: str | None = None) -> int:
        from sqlalchemy import func

        from app.models.vector_index import VectorIndex

        stmt = select(func.count(VectorIndex.id))
        if context_type:
            stmt = stmt.where(VectorIndex.context_type == context_type)

        result = await self._session.execute(stmt)
        return result.scalar() or 0

    async def get_by_uri(self, uri: str, level: int | None = None) -> list[VectorRecord]:
        from app.models.vector_index import VectorIndex

        stmt = select(VectorIndex).where(VectorIndex.uri == uri)
        if level is not None:
            stmt = stmt.where(VectorIndex.level == level)

        result = await self._session.execute(stmt)
        rows = result.scalars().all()

        return [
            VectorRecord(
                id=row.id,
                uri=row.uri,
                text=row.text,
                context_type=row.context_type,
                level=row.level,
                meta=row.meta or {},
                active_count=row.active_count,
            )
            for row in rows
        ]
