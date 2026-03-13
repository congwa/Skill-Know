"""技能检索工具

根据关键词在知识库中检索相关技能。
支持 IntentAnalyzer 意图拆解：复杂查询自动拆分为多条子查询并行检索后合并去重。
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from typing import Annotated

from langchain.tools import ToolRuntime, tool
from pydantic import Field

from app.core.database import get_db_context
from app.core.logging import get_logger
from app.schemas.events import BusinessEventType, StreamEventType
from app.services.streaming.context import ChatContext

logger = get_logger("tool.search_skills")


@dataclass
class _Match:
    skill_id: str
    name: str
    description: str
    category: str
    score: float
    preview: str


async def _multi_query_search(
    session,
    queries: list,
    limit: int,
) -> list[_Match]:
    """对多条子查询并行检索并合并去重，保留最高分。"""
    import asyncio

    from app.core.config import settings
    from app.core.rerank import get_rerank_client
    from app.core.service import get_service
    from app.services.retriever import SkillRetriever

    vector_store = get_service().get_vector_store(session)
    rerank_client = get_rerank_client() if settings.DEFAULT_SEARCH_MODE == "thinking" else None
    retriever = SkillRetriever(session, vector_store=vector_store, rerank_client=rerank_client)
    seen: dict[str, _Match] = {}

    async def _search_one(sq):
        return await retriever.retrieve(
            query=sq.query,
            limit=limit,
            context_type=sq.context_type or None,
        )

    results = await asyncio.gather(*[_search_one(sq) for sq in queries], return_exceptions=True)

    for retrieval in results:
        if isinstance(retrieval, Exception):
            logger.warning(f"子查询检索失败: {retrieval}")
            continue
        for r in retrieval.results:
            existing = seen.get(r.skill_id)
            match = _Match(
                skill_id=r.skill_id,
                name=r.name,
                description=r.description,
                category=r.category,
                score=r.score,
                preview=r.abstract or (r.content[:200] if r.content else ""),
            )
            if existing is None or r.score > existing.score:
                seen[r.skill_id] = match

    merged = sorted(seen.values(), key=lambda m: m.score, reverse=True)
    return merged[:limit]


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
            query_text = " ".join(keywords)

            from app.services.intent_analyzer import SearchQuery

            # IntentAnalyzer: 将原始关键词组合拆解为更精确的子查询
            sub_queries: list[SearchQuery] = [SearchQuery(query=query_text, priority=1)]
            try:
                from langchain_openai import ChatOpenAI

                from app.services.conversation import ConversationService
                from app.services.intent_analyzer import IntentAnalyzer
                from app.services.system_config import SystemConfigService

                config_service = SystemConfigService(session)
                llm_config = await config_service.get_llm_config()
                llm = ChatOpenAI(
                    api_key=llm_config["api_key"],
                    base_url=llm_config["base_url"],
                    model=llm_config["chat_model"],
                )

                # 从 ChatContext 获取会话历史
                history: list[dict[str, str]] | None = None
                ctx = runtime.context
                if ctx and hasattr(ctx, "conversation_id") and ctx.conversation_id:
                    try:
                        conv_service = ConversationService(session)
                        messages = await conv_service.get_messages(ctx.conversation_id)
                        if messages:
                            history = [
                                {"role": m.role.value, "content": m.content}
                                for m in messages[-10:]
                                if m.content
                            ]
                    except Exception:
                        pass

                analyzer = IntentAnalyzer(llm=llm)
                plan = await analyzer.analyze(
                    current_message=query_text,
                    history=history,
                )

                if plan.needs_retrieval and plan.queries:
                    sub_queries = sorted(plan.queries, key=lambda q: q.priority)
                    logger.info(f"│ [0] 意图拆解: {len(sub_queries)} 条子查询")

                    if emitter and hasattr(emitter, "aemit"):
                        await emitter.aemit(
                            BusinessEventType.INTENT_EXTRACTED,
                            {
                                "tool_call_id": tool_call_id,
                                "needs_retrieval": plan.needs_retrieval,
                                "sub_queries": [sq.query for sq in sub_queries],
                                "reasoning": plan.reasoning,
                            },
                        )
                elif not plan.needs_retrieval:
                    logger.info("│ [0] 意图分析: 无需检索知识库")
            except Exception as e:
                logger.warning(f"│ [0] IntentAnalyzer 降级: {e}")

            result_matches = await _multi_query_search(session, sub_queries, limit)

            logger.info(
                "│ [1] 检索完成",
                match_count=len(result_matches),
            )
            logger.info(f"│     检索关键词: {keywords}")
            logger.info(f"│     子查询数: {len(sub_queries)}")
            logger.info(f"│     找到 {len(result_matches)} 个匹配结果")
            for i, m in enumerate(result_matches[:limit]):
                logger.info(f"│     [{i+1}] {m.name} (ID: {m.skill_id}, 分数: {round(m.score, 2)})")
                if m.description:
                    desc_preview = f"{m.description[:50]}..." if len(m.description) > 50 else m.description
                    logger.info(f"│         描述: {desc_preview}")

            if not result_matches:
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

            skills_info = [
                {
                    "skill_id": m.skill_id,
                    "name": m.name,
                    "description": m.description,
                    "category": m.category,
                    "preview": m.preview[:200] if m.preview else "",
                    "score": round(m.score, 2),
                }
                for m in result_matches[:limit]
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
