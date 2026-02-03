"""批量上传路由

提供批量上传和进度查询接口。
"""

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.batch_upload import BatchUploadService
from app.services.upload_task import task_manager

router = APIRouter(prefix="/upload", tags=["upload"])


@router.post("/batch")
async def batch_upload(
    files: list[UploadFile] = File(...),
    folder_id: str | None = None,
    use_llm: bool = True,
    db: AsyncSession = Depends(get_db),
):
    """批量上传文档并转换为 Skill

    Args:
        files: 上传的文件列表
        folder_id: 目标文件夹 ID
        use_llm: 是否使用 LLM 生成 Skill

    Returns:
        task_id 和 stream_url
    """
    if not files:
        raise HTTPException(status_code=400, detail="请选择至少一个文件")

    # 验证文件格式
    supported_exts = {'.txt', '.md', '.markdown', '.pdf', '.docx', '.doc'}
    for file in files:
        if file.filename:
            ext = '.' + file.filename.split('.')[-1].lower() if '.' in file.filename else ''
            if ext not in supported_exts:
                raise HTTPException(
                    status_code=400,
                    detail=f"不支持的文件格式: {file.filename}"
                )

    service = BatchUploadService(db)
    task_id = await service.start_batch_upload(
        files=files,
        folder_id=folder_id,
        use_llm=use_llm,
    )

    return {
        "task_id": task_id,
        "file_count": len(files),
        "stream_url": f"/api/upload/tasks/{task_id}/stream",
    }


@router.get("/tasks/{task_id}")
async def get_task_status(task_id: str):
    """获取任务状态

    Args:
        task_id: 任务 ID

    Returns:
        任务状态和文件进度
    """
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    return {
        "task_id": task.task_id,
        "status": task.status,
        "total": task.total,
        "completed": task.completed,
        "failed": task.failed,
        "files": [
            {
                "file_id": fp.file_id,
                "filename": fp.filename,
                "step": fp.step.value,
                "status": fp.status.value,
                "progress": fp.progress,
                "message": fp.message,
                "error": fp.error,
                "result": fp.result,
            }
            for fp in task.files.values()
        ],
    }


@router.get("/tasks/{task_id}/stream")
async def stream_task_progress(task_id: str):
    """获取任务进度流（SSE）

    Args:
        task_id: 任务 ID

    Returns:
        SSE 事件流
    """
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    async def event_generator():
        async for event in task_manager.get_event_stream(task_id):
            data = json.dumps(event.to_dict(), ensure_ascii=False)
            yield f"event: file.progress\ndata: {data}\n\n"

        # 发送任务完成事件
        task = task_manager.get_task(task_id)
        if task:
            complete_data = json.dumps({
                "task_id": task_id,
                "total": task.total,
                "completed": task.completed,
                "failed": task.failed,
                "status": task.status,
            }, ensure_ascii=False)
            yield f"event: task.completed\ndata: {complete_data}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.delete("/tasks/{task_id}")
async def cleanup_task(task_id: str):
    """清理任务

    Args:
        task_id: 任务 ID

    Returns:
        success
    """
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    task_manager.cleanup_task(task_id)

    return {"success": True}
