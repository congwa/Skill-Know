"""系统配置数据模型

存储系统级配置，如 API Key、模型配置等。
"""

from sqlalchemy import Boolean, String, Text
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class SystemConfig(Base, TimestampMixin):
    """系统配置模型

    使用 key-value 方式存储配置项。
    """

    __tablename__ = "system_configs"

    # 配置键
    key: Mapped[str] = mapped_column(
        String(100),
        primary_key=True,
        comment="配置键",
    )

    # 配置值（JSON 格式，支持复杂类型）
    value: Mapped[dict | str | int | bool | None] = mapped_column(
        JSON,
        nullable=True,
    )

    # 描述
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 是否敏感（如 API Key）
    is_sensitive: Mapped[bool] = mapped_column(Boolean, default=False)

    # 分组
    group: Mapped[str] = mapped_column(String(50), default="general", index=True)

    def __repr__(self) -> str:
        return f"<SystemConfig {self.key}>"
