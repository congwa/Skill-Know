"""技能相关 schemas"""

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.skill import SkillType, SkillCategory


class SkillCreate(BaseModel):
    """创建技能"""

    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., min_length=1)
    category: SkillCategory = SkillCategory.PROMPT
    content: str = Field(..., min_length=1)
    trigger_keywords: list[str] = Field(default_factory=list)
    trigger_intents: list[str] = Field(default_factory=list)
    always_apply: bool = False
    folder_id: str | None = None
    priority: int = 100
    config: dict = Field(default_factory=dict)


class SkillUpdate(BaseModel):
    """更新技能"""

    name: str | None = None
    description: str | None = None
    category: SkillCategory | None = None
    content: str | None = None
    trigger_keywords: list[str] | None = None
    trigger_intents: list[str] | None = None
    always_apply: bool | None = None
    folder_id: str | None = None
    priority: int | None = None
    is_active: bool | None = None
    config: dict | None = None


class SkillResponse(BaseModel):
    """技能响应"""

    id: str
    name: str
    description: str
    type: SkillType
    category: SkillCategory
    content: str
    trigger_keywords: list[str]
    trigger_intents: list[str]
    always_apply: bool
    version: str
    author: str | None
    is_active: bool
    source_document_id: str | None
    folder_id: str | None
    priority: int
    config: dict
    is_editable: bool
    is_deletable: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SkillListResponse(BaseModel):
    """技能列表响应"""

    items: list[SkillResponse]
    total: int
    page: int
    page_size: int


class SkillSearchRequest(BaseModel):
    """技能搜索请求"""

    query: str
    category: SkillCategory | None = None
    type: SkillType | None = None
    limit: int = Field(default=20, ge=1, le=100)
