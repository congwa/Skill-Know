"""聊天路由"""

import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat import ChatService

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/stream")
async def chat_stream(
    data: ChatRequest,
    db: AsyncSession = Depends(get_db),
):
    """流式聊天"""
    service = ChatService(db)

    async def generate():
        async for event in service.chat_stream(
            message=data.message,
            conversation_id=data.conversation_id,
        ):
            yield f"data: {event.model_dump_json()}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/agent/stream")
async def chat_agent_stream(
    data: ChatRequest,
    db: AsyncSession = Depends(get_db),
):
    """流式聊天 - Agent 模式（支持 Tool Calling）"""
    service = ChatService(db)

    async def generate():
        async for event in service.chat_stream_with_tools(
            message=data.message,
            conversation_id=data.conversation_id,
        ):
            yield f"data: {event.model_dump_json()}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("", response_model=ChatResponse)
async def chat(
    data: ChatRequest,
    db: AsyncSession = Depends(get_db),
):
    """非流式聊天"""
    service = ChatService(db)
    try:
        result = await service.chat(
            message=data.message,
            conversation_id=data.conversation_id,
        )
        return ChatResponse(
            conversation_id=result["conversation_id"],
            message_id=result["message_id"],
            content=result["content"],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
