"""知识关联模型

存储 Context 之间的双向关联关系，实现知识图谱式溯源。
例如：Skill 从 Document 派生、Skill 依赖另一个 Skill。
"""

import uuid

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class ContextRelation(Base, TimestampMixin):
    """知识关联表

    记录两个 Context (通过 URI 标识) 之间的有向关系。

    relation_type 约定:
        - derived_from  : 来源（如 Skill 由 Document 转换而来）
        - depends_on    : 依赖（如 Skill A 依赖 Skill B 的知识）
        - related_to    : 相关（弱关联，由检索或 LLM 自动发现）
        - merged_from   : 合并来源（去重合并时记录）
    """

    __tablename__ = "context_relations"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    source_uri: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    target_uri: Mapped[str] = mapped_column(String(500), nullable=False, index=True)

    relation_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    reason: Mapped[str] = mapped_column(Text, default="")

    def __repr__(self) -> str:
        return f"<ContextRelation {self.source_uri} --[{self.relation_type}]--> {self.target_uri}>"
