"""向量索引模型

存储知识实体的向量嵌入，支持语义检索。
"""

import uuid

from sqlalchemy import Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class VectorIndex(Base, TimestampMixin):
    """向量索引表

    存储 Context 的向量嵌入和元数据，用于语义检索。
    每个 URI 可以有多条记录（L0/L1/L2 各一条），通过 (uri, level) 复合唯一键区分。
    """

    __tablename__ = "vector_index"
    __table_args__ = (
        UniqueConstraint("uri", "level", name="uq_vector_index_uri_level"),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    uri: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    context_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    level: Mapped[int] = mapped_column(Integer, default=0, index=True)

    text: Mapped[str] = mapped_column(Text, nullable=False)
    vector_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    vector_dim: Mapped[int] = mapped_column(Integer, default=0)

    meta: Mapped[dict] = mapped_column(JSON, default=dict)
    active_count: Mapped[int] = mapped_column(Integer, default=0)

    def __repr__(self) -> str:
        return f"<VectorIndex {self.uri} L{self.level}>"
