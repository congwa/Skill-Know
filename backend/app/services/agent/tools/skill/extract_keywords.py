"""关键词提取工具

从用户问题中提取关键词，用于后续的知识库检索。
这是查询知识库的第一步。
"""

from __future__ import annotations

import json
import uuid
from typing import Annotated

from langchain.tools import ToolRuntime, tool
from pydantic import Field

from app.core.logging import get_logger
from app.schemas.events import StreamEventType
from app.services.streaming.context import ChatContext

logger = get_logger("tool.extract_keywords")


@tool
async def extract_keywords(
    runtime: ToolRuntime[ChatContext, dict],
    query: Annotated[str, Field(description="用户的问题或查询文本")],
) -> str:
    """从用户问题中提取关键词，用于后续的知识库检索。

    分析用户的自然语言问题，使用 LLM 提取出最相关的关键词，
    这些关键词将用于在知识库中检索相关技能。

    Args:
        query: 用户的问题或查询文本

    Returns:
        提取的关键词列表的 JSON 字符串

    Examples:
        >>> extract_keywords(query="如何拍出好看的照片")
        '{"keywords": ["拍照", "摄影", "构图"], "intent": "学习摄影技巧"}'
    """
    tool_call_id = uuid.uuid4().hex
    
    # 从 runtime.context 获取 emitter
    emitter = getattr(runtime.context, "emitter", None) if runtime.context else None
    
    if emitter and hasattr(emitter, "aemit"):
        await emitter.aemit(
            StreamEventType.TOOL_START.value,
            {
                "tool_call_id": tool_call_id,
                "name": "extract_keywords",
                "input": {"query": query},
            },
        )

    logger.info(
        "┌── 工具: extract_keywords 开始 ──┐",
        query=query[:100],
    )

    try:
        from langchain_openai import ChatOpenAI
        from app.core.database import get_db_context
        from app.services.skill_search.intent import IntentExtractor
        from app.services.system_config import SystemConfigService
        
        # 获取 LLM 实例（通过 SystemConfigService 获取配置）
        async with get_db_context() as session:
            config_service = SystemConfigService(session)
            llm_config = await config_service.get_llm_config()
            llm = ChatOpenAI(
                api_key=llm_config["api_key"],
                base_url=llm_config["base_url"],
                model=llm_config["chat_model"],
            )
        
        intent_extractor = IntentExtractor(llm=llm)
        
        # 提取关键词
        result = await intent_extractor.extract(query)

        logger.info(
            "│ [1] 关键词提取完成",
            query=query,
            keywords=result.keywords,
            intent=result.intent,
            entities=result.entities,
        )
        logger.info(f"│     原始问题: {query}")
        logger.info(f"│     提取关键词: {result.keywords}")
        logger.info(f"│     用户意图: {result.intent}")
        if result.entities:
            logger.info(f"│     识别实体: {result.entities}")

        result_data = {
            "keywords": result.keywords,
            "intent": result.intent,
            "entities": result.entities,
        }

        if emitter and hasattr(emitter, "aemit"):
            await emitter.aemit(
                StreamEventType.TOOL_END.value,
                {
                    "tool_call_id": tool_call_id,
                    "name": "extract_keywords",
                    "status": "success",
                    "output_preview": result_data,
                },
            )

        logger.info(
            "└── 工具: extract_keywords 结束 ──┘",
            keywords_count=len(result.keywords),
        )

        return json.dumps(result_data, ensure_ascii=False)

    except Exception as e:
        if emitter and hasattr(emitter, "aemit"):
            await emitter.aemit(
                StreamEventType.TOOL_END.value,
                {
                    "tool_call_id": tool_call_id,
                    "name": "extract_keywords",
                    "status": "error",
                    "error": str(e),
                },
            )
        logger.exception("关键词提取失败", error=str(e))
        return json.dumps({"error": f"关键词提取失败: {e}"}, ensure_ascii=False)
