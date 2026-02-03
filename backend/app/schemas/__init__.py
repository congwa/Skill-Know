"""Pydantic schemas"""

from app.schemas.document import (
    DocumentCreate,
    DocumentUpdate,
    DocumentResponse,
    DocumentFolderCreate,
    DocumentFolderUpdate,
    DocumentFolderResponse,
)
from app.schemas.skill import (
    SkillCreate,
    SkillUpdate,
    SkillResponse,
)
from app.schemas.prompt import (
    PromptCreate,
    PromptUpdate,
    PromptResponse,
)
from app.schemas.conversation import (
    ConversationCreate,
    ConversationResponse,
    MessageCreate,
    MessageResponse,
)
from app.schemas.chat import ChatRequest, ChatResponse
from app.schemas.events import StreamEventType, StreamEvent
from app.schemas.quick_setup import (
    QuickSetupState,
    SetupStep,
    ChecklistItem,
    ChecklistResponse,
)

__all__ = [
    "DocumentCreate",
    "DocumentUpdate",
    "DocumentResponse",
    "DocumentFolderCreate",
    "DocumentFolderUpdate",
    "DocumentFolderResponse",
    "SkillCreate",
    "SkillUpdate",
    "SkillResponse",
    "PromptCreate",
    "PromptUpdate",
    "PromptResponse",
    "ConversationCreate",
    "ConversationResponse",
    "MessageCreate",
    "MessageResponse",
    "ChatRequest",
    "ChatResponse",
    "StreamEventType",
    "StreamEvent",
    "QuickSetupState",
    "SetupStep",
    "ChecklistItem",
    "ChecklistResponse",
]
