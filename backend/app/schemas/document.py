"""文档相关 schemas"""

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.document import DocumentStatus


class DocumentFolderCreate(BaseModel):
    """创建文档文件夹"""

    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    parent_id: str | None = None


class DocumentFolderUpdate(BaseModel):
    """更新文档文件夹"""

    name: str | None = None
    description: str | None = None
    parent_id: str | None = None
    sort_order: int | None = None


class DocumentFolderResponse(BaseModel):
    """文档文件夹响应"""

    id: str
    name: str
    description: str | None
    parent_id: str | None
    sort_order: int
    is_system: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentCreate(BaseModel):
    """创建文档"""

    title: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    folder_id: str | None = None
    tags: list[str] = Field(default_factory=list)


class DocumentUpdate(BaseModel):
    """更新文档"""

    title: str | None = None
    description: str | None = None
    folder_id: str | None = None
    category: str | None = None
    tags: list[str] | None = None


class DocumentResponse(BaseModel):
    """文档响应"""

    id: str
    title: str
    description: str | None
    filename: str
    file_path: str
    file_size: int
    file_type: str
    content: str | None
    status: DocumentStatus
    error_message: str | None
    category: str | None
    tags: list[str]
    folder_id: str | None
    extra_metadata: dict = Field(default_factory=dict)
    # 技能转化相关
    skill_id: str | None = None
    is_converted: bool = False
    converted_at: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentListResponse(BaseModel):
    """文档列表响应"""

    items: list[DocumentResponse]
    total: int
    page: int
    page_size: int
