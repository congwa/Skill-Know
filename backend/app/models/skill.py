"""技能数据模型

定义 Skill 模型，支持系统级和文档级技能。

系统技能（SYSTEM）：不可修改/删除，提供 SQL 搜索等核心能力
文档技能（DOCUMENT）：来源于文档，可修改、可迁移
用户技能（USER）：用户自定义创建
"""

import uuid
from enum import Enum as PyEnum

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.document import Document


class SkillType(str, PyEnum):
    """技能类型"""

    SYSTEM = "system"  # 系统内置（不可修改/删除）
    DOCUMENT = "document"  # 来源于文档
    USER = "user"  # 用户创建


class SkillCategory(str, PyEnum):
    """技能分类"""

    SEARCH = "search"  # 搜索类（SQL 搜索、全文搜索）
    PROMPT = "prompt"  # 提示词增强
    RETRIEVAL = "retrieval"  # 检索增强
    TOOL = "tool"  # 工具扩展
    WORKFLOW = "workflow"  # 工作流


class Skill(Base, TimestampMixin):
    """技能模型"""

    __tablename__ = "skills"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    # 基础信息
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # 类型和分类
    type: Mapped[SkillType] = mapped_column(
        Enum(SkillType),
        default=SkillType.USER,
        nullable=False,
        index=True,
    )
    category: Mapped[SkillCategory] = mapped_column(
        Enum(SkillCategory),
        default=SkillCategory.PROMPT,
        nullable=False,
        index=True,
    )

    # 技能内容（Markdown 格式）
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # 触发配置
    trigger_keywords: Mapped[list] = mapped_column(JSON, default=list)
    trigger_intents: Mapped[list] = mapped_column(JSON, default=list)
    always_apply: Mapped[bool] = mapped_column(Boolean, default=False)

    # 元数据
    version: Mapped[str] = mapped_column(String(20), default="1.0.0")
    author: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # 状态
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)

    # 来源文档（仅 DOCUMENT 类型）
    source_document_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # 文件夹归属（用于组织管理）
    folder_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("document_folders.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # 排序优先级（数值越小优先级越高）
    priority: Mapped[int] = mapped_column(Integer, default=100)

    # 额外配置
    config: Mapped[dict] = mapped_column(JSON, default=dict)

    # 反向关联：来源文档（通过 source_document_id 关联）
    source_document: Mapped["Document | None"] = relationship(
        "Document",
        foreign_keys=[source_document_id],
        uselist=False,
    )

    def __repr__(self) -> str:
        return f"<Skill {self.name} ({self.type.value})>"

    @property
    def is_editable(self) -> bool:
        """是否可编辑"""
        return self.type != SkillType.SYSTEM

    @property
    def is_deletable(self) -> bool:
        """是否可删除"""
        return self.type != SkillType.SYSTEM
