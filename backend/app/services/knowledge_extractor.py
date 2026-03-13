"""对话知识提取

参考 OpenViking MemoryExtractor + SessionCompressor 模式，
在对话结束时自动从对话中提取有价值的知识点并存入知识库。

提取的知识分类：
  - FAQ: 用户提出的问题和 AI 的回答
  - CORRECTION: 用户纠正了 AI 的错误回答
  - SUPPLEMENT: 用户补充了知识库中没有的信息

核心流程:
  对话结束 → LLM 提取候选知识 → KnowledgeDeduplicator 去重 → SkillProcessor 入库
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.core.logging import get_logger

logger = get_logger("knowledge_extractor")


class KnowledgeCategory(str, Enum):
    FAQ = "faq"
    CORRECTION = "correction"
    SUPPLEMENT = "supplement"


@dataclass
class CandidateKnowledge:
    """从对话中提取的候选知识"""
    category: KnowledgeCategory
    title: str
    abstract: str
    content: str
    source_conversation_id: str = ""
    keywords: list[str] = field(default_factory=list)


EXTRACTION_PROMPT = """你是 Skill-Know 知识库的知识提取专家。
请分析以下对话，提取出值得保存到知识库的知识点。

## 对话内容
{conversation}

## 提取规则
1. **FAQ** — 用户提出了一个有价值的问题，AI 给出了有用的回答
2. **CORRECTION** — 用户纠正了 AI 的错误信息（这类知识最有价值）
3. **SUPPLEMENT** — 用户主动补充了专业知识或经验信息

## 过滤规则
- 忽略闲聊、打招呼、感谢等无实质内容
- 忽略 AI 的通用性回答（如"我不确定"、"请提供更多信息"）
- 只提取可以复用的、有知识价值的内容
- 如果对话没有任何值得提取的知识，返回空列表

## 输出格式
输出 JSON，不要其他内容：
```json
{{
  "knowledge": [
    {{
      "category": "faq|correction|supplement",
      "title": "简短标题（<20字）",
      "abstract": "一句话摘要（<100字）",
      "content": "完整的知识内容（Markdown 格式）",
      "keywords": ["关键词1", "关键词2"]
    }}
  ]
}}
```

只输出 JSON。如果没有值得提取的知识，输出 {{"knowledge": []}}。"""


class KnowledgeExtractor:
    """对话知识提取器

    从对话历史中提取有价值的知识并入库。
    """

    def __init__(self, llm: Any):
        self._llm = llm

    async def extract(
        self,
        messages: list[dict[str, str]],
        conversation_id: str = "",
    ) -> list[CandidateKnowledge]:
        """从对话消息中提取候选知识。

        Args:
            messages: 对话消息列表 [{"role": "user"/"assistant", "content": "..."}]
            conversation_id: 会话 ID

        Returns:
            提取的候选知识列表
        """
        if len(messages) < 2:
            return []

        conversation_text = self._format_messages(messages)

        from app.prompts import render_prompt
        prompt = render_prompt("compression.knowledge_extraction", {
            "conversation": conversation_text,
        })
        if not prompt:
            prompt = EXTRACTION_PROMPT.format(conversation=conversation_text)

        try:
            response = await self._llm.ainvoke([
                SystemMessage(content="你是知识提取专家。"),
                HumanMessage(content=prompt),
            ])
            parsed = self._parse_response(str(response.content))
        except Exception as e:
            logger.warning(f"LLM 知识提取失败: {e}")
            return []

        if not parsed:
            return []

        candidates = []
        for item in parsed.get("knowledge", []):
            try:
                category = KnowledgeCategory(item.get("category", "faq"))
            except ValueError:
                category = KnowledgeCategory.FAQ

            if not item.get("title") or not item.get("content"):
                continue

            candidates.append(CandidateKnowledge(
                category=category,
                title=item["title"],
                abstract=item.get("abstract", ""),
                content=item["content"],
                source_conversation_id=conversation_id,
                keywords=item.get("keywords", []),
            ))

        logger.info(
            "知识提取完成",
            conversation_id=conversation_id,
            candidate_count=len(candidates),
        )
        return candidates

    @staticmethod
    def _format_messages(messages: list[dict[str, str]]) -> str:
        lines = []
        for m in messages[-20:]:
            role = "用户" if m.get("role") == "user" else "AI"
            lines.append(f"[{role}]: {m.get('content', '')}")
        return "\n".join(lines)

    @staticmethod
    def _parse_response(content: str) -> dict[str, Any] | None:
        content = content.strip()
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        return None


async def extract_and_store_knowledge(
    conversation_id: str,
    messages: list[dict[str, str]],
) -> int:
    """从对话中提取知识并存入数据库（完整流程）。

    Returns:
        成功存入的知识数量
    """
    from app.core.database import get_db_context
    from app.core.service import get_service
    from app.models.skill import SkillCategory, SkillType
    from app.services.skill_processor import SkillProcessor
    from app.services.system_config import SystemConfigService

    stored_count = 0

    try:
        async with get_db_context() as session:
            config_service = SystemConfigService(session)
            llm_config = await config_service.get_llm_config()

            if not llm_config.get("api_key"):
                return 0

            from langchain_openai import ChatOpenAI
            llm = ChatOpenAI(
                api_key=llm_config["api_key"],
                base_url=llm_config["base_url"],
                model=llm_config["chat_model"],
                temperature=0.3,
            )

            extractor = KnowledgeExtractor(llm=llm)
            candidates = await extractor.extract(messages, conversation_id)

            if not candidates:
                return 0

            service = get_service()
            vector_store = service.get_vector_store(session)
            processor = SkillProcessor(session=session, llm=llm, vector_store=vector_store)

            for candidate in candidates:
                result = await processor.process(
                    data={
                        "name": candidate.title,
                        "description": candidate.abstract,
                        "content": candidate.content,
                        "trigger_keywords": candidate.keywords,
                    },
                    skill_type=SkillType.USER,
                    category=SkillCategory.RETRIEVAL,
                )
                if result.success and result.skill:
                    stored_count += 1
                    logger.info(
                        "对话知识已入库",
                        title=candidate.title,
                        category=candidate.category.value,
                        skill_id=result.skill.id,
                    )

            await session.commit()

    except Exception as e:
        logger.warning(f"对话知识提取失败（非阻塞）: {e}")

    return stored_count
