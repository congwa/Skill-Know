"""提示词相关 schemas"""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from app.models.prompt import PromptCategory


class PromptSource(StrEnum):
    """提示词来源"""

    DEFAULT = "default"  # 系统默认
    CUSTOM = "custom"  # 用户自定义


class PromptCreate(BaseModel):
    """创建提示词"""

    key: str = Field(..., min_length=1, max_length=100)
    category: PromptCategory
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    content: str = Field(..., min_length=1)
    variables: list[str] = Field(default_factory=list)


class PromptUpdate(BaseModel):
    """更新提示词"""

    name: str | None = None
    description: str | None = None
    content: str | None = None
    is_active: bool | None = None


class PromptResponse(BaseModel):
    """提示词响应"""

    key: str
    category: str
    name: str
    description: str | None
    content: str
    variables: list[str]
    source: PromptSource
    is_active: bool
    default_content: str | None = None
    created_at: datetime | None
    updated_at: datetime | None

    model_config = {"from_attributes": True}


class PromptListResponse(BaseModel):
    """提示词列表响应"""

    items: list[PromptResponse]
    total: int
