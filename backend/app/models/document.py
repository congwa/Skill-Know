"""文档数据模型

定义 Document（文档）和 DocumentFolder（文档文件夹）。
"""

import uuid
from enum import Enum as PyEnum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.skill import Skill


class DocumentStatus(str, PyEnum):
    """文档状态"""

    PENDING = "pending"  # 待处理
    PROCESSING = "processing"  # 处理中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"  # 处理失败


class DocumentFolder(Base, TimestampMixin):
    """文档文件夹模型"""

    __tablename__ = "document_folders"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 父文件夹（支持嵌套）
    parent_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("document_folders.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # 排序顺序
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    # 是否为系统文件夹（不可删除）
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)

    # 关联
    documents: Mapped[list["Document"]] = relationship(
        "Document",
        back_populates="folder",
        cascade="all, delete-orphan",
    )
    children: Mapped[list["DocumentFolder"]] = relationship(
        "DocumentFolder",
        back_populates="parent",
        cascade="all, delete-orphan",
    )
    parent: Mapped["DocumentFolder | None"] = relationship(
        "DocumentFolder",
        back_populates="children",
        remote_side=[id],
    )

    def __repr__(self) -> str:
        return f"<DocumentFolder {self.name}>"


class Document(Base, TimestampMixin):
    """文档模型"""

    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    # URI 标识 (sk://documents/{id})
    uri: Mapped[str | None] = mapped_column(String(500), nullable=True, unique=True, index=True)

    # 基础信息
    title: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 文件信息
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, default=0)
    file_type: Mapped[str] = mapped_column(String(50), nullable=False)  # pdf, md, txt, etc.

    # 三层内容体系 (L0/L1/L2)
    abstract: Mapped[str | None] = mapped_column(Text, nullable=True)   # L0: 简短摘要
    overview: Mapped[str | None] = mapped_column(Text, nullable=True)   # L1: 结构化概览
    content: Mapped[str | None] = mapped_column(Text, nullable=True)    # L2: 完整内容
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # 状态
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus),
        default=DocumentStatus.PENDING,
        nullable=False,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 分类（AI 归类结果）
    category: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    tags: Mapped[list] = mapped_column(JSON, default=list)

    # 文件夹归属
    folder_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("document_folders.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # 元数据
    extra_metadata: Mapped[dict] = mapped_column(JSON, default=dict)

    # 技能转化关联
    skill_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("skills.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    is_converted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    converted_at: Mapped[str | None] = mapped_column(String(30), nullable=True)

    # 关联
    folder: Mapped["DocumentFolder | None"] = relationship(
        "DocumentFolder",
        back_populates="documents",
    )
    # 转化后的技能（通过 skill_id 关联）
    skill: Mapped["Skill | None"] = relationship(
        "Skill",
        foreign_keys=[skill_id],
        uselist=False,
    )

    def __repr__(self) -> str:
        return f"<Document {self.title}>"
