"""快速设置路由"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.models_dev import get_providers, get_provider_models, get_provider_base_url
from app.schemas.quick_setup import (
    QuickSetupState,
    ChecklistResponse,
    EssentialSetupRequest,
    TestConnectionRequest,
    TestConnectionResponse,
)
from app.services.quick_setup import QuickSetupService

router = APIRouter(prefix="/quick-setup", tags=["quick-setup"])


@router.get("/state", response_model=QuickSetupState)
async def get_state(db: AsyncSession = Depends(get_db)):
    """获取设置状态"""
    service = QuickSetupService(db)
    return await service.get_state()


@router.get("/checklist", response_model=ChecklistResponse)
async def get_checklist(db: AsyncSession = Depends(get_db)):
    """获取配置检查清单"""
    service = QuickSetupService(db)
    return await service.get_checklist()


@router.post("/essential", response_model=QuickSetupState)
async def complete_essential_setup(
    data: EssentialSetupRequest,
    db: AsyncSession = Depends(get_db),
):
    """完成精简设置"""
    service = QuickSetupService(db)
    return await service.complete_essential_setup(
        llm_provider=data.llm_provider,
        llm_api_key=data.llm_api_key,
        llm_base_url=data.llm_base_url,
        llm_chat_model=data.llm_chat_model,
    )


@router.post("/test-connection", response_model=TestConnectionResponse)
async def test_connection(
    data: TestConnectionRequest,
    db: AsyncSession = Depends(get_db),
):
    """测试 LLM 连接"""
    service = QuickSetupService(db)
    return await service.test_connection(
        llm_provider=data.llm_provider,
        llm_api_key=data.llm_api_key,
        llm_base_url=data.llm_base_url,
        llm_chat_model=data.llm_chat_model,
    )


@router.post("/reset", response_model=QuickSetupState)
async def reset_setup(db: AsyncSession = Depends(get_db)):
    """重置设置"""
    service = QuickSetupService(db)
    return await service.reset()


@router.get("/providers")
async def list_providers():
    """获取支持的 LLM 提供商列表（只包含支持工具调用的模型）"""
    providers = get_providers(tool_calling_only=True)
    return {
        "providers": [p.to_dict() for p in providers],
    }


@router.get("/providers/{provider_id}/models")
async def list_provider_models(provider_id: str):
    """获取指定提供商的模型列表（只包含支持工具调用的模型）"""
    models = get_provider_models(provider_id, tool_calling_only=True)
    base_url = get_provider_base_url(provider_id)
    return {
        "provider_id": provider_id,
        "base_url": base_url,
        "models": [m.to_dict() for m in models],
    }
