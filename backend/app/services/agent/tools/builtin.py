"""Skill-Know 工具定义

基于 LangChain Tool Calling 实现，兼容 create_agent。
使用 ToolRuntime 访问上下文和数据库会话。
"""

import json
import uuid
from typing import Annotated, Any

from langchain.tools import ToolRuntime, tool
from pydantic import Field

from app.core.logging import get_logger
from app.schemas.events import StreamEventType

logger = get_logger("agent.tools")


@tool
async def search_skills(
    query: Annotated[str, Field(description="搜索查询关键词")],
    runtime: ToolRuntime,
    category: Annotated[str | None, Field(description="技能分类筛选")] = None,
) -> str:
    """搜索知识库中的技能。

    根据关键词搜索相关的技能，返回匹配的技能列表。

    Args:
        query: 搜索关键词
        category: 可选的分类筛选

    Returns:
        JSON 格式的技能列表
    """
    tool_call_id = uuid.uuid4().hex
    
    # 发送工具开始事件
    if hasattr(runtime, "context") and hasattr(runtime.context, "emitter"):
        emitter = runtime.context.emitter
        if hasattr(emitter, "emit"):
            emitter.emit(
                StreamEventType.TOOL_START.value,
                {"tool_call_id": tool_call_id, "name": "search_skills", "input": {"query": query, "category": category}},
            )

    logger.info("搜索技能", query=query, category=category)

    try:
        # 从 runtime.context 获取数据库会话
        session = getattr(runtime.context, "session", None) if hasattr(runtime, "context") else None
        
        if session is None:
            # 使用全局数据库连接
            from app.core.database import get_db_context
            
            async with get_db_context() as session:
                from app.services.skill import SkillService
                skill_service = SkillService(session)
                skills = await skill_service.search_skills(query=query, category=category, limit=5)
        else:
            from app.services.skill import SkillService
            skill_service = SkillService(session)
            skills = await skill_service.search_skills(query=query, category=category, limit=5)

        results = [
            {
                "skill_id": s.id,
                "name": s.name,
                "description": s.description or "",
                "category": s.category.value if s.category else None,
            }
            for s in skills
        ]

        # 发送工具结束事件
        if hasattr(runtime, "context") and hasattr(runtime.context, "emitter"):
            emitter = runtime.context.emitter
            if hasattr(emitter, "emit"):
                emitter.emit(
                    StreamEventType.TOOL_END.value,
                    {"tool_call_id": tool_call_id, "name": "search_skills", "status": "success", "count": len(results)},
                )

        logger.info("技能搜索完成", count=len(results))
        return json.dumps({"skills": results, "count": len(results)}, ensure_ascii=False)

    except Exception as e:
        logger.exception("技能搜索失败", error=str(e))
        return json.dumps({"error": str(e), "query": query}, ensure_ascii=False)


@tool
async def get_skill_content(
    skill_id: Annotated[str, Field(description="技能 ID")],
    runtime: ToolRuntime,
) -> str:
    """获取指定技能的完整内容。

    根据技能 ID 获取技能的详细内容。

    Args:
        skill_id: 技能 ID

    Returns:
        技能的完整内容
    """
    tool_call_id = uuid.uuid4().hex
    
    # 发送工具开始事件
    if hasattr(runtime, "context") and hasattr(runtime.context, "emitter"):
        emitter = runtime.context.emitter
        if hasattr(emitter, "emit"):
            emitter.emit(
                StreamEventType.TOOL_START.value,
                {"tool_call_id": tool_call_id, "name": "get_skill_content", "input": {"skill_id": skill_id}},
            )

    logger.info("获取技能内容", skill_id=skill_id)

    try:
        # 从 runtime.context 获取数据库会话
        session = getattr(runtime.context, "session", None) if hasattr(runtime, "context") else None
        
        if session is None:
            from app.core.database import get_db_context
            
            async with get_db_context() as session:
                from app.services.skill import SkillService
                skill_service = SkillService(session)
                skill = await skill_service.get(skill_id)
        else:
            from app.services.skill import SkillService
            skill_service = SkillService(session)
            skill = await skill_service.get(skill_id)

        if not skill:
            return json.dumps({"error": f"技能未找到: {skill_id}"}, ensure_ascii=False)

        result = {
            "skill_id": skill.id,
            "name": skill.name,
            "description": skill.description or "",
            "category": skill.category.value if skill.category else None,
            "content": skill.content or "",
        }

        # 发送工具结束事件
        if hasattr(runtime, "context") and hasattr(runtime.context, "emitter"):
            emitter = runtime.context.emitter
            if hasattr(emitter, "emit"):
                emitter.emit(
                    StreamEventType.TOOL_END.value,
                    {"tool_call_id": tool_call_id, "name": "get_skill_content", "status": "success"},
                )

        logger.info("技能内容获取完成", skill_id=skill_id, name=skill.name)
        return json.dumps(result, ensure_ascii=False)

    except Exception as e:
        logger.exception("获取技能内容失败", error=str(e))
        return json.dumps({"error": str(e), "skill_id": skill_id}, ensure_ascii=False)


# 工具注册表
TOOLS = [search_skills, get_skill_content]


def get_tools() -> list:
    """获取所有可用工具"""
    return TOOLS


def get_tool_schemas() -> list[dict[str, Any]]:
    """获取工具的 JSON Schema（用于 LLM bind_tools）"""
    schemas = []
    for t in TOOLS:
        schemas.append({
            "name": t.name,
            "description": t.description,
            "parameters": t.args_schema.schema() if t.args_schema else {},
        })
    return schemas
