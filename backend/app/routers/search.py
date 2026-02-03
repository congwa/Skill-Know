"""统一搜索路由

实现系统 skill 的 SQL 搜索能力。
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logging import get_logger
from app.services.document import DocumentService
from app.services.skill import SkillService

router = APIRouter(prefix="/search", tags=["search"])
logger = get_logger("search_router")


@router.get("")
async def unified_search(
    q: str = Query(..., min_length=1, description="搜索查询"),
    type: str | None = Query(default=None, description="搜索类型：skill, document, all"),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """统一搜索接口

    搜索技能和文档，支持渐进式披露。
    """
    results = {
        "query": q,
        "skills": [],
        "documents": [],
        "total": 0,
    }

    if type in [None, "all", "skill"]:
        skill_service = SkillService(db)
        skills = await skill_service.search_skills(q, limit=limit)
        results["skills"] = [
            {
                "id": s.id,
                "name": s.name,
                "description": s.description,
                "type": s.type.value,
                "category": s.category.value,
                "content_preview": s.content[:200] + "..." if len(s.content) > 200 else s.content,
            }
            for s in skills
        ]

    if type in [None, "all", "document"]:
        doc_service = DocumentService(db)
        documents = await doc_service.search_documents(q, limit=limit)
        results["documents"] = [
            {
                "id": d.id,
                "title": d.title,
                "description": d.description,
                "category": d.category,
                "content_preview": d.content[:200] + "..." if d.content and len(d.content) > 200 else d.content,
            }
            for d in documents
        ]

    results["total"] = len(results["skills"]) + len(results["documents"])
    return results


@router.post("/sql")
async def sql_search(
    query: str = Query(..., description="SQL 查询语句（仅支持 SELECT）"),
    db: AsyncSession = Depends(get_db),
):
    """SQL 搜索接口

    系统 skill 使用的 SQL 搜索能力。
    仅支持 SELECT 语句，用于搜索技能和文档。
    """
    # 安全检查：仅允许 SELECT 语句
    query_upper = query.strip().upper()
    if not query_upper.startswith("SELECT"):
        return {"error": "仅支持 SELECT 语句", "results": []}

    # 禁止危险操作
    dangerous_keywords = ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "CREATE", "TRUNCATE"]
    for keyword in dangerous_keywords:
        if keyword in query_upper:
            return {"error": f"不允许使用 {keyword} 操作", "results": []}

    try:
        result = await db.execute(text(query))
        rows = result.fetchall()
        columns = result.keys()

        results = [dict(zip(columns, row)) for row in rows]
        return {
            "query": query,
            "results": results,
            "count": len(results),
        }
    except Exception as e:
        logger.error("SQL 查询失败", query=query, error=str(e))
        return {"error": str(e), "results": []}


@router.get("/tables")
async def list_tables(db: AsyncSession = Depends(get_db)):
    """列出可搜索的表

    供系统 skill 使用，了解可查询的数据结构。
    """
    return {
        "tables": [
            {
                "name": "skills",
                "description": "技能表",
                "columns": [
                    "id", "name", "description", "type", "category",
                    "content", "trigger_keywords", "is_active", "created_at"
                ],
            },
            {
                "name": "documents",
                "description": "文档表",
                "columns": [
                    "id", "title", "description", "content", "category",
                    "tags", "status", "folder_id", "created_at"
                ],
            },
            {
                "name": "document_folders",
                "description": "文档文件夹表",
                "columns": ["id", "name", "description", "parent_id"],
            },
        ]
    }
