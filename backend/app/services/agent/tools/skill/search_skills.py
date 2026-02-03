"""技能检索工具

根据关键词在知识库中检索相关技能。
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

logger = get_logger("tool.search_skills")


@tool
async def search_skills(
    runtime: ToolRuntime[ChatContext, dict],
    keywords: Annotated[list[str], Field(description="用于检索的关键词列表")],
    limit: Annotated[int, Field(default=5, description="最大返回数量")] = 5,
) -> str:
    """根据关键词在知识库中检索相关技能。

    使用提取的关键词在知识库中进行全文检索，
    返回匹配度最高的技能列表。

    Args:
        keywords: 用于检索的关键词列表
        limit: 最大返回数量，默认 5

    Returns:
        检索到的技能列表的 JSON 字符串

    Examples:
        >>> search_skills(keywords=["拍照", "摄影"])
        '{"count": 2, "skills": [{"skill_id": "...", "name": "摄影入门"}]}'
    """
    tool_call_id = uuid.uuid4().hex
    
    emitter = getattr(runtime.context, "emitter", None) if runtime.context else None
    
    if emitter and hasattr(emitter, "aemit"):
        await emitter.aemit(
            StreamEventType.TOOL_START.value,
            {
                "tool_call_id": tool_call_id,
                "name": "search_skills",
                "input": {"keywords": keywords, "limit": limit},
            },
        )

    logger.info(
        "┌── 工具: search_skills 开始 ──┐",
        keywords=keywords,
        limit=limit,
    )

    try:
        async with get_db_context() as session:
            from app.services.skill_search.searcher import SkillSearcher
            from app.services.skill_search.query import QueryCondition, SearchQuery
            
            # 构建查询
            conditions = [
                QueryCondition(type="keyword", pattern=kw, field="content")
                for kw in keywords
            ]
            search_query = SearchQuery(conditions=conditions, intent="search", limit=limit)
            
            # 执行检索
            skill_searcher = SkillSearcher(session)
            result = await skill_searcher.search(search_query)

            logger.info(
                "│ [1] 检索完成",
                match_count=len(result.matches),
            )
            logger.info(f"│     检索关键词: {keywords}")
            logger.info(f"│     找到 {len(result.matches)} 个匹配结果")
            for i, m in enumerate(result.matches[:limit]):
                logger.info(f"│     [{i+1}] {m.name} (ID: {m.skill_id}, 分数: {round(m.score, 2)})")
                if m.description:
                    logger.info(f"│         描述: {m.description[:50]}..." if len(m.description) > 50 else f"│         描述: {m.description}")

            if not result.matches:
                if emitter and hasattr(emitter, "aemit"):
                    await emitter.aemit(
                        StreamEventType.TOOL_END.value,
                        {
                            "tool_call_id": tool_call_id,
                            "name": "search_skills",
                            "status": "empty",
                            "count": 0,
                        },
                    )
                logger.info("└── 工具: search_skills 结束 (无结果) ──┘")
                return json.dumps({"count": 0, "skills": []}, ensure_ascii=False)

            # 构建返回结果
            skills_info = [
                {
                    "skill_id": m.skill_id,
                    "name": m.name,
                    "description": m.description,
                    "category": m.category,
                    "preview": m.preview[:200] if m.preview else "",
                    "score": round(m.score, 2),
                }
                for m in result.matches[:limit]
            ]

            result_data = {
                "count": len(skills_info),
                "skills": skills_info,
            }

            if emitter and hasattr(emitter, "aemit"):
                await emitter.aemit(
                    StreamEventType.TOOL_END.value,
                    {
                        "tool_call_id": tool_call_id,
                        "name": "search_skills",
                        "status": "success",
                        "count": len(skills_info),
                        "output_preview": skills_info[:3],
                    },
                )

            logger.info(
                "└── 工具: search_skills 结束 ──┘",
                skill_count=len(skills_info),
            )

            return json.dumps(result_data, ensure_ascii=False)

    except Exception as e:
        if emitter and hasattr(emitter, "aemit"):
            await emitter.aemit(
                StreamEventType.TOOL_END.value,
                {
                    "tool_call_id": tool_call_id,
                    "name": "search_skills",
                    "status": "error",
                    "error": str(e),
                },
            )
        logger.exception("技能检索失败", error=str(e))
        return json.dumps({"error": f"技能检索失败: {e}"}, ensure_ascii=False)
