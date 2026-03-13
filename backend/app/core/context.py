"""统一上下文模型

参考 OpenViking Context 机制，为 Skill-Know 提供 URI 标识体系和三层内容模型 (L0/L1/L2)。

URI 协议: sk://
  - sk://skills/{name}         — 技能
  - sk://documents/{id}        — 文档
  - sk://knowledge/{id}        — 知识条目
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4


class ContextType(str, Enum):
    SKILL = "skill"
    DOCUMENT = "document"
    KNOWLEDGE = "knowledge"


class ContextLevel(int, Enum):
    ABSTRACT = 0   # L0: 简短摘要 (~100 tokens)
    OVERVIEW = 1   # L1: 结构化概览 (~2k tokens)
    DETAIL = 2     # L2: 完整内容


URI_PREFIX = "sk://"


class Context:
    """统一上下文对象

    每个知识实体（Skill/Document/Knowledge）都有对应的 Context，
    通过 URI 唯一标识，支持 L0/L1/L2 三层内容按需加载。
    """

    def __init__(
        self,
        uri: str,
        parent_uri: str | None = None,
        context_type: ContextType | None = None,
        abstract: str = "",
        overview: str = "",
        content: str = "",
        meta: dict[str, Any] | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
        active_count: int = 0,
        vectorize_text: str = "",
        id: str | None = None,
        relations: list[dict[str, str]] | None = None,
    ):
        self.id = id or str(uuid4())
        self.uri = uri
        self.parent_uri = parent_uri
        self.context_type = context_type or self._derive_type()
        self.abstract = abstract
        self.overview = overview
        self.content = content
        self.meta = meta or {}
        self.created_at = created_at or datetime.now(timezone.utc)
        self.updated_at = updated_at or self.created_at
        self.active_count = active_count
        self.vectorize_text = vectorize_text or abstract
        self.vector: list[float] | None = None
        self.relations: list[dict[str, str]] = relations or []

    def _derive_type(self) -> ContextType:
        if "/skills" in self.uri:
            return ContextType.SKILL
        elif "/documents" in self.uri:
            return ContextType.DOCUMENT
        return ContextType.KNOWLEDGE

    def get_level_content(self, level: ContextLevel) -> str:
        """按层级获取内容"""
        if level == ContextLevel.ABSTRACT:
            return self.abstract
        elif level == ContextLevel.OVERVIEW:
            return self.overview or self.abstract
        return self.content or self.overview or self.abstract

    def update_activity(self) -> None:
        self.active_count += 1
        self.updated_at = datetime.now(timezone.utc)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "uri": self.uri,
            "parent_uri": self.parent_uri,
            "context_type": self.context_type.value if self.context_type else None,
            "abstract": self.abstract,
            "overview": self.overview,
            "content": self.content,
            "meta": self.meta,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "active_count": self.active_count,
            "relations": self.relations,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Context":
        ctx_type = None
        if data.get("context_type"):
            ctx_type = ContextType(data["context_type"])
        return cls(
            id=data.get("id"),
            uri=data["uri"],
            parent_uri=data.get("parent_uri"),
            context_type=ctx_type,
            abstract=data.get("abstract", ""),
            overview=data.get("overview", ""),
            content=data.get("content", ""),
            meta=data.get("meta", {}),
            active_count=data.get("active_count", 0),
            relations=data.get("relations", []),
        )


def build_skill_uri(name: str) -> str:
    """构建技能 URI"""
    return f"{URI_PREFIX}skills/{name}"


def build_document_uri(doc_id: str) -> str:
    """构建文档 URI"""
    return f"{URI_PREFIX}documents/{doc_id}"
