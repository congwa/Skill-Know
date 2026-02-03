"""提示词管理路由"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.prompt import (
    PromptUpdate,
    PromptResponse,
    PromptListResponse,
)
from app.services.prompt import PromptService

router = APIRouter(prefix="/prompts", tags=["prompts"])


@router.get("", response_model=PromptListResponse)
async def list_prompts(
    category: str | None = None,
    include_inactive: bool = False,
    db: AsyncSession = Depends(get_db),
):
    """列出所有提示词"""
    service = PromptService(db)
    prompts = await service.list_all(category, include_inactive)
    return PromptListResponse(items=prompts, total=len(prompts))


@router.get("/{key}", response_model=PromptResponse)
async def get_prompt(
    key: str,
    db: AsyncSession = Depends(get_db),
):
    """获取提示词"""
    service = PromptService(db)
    prompt = await service.get(key)
    if not prompt:
        raise HTTPException(status_code=404, detail="提示词不存在")
    return prompt


@router.put("/{key}", response_model=PromptResponse)
async def update_prompt(
    key: str,
    data: PromptUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新提示词"""
    service = PromptService(db)
    try:
        prompt = await service.update(key, data)
        return prompt
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{key}/reset", response_model=PromptResponse)
async def reset_prompt(
    key: str,
    db: AsyncSession = Depends(get_db),
):
    """重置提示词为默认值"""
    service = PromptService(db)
    try:
        prompt = await service.reset(key)
        return prompt
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
