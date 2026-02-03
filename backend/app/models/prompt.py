"""提示词数据模型

存储系统提示词，支持默认值 + 用户自定义覆盖。
所有提示词统一使用 Markdown 格式。
"""

from enum import Enum as PyEnum

from sqlalchemy import Boolean, Enum, String, Text
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class PromptCategory(str, PyEnum):
    """提示词分类"""

    SYSTEM = "system"  # 系统提示词
    CHAT = "chat"  # 聊天相关
    SKILL = "skill"  # 技能生成
    CLASSIFICATION = "classification"  # 分类相关
    SEARCH = "search"  # 搜索相关


class Prompt(Base, TimestampMixin):
    """提示词模型

    key 作为主键，对应唯一标识，如 "system.chat", "skill.generator"
    """

    __tablename__ = "prompts"

    # 主键：提示词唯一标识
    key: Mapped[str] = mapped_column(
        String(100),
        primary_key=True,
        comment="提示词唯一标识",
    )

    # 分类
    category: Mapped[PromptCategory] = mapped_column(
        Enum(PromptCategory),
        nullable=False,
        index=True,
    )

    # 显示名称
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    # 描述
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # 提示词内容（Markdown 格式）
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # 支持的变量列表
    variables: Mapped[list] = mapped_column(JSON, default=list)

    # 是否启用
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    def __repr__(self) -> str:
        return f"<Prompt {self.key}>"
