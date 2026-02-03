"""文档管理路由"""

import os
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.document import DocumentStatus
from app.schemas.document import (
    DocumentCreate,
    DocumentUpdate,
    DocumentResponse,
    DocumentListResponse,
    DocumentFolderCreate,
    DocumentFolderUpdate,
    DocumentFolderResponse,
)
from app.services.document import DocumentService
from app.services.document_to_skill import DocumentToSkillService, ConvertOptions

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/folders", response_model=DocumentFolderResponse)
async def create_folder(
    data: DocumentFolderCreate,
    db: AsyncSession = Depends(get_db),
):
    """创建文件夹"""
    service = DocumentService(db)
    folder = await service.create_folder(data)
    return folder


@router.get("/folders", response_model=list[DocumentFolderResponse])
async def list_folders(
    parent_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """列出文件夹"""
    service = DocumentService(db)
    folders = await service.list_folders(parent_id)
    return folders


@router.get("/folders/{folder_id}", response_model=DocumentFolderResponse)
async def get_folder(
    folder_id: str,
    db: AsyncSession = Depends(get_db),
):
    """获取文件夹"""
    service = DocumentService(db)
    folder = await service.get_folder(folder_id)
    if not folder:
        raise HTTPException(status_code=404, detail="文件夹不存在")
    return folder


@router.put("/folders/{folder_id}", response_model=DocumentFolderResponse)
async def update_folder(
    folder_id: str,
    data: DocumentFolderUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新文件夹"""
    service = DocumentService(db)
    folder = await service.update_folder(folder_id, data)
    if not folder:
        raise HTTPException(status_code=404, detail="文件夹不存在")
    return folder


@router.delete("/folders/{folder_id}")
async def delete_folder(
    folder_id: str,
    db: AsyncSession = Depends(get_db),
):
    """删除文件夹"""
    service = DocumentService(db)
    success = await service.delete_folder(folder_id)
    if not success:
        raise HTTPException(status_code=404, detail="文件夹不存在或无法删除")
    return {"success": True}


@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    title: str | None = None,
    folder_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """上传文档"""
    # 确保上传目录存在
    upload_dir = settings.ensure_data_dir() / "uploads"
    upload_dir.mkdir(exist_ok=True)

    # 生成文件路径
    file_ext = Path(file.filename).suffix if file.filename else ""
    file_id = str(uuid.uuid4())
    file_path = upload_dir / f"{file_id}{file_ext}"

    # 保存文件
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    # 提取文本内容（简单实现，仅支持文本文件）
    text_content = None
    if file_ext.lower() in [".txt", ".md", ".markdown"]:
        try:
            text_content = content.decode("utf-8")
        except Exception:
            pass

    # 创建文档记录
    service = DocumentService(db)
    data = DocumentCreate(
        title=title or file.filename or "未命名文档",
        folder_id=folder_id,
    )
    document = await service.create_document(
        data=data,
        filename=file.filename or "unknown",
        file_path=str(file_path),
        file_size=len(content),
        file_type=file_ext.lstrip(".") or "unknown",
        content=text_content,
    )
    return document


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    folder_id: str | None = None,
    category: str | None = None,
    status: DocumentStatus | None = None,
    is_converted: bool | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """列出文档
    
    Args:
        is_converted: 过滤是否已转化为技能（True=已转化, False=未转化, None=全部）
    """
    service = DocumentService(db)
    documents, total = await service.list_documents(
        folder_id=folder_id,
        category=category,
        status=status,
        is_converted=is_converted,
        page=page,
        page_size=page_size,
    )
    return DocumentListResponse(
        items=documents,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/search")
async def search_documents(
    q: str = Query(..., min_length=1),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """搜索文档"""
    service = DocumentService(db)
    documents = await service.search_documents(q, limit)
    return {"items": documents, "total": len(documents)}


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
):
    """获取文档详情"""
    service = DocumentService(db)
    document = await service.get_document(document_id)
    if not document:
        raise HTTPException(status_code=404, detail="文档不存在")
    return document


@router.put("/{document_id}", response_model=DocumentResponse)
async def update_document(
    document_id: str,
    data: DocumentUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新文档"""
    service = DocumentService(db)
    document = await service.update_document(document_id, data)
    if not document:
        raise HTTPException(status_code=404, detail="文档不存在")
    return document


@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
):
    """删除文档"""
    service = DocumentService(db)
    success = await service.delete_document(document_id)
    if not success:
        raise HTTPException(status_code=404, detail="文档不存在")
    return {"success": True}


@router.post("/{document_id}/move")
async def move_document(
    document_id: str,
    folder_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """移动文档到指定文件夹"""
    service = DocumentService(db)
    document = await service.move_document(document_id, folder_id)
    if not document:
        raise HTTPException(status_code=404, detail="文档不存在")
    return {"success": True, "folder_id": folder_id}


@router.post("/{document_id}/convert-to-skill")
async def convert_to_skill(
    document_id: str,
    use_llm: bool = True,
    auto_activate: bool = True,
    folder_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """将文档转换为 Skill
    
    Args:
        document_id: 文档 ID
        use_llm: 是否使用 LLM 生成（默认 True）
        auto_activate: 是否自动激活 Skill（默认 True）
        folder_id: 目标文件夹 ID
    
    Returns:
        转换结果，包含生成的 Skill 信息
    """
    options = ConvertOptions(
        use_llm=use_llm,
        auto_activate=auto_activate,
        folder_id=folder_id,
    )
    
    service = DocumentToSkillService(db)
    result = await service.convert(document_id, options)
    
    if not result.success:
        raise HTTPException(status_code=400, detail=result.error)
    
    return {
        "success": True,
        "skill": {
            "id": result.skill.id,
            "name": result.skill.name,
            "description": result.skill.description,
            "category": result.skill.category.value,
            "trigger_keywords": result.skill.trigger_keywords,
        } if result.skill else None,
        "analysis": {
            "doc_type": result.analysis.doc_type,
            "word_count": result.analysis.word_count,
            "complexity": result.analysis.complexity,
            "concepts": result.analysis.concepts[:10],
        } if result.analysis else None,
    }


@router.post("/batch-convert")
async def batch_convert_to_skill(
    document_ids: list[str],
    use_llm: bool = True,
    folder_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """批量将文档转换为 Skill
    
    Args:
        document_ids: 文档 ID 列表
        use_llm: 是否使用 LLM 生成
        folder_id: 目标文件夹 ID
    
    Returns:
        批量转换结果
    """
    options = ConvertOptions(
        use_llm=use_llm,
        folder_id=folder_id,
    )
    
    service = DocumentToSkillService(db)
    results = await service.batch_convert(document_ids, options)
    
    return {
        "total": len(results),
        "success_count": sum(1 for r in results if r.success),
        "results": [
            {
                "document_id": r.document_id,
                "success": r.success,
                "skill_id": r.skill.id if r.skill else None,
                "skill_name": r.skill.name if r.skill else None,
                "error": r.error,
            }
            for r in results
        ],
    }
