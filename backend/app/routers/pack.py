"""知识包导出/导入路由"""

import json

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.pack import PackService

router = APIRouter(prefix="/pack", tags=["pack"])


@router.post("/export")
async def export_pack(
    category: str | None = None,
    folder_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """导出知识包"""
    service = PackService(db)
    pack = await service.export_skills(category=category, folder_id=folder_id)
    return pack


@router.post("/import")
async def import_pack(
    file: UploadFile,
    skip_duplicates: bool = True,
    db: AsyncSession = Depends(get_db),
):
    """导入知识包"""
    content = await file.read()
    try:
        pack_data = json.loads(content)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="无效的 JSON 文件")

    service = PackService(db)
    result = await service.import_skills(pack_data, skip_duplicates=skip_duplicates)
    await db.commit()
    return result
