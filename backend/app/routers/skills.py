"""技能管理路由"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.skill import SkillType, SkillCategory
from app.schemas.skill import (
    SkillCreate,
    SkillUpdate,
    SkillResponse,
    SkillListResponse,
    SkillSearchRequest,
)
from app.services.skill import SkillService

router = APIRouter(prefix="/skills", tags=["skills"])


@router.post("", response_model=SkillResponse)
async def create_skill(
    data: SkillCreate,
    db: AsyncSession = Depends(get_db),
):
    """创建技能"""
    service = SkillService(db)
    skill = await service.create_skill(data)
    return skill


@router.get("", response_model=SkillListResponse)
async def list_skills(
    type: SkillType | None = None,
    category: SkillCategory | None = None,
    folder_id: str | None = None,
    is_active: bool | None = True,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """列出技能"""
    service = SkillService(db)
    skills, total = await service.list_skills(
        skill_type=type,
        category=category,
        folder_id=folder_id,
        is_active=is_active,
        page=page,
        page_size=page_size,
    )
    return SkillListResponse(
        items=skills,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/search")
async def search_skills(
    data: SkillSearchRequest,
    db: AsyncSession = Depends(get_db),
):
    """搜索技能"""
    service = SkillService(db)
    skills = await service.search_skills(
        query=data.query,
        category=data.category,
        skill_type=data.type,
        limit=data.limit,
    )
    return {"items": skills, "total": len(skills)}


@router.get("/{skill_id}", response_model=SkillResponse)
async def get_skill(
    skill_id: str,
    db: AsyncSession = Depends(get_db),
):
    """获取技能详情"""
    service = SkillService(db)
    skill = await service.get_skill(skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="技能不存在")
    return skill


@router.put("/{skill_id}", response_model=SkillResponse)
async def update_skill(
    skill_id: str,
    data: SkillUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新技能"""
    service = SkillService(db)
    skill = await service.update_skill(skill_id, data)
    if not skill:
        raise HTTPException(status_code=404, detail="技能不存在或不可编辑")
    return skill


@router.delete("/{skill_id}")
async def delete_skill(
    skill_id: str,
    db: AsyncSession = Depends(get_db),
):
    """删除技能"""
    service = SkillService(db)
    success = await service.delete_skill(skill_id)
    if not success:
        raise HTTPException(status_code=404, detail="技能不存在或不可删除")
    return {"success": True}


@router.post("/{skill_id}/move")
async def move_skill(
    skill_id: str,
    folder_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """移动技能到指定文件夹"""
    service = SkillService(db)
    skill = await service.move_skill(skill_id, folder_id)
    if not skill:
        raise HTTPException(status_code=404, detail="技能不存在或不可移动")
    return {"success": True, "folder_id": folder_id}
