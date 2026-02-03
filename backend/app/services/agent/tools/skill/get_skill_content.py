"""获取技能内容工具

获取指定技能的完整内容。
"""

from __future__ import annotations

import json
import uuid
from typing import Annotated

from langchain.tools import ToolRuntime, tool
from pydantic import Field

from app.core.database import get_db_context
from app.core.logging import get_logger
from app.schemas.events import StreamEventType
from app.services.streaming.context import ChatContext

logger = get_logger("tool.get_skill_content")


@tool
async def get_skill_content(
    runtime: ToolRuntime[ChatContext, dict],
    skill_id: Annotated[str, Field(description="技能 ID")],
) -> str:
    """获取指定技能的完整内容。

    根据技能 ID 从知识库中获取技能的完整内容，
    包括名称、描述、分类和详细内容。

    Args:
        skill_id: 技能 ID

    Returns:
        技能详细信息的 JSON 字符串

    Examples:
        >>> get_skill_content(skill_id="abc123")
        '{"skill_id": "abc123", "name": "摄影入门", "content": "..."}'
    """
    tool_call_id = uuid.uuid4().hex
    
    emitter = getattr(runtime.context, "emitter", None) if runtime.context else None
    
    if emitter and hasattr(emitter, "aemit"):
        await emitter.aemit(
            StreamEventType.TOOL_START.value,
            {
                "tool_call_id": tool_call_id,
                "name": "get_skill_content",
                "input": {"skill_id": skill_id},
            },
        )

    logger.info(
        "┌── 工具: get_skill_content 开始 ──┐",
        skill_id=skill_id,
    )

    try:
        async with get_db_context() as session:
            from app.services.skill import SkillService
            
            skill_service = SkillService(session)
            skill = await skill_service.get_skill(skill_id)

            if not skill:
                if emitter and hasattr(emitter, "aemit"):
                    await emitter.aemit(
                        StreamEventType.TOOL_END.value,
                        {
                            "tool_call_id": tool_call_id,
                            "name": "get_skill_content",
                            "status": "not_found",
                            "skill_id": skill_id,
                        },
                    )
                logger.warning(
                    "│ [1] 技能未找到",
                    skill_id=skill_id,
                )
                logger.info("└── 工具: get_skill_content 结束 (未找到) ──┘")
                return json.dumps({"error": f"技能未找到: {skill_id}"}, ensure_ascii=False)

            logger.info(
                "│ [1] 获取技能成功",
                skill_name=skill.name,
                content_length=len(skill.content) if skill.content else 0,
            )
            logger.info(f"│     技能 ID: {skill.id}")
            logger.info(f"│     技能名称: {skill.name}")
            logger.info(f"│     技能分类: {skill.category.value if skill.category else '无'}")
            if skill.description:
                logger.info(f"│     技能描述: {skill.description[:100]}..." if len(skill.description) > 100 else f"│     技能描述: {skill.description}")
            logger.info(f"│     内容长度: {len(skill.content) if skill.content else 0} 字符")

            result_data = {
                "skill_id": skill.id,
                "name": skill.name,
                "description": skill.description,
                "category": skill.category.value if skill.category else None,
                "content": skill.content,
            }

            if emitter and hasattr(emitter, "aemit"):
                await emitter.aemit(
                    StreamEventType.TOOL_END.value,
                    {
                        "tool_call_id": tool_call_id,
                        "name": "get_skill_content",
                        "status": "success",
                        "skill_id": skill.id,
                        "skill_name": skill.name,
                    },
                )

            logger.info(
                "└── 工具: get_skill_content 结束 ──┘",
                skill_name=skill.name,
            )

            return json.dumps(result_data, ensure_ascii=False)

    except Exception as e:
        if emitter and hasattr(emitter, "aemit"):
            await emitter.aemit(
                StreamEventType.TOOL_END.value,
                {
                    "tool_call_id": tool_call_id,
                    "name": "get_skill_content",
                    "status": "error",
                    "error": str(e),
                },
            )
        logger.exception("获取技能内容失败", error=str(e))
        return json.dumps({"error": f"获取技能内容失败: {e}"}, ensure_ascii=False)
