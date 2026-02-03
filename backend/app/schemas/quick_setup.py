"""快速设置相关 schemas"""

from enum import StrEnum

from pydantic import BaseModel, Field


class ChecklistItemStatus(StrEnum):
    """检查项状态"""

    OK = "ok"  # 已正确配置
    DEFAULT = "default"  # 使用默认值
    MISSING = "missing"  # 缺失
    ERROR = "error"  # 错误


class ChecklistItem(BaseModel):
    """检查项"""

    key: str
    label: str
    category: str
    status: ChecklistItemStatus
    current_value: str | None = None
    default_value: str | None = None
    description: str | None = None
    step_index: int | None = None


class ChecklistResponse(BaseModel):
    """检查清单响应"""

    items: list[ChecklistItem]
    total: int
    ok_count: int
    default_count: int
    missing_count: int


class SetupStepStatus(StrEnum):
    """设置步骤状态"""

    PENDING = "pending"
    COMPLETED = "completed"
    SKIPPED = "skipped"


class SetupStep(BaseModel):
    """设置步骤"""

    index: int
    key: str
    title: str
    description: str | None = None
    status: SetupStepStatus = SetupStepStatus.PENDING
    is_required: bool = True


class QuickSetupState(BaseModel):
    """快速设置状态"""

    current_step: int = 0
    steps: list[SetupStep] = Field(default_factory=list)
    essential_completed: bool = False
    setup_level: str = "none"  # none, essential, full
    data: dict = Field(default_factory=dict)


class EssentialSetupRequest(BaseModel):
    """精简设置请求"""

    llm_provider: str
    llm_api_key: str
    llm_base_url: str
    llm_chat_model: str


class TestConnectionRequest(BaseModel):
    """测试连接请求"""

    llm_provider: str
    llm_api_key: str
    llm_base_url: str
    llm_chat_model: str


class TestConnectionResponse(BaseModel):
    """测试连接响应"""

    success: bool
    message: str
    latency_ms: int | None = None
