"""技能处理管线

参考 OpenViking SkillProcessor，提供标准化的技能处理流水线：
1. Parse   — 通过 ParserRegistry 解析输入
2. Analyze — 用 LLM 生成 L0 (abstract) 和 L1 (overview)
3. Store   — 写入数据库（三层内容）
4. Index   — 异步生成向量嵌入并写入向量索引
"""

from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context import Context, ContextType, build_skill_uri
from app.core.logging import get_logger
from app.models.skill import Skill, SkillCategory, SkillType
from app.parse import get_registry
from app.schemas.skill import SkillCreate

logger = get_logger("skill_processor")

OVERVIEW_GENERATION_PROMPT = """请根据以下技能信息生成一个结构化的概览（约 500 字以内）。

## 技能名称
{name}

## 技能描述
{description}

## 技能内容
{content}

## 输出要求
1. 用 Markdown 格式
2. 包含：功能概述、核心知识点、使用场景
3. 简洁精炼，突出重点
4. 不超过 500 字"""

ABSTRACT_GENERATION_PROMPT = """请用一句话概括以下技能的核心功能（不超过 100 字）。

技能名称：{name}
技能描述：{description}

只输出概括文本，不要其他内容。"""


@dataclass
class ProcessResult:
    """处理结果"""
    success: bool
    skill: Skill | None = None
    context: Context | None = None
    error: str | None = None


class SkillProcessor:
    """技能处理管线

    统一的技能处理入口，支持从多种来源（文件/字符串/dict）创建技能。
    入库前自动执行 LLM 辅助去重（CREATE / SKIP / MERGE）。
    """

    def __init__(self, session: AsyncSession, llm: Any = None, vector_store: Any = None):
        self._session = session
        self._registry = get_registry()
        self._llm = llm
        self._vector_store = vector_store

    async def process(
        self,
        data: Any,
        skill_type: SkillType = SkillType.USER,
        category: SkillCategory = SkillCategory.RETRIEVAL,
        source_document_id: str | None = None,
        folder_id: str | None = None,
    ) -> ProcessResult:
        """处理并存储技能

        Args:
            data: 技能数据（文件路径 / 字符串内容 / dict）
            skill_type: 技能类型
            category: 技能分类
            source_document_id: 来源文档 ID
            folder_id: 文件夹 ID
        """
        try:
            # Step 1: Parse
            skill_dict = await self._parse_input(data)
            logger.info("解析完成", name=skill_dict.get("name", "unknown"))

            # Step 2: Generate L0/L1
            abstract = await self._generate_abstract(skill_dict)
            overview = await self._generate_overview(skill_dict)

            # Step 2.5: Dedup check — 在入库前判断是否与已有知识重复
            dedup_result = await self._dedup_check(
                title=skill_dict["name"],
                abstract=abstract,
                content=skill_dict.get("content", ""),
            )

            if dedup_result and dedup_result.decision.value == "skip":
                logger.info("去重: 跳过重复知识", name=skill_dict["name"], reason=dedup_result.reason)
                return ProcessResult(success=True, error=f"SKIP: {dedup_result.reason}")

            if dedup_result and dedup_result.decision.value == "merge" and dedup_result.merge_target_uri:
                return await self._execute_merge(
                    dedup_result=dedup_result,
                    skill_dict=skill_dict,
                    abstract=abstract,
                    overview=overview,
                    category=category,
                )

            # Step 3: Store (CREATE path)
            uri = build_skill_uri(skill_dict["name"])

            skill_data = SkillCreate(
                name=skill_dict["name"],
                description=skill_dict.get("description", ""),
                content=skill_dict.get("content", ""),
                category=category,
                trigger_keywords=skill_dict.get("trigger_keywords", []),
                trigger_intents=skill_dict.get("trigger_intents", []),
                folder_id=folder_id,
            )

            from app.services.skill import SkillService
            skill_service = SkillService(self._session)
            skill = await skill_service.create_skill(
                data=skill_data,
                skill_type=skill_type,
                source_document_id=source_document_id,
            )

            skill.abstract = abstract
            skill.overview = overview
            skill.uri = uri
            await self._session.flush()

            # Step 4: Build Context for indexing
            context = Context(
                uri=uri,
                parent_uri="sk://skills",
                context_type=ContextType.SKILL,
                abstract=abstract,
                overview=overview,
                content=skill_dict.get("content", ""),
                meta={
                    "name": skill_dict["name"],
                    "description": skill_dict.get("description", ""),
                    "category": category.value,
                    "skill_id": skill.id,
                },
            )

            # Step 5: Enqueue for async indexing
            await self._enqueue_indexing(context)

            logger.info(
                "技能处理完成",
                skill_id=skill.id,
                uri=uri,
                has_abstract=bool(abstract),
                has_overview=bool(overview),
            )

            return ProcessResult(success=True, skill=skill, context=context)

        except Exception as e:
            logger.exception("技能处理失败", error=str(e))
            return ProcessResult(success=False, error=str(e))

    async def _enqueue_indexing(self, context: Context) -> None:
        """将 Context 入队异步向量索引"""
        try:
            from app.core.queue import QueueTask, TaskType
            from app.core.service import get_service

            service = get_service()
            if service.queue_manager:
                await service.queue_manager.enqueue(
                    QueueTask(
                        task_type=TaskType.SKILL_INDEXING,
                        payload={"context": context.to_dict()},
                    )
                )
                logger.info("已入队异步索引", uri=context.uri)
        except Exception as e:
            logger.warning(f"入队索引失败（非阻塞）: {e}")

    async def _dedup_check(self, title: str, abstract: str, content: str):
        """执行去重检查（需要 LLM 和 VectorStore 均可用）"""
        if not self._llm or not self._vector_store:
            return None
        try:
            from app.services.knowledge_deduplicator import KnowledgeDeduplicator
            deduplicator = KnowledgeDeduplicator(llm=self._llm, vector_store=self._vector_store)
            return await deduplicator.check(title=title, abstract=abstract, content=content)
        except Exception as e:
            logger.warning(f"去重检查失败，跳过: {e}")
            return None

    async def _execute_merge(
        self,
        dedup_result,
        skill_dict: dict,
        abstract: str,
        overview: str,
        category: SkillCategory,
    ) -> ProcessResult:
        """执行 MERGE 操作：将新知识合并到已有 Skill"""
        target_uri = dedup_result.merge_target_uri
        logger.info("去重: 合并到已有知识", target_uri=target_uri, name=skill_dict["name"])

        stmt = select(Skill).where(Skill.uri == target_uri, Skill.is_active.is_(True))
        result = await self._session.execute(stmt)
        target_skill = result.scalar_one_or_none()

        if not target_skill:
            logger.warning("合并目标不存在，降级为创建", target_uri=target_uri)
            uri = build_skill_uri(skill_dict["name"])
            skill_data = SkillCreate(
                name=skill_dict["name"],
                description=skill_dict.get("description", ""),
                content=skill_dict.get("content", ""),
                category=category,
                trigger_keywords=skill_dict.get("trigger_keywords", []),
                trigger_intents=skill_dict.get("trigger_intents", []),
            )
            from app.services.skill import SkillService
            skill_service = SkillService(self._session)
            skill = await skill_service.create_skill(data=skill_data, skill_type=SkillType.USER)
            skill.abstract = abstract
            skill.overview = overview
            skill.uri = uri
            await self._session.flush()
            context = Context(
                uri=uri, parent_uri="sk://skills", context_type=ContextType.SKILL,
                abstract=abstract, overview=overview, content=skill_dict.get("content", ""),
                meta={"name": skill_dict["name"], "skill_id": skill.id, "category": category.value},
            )
            return ProcessResult(success=True, skill=skill, context=context)

        if dedup_result.merged_content:
            target_skill.content = dedup_result.merged_content
        else:
            target_skill.content += f"\n\n---\n\n{skill_dict.get('content', '')}"

        target_skill.overview = overview or target_skill.overview
        await self._session.flush()

        context = Context(
            uri=target_skill.uri or "",
            parent_uri="sk://skills",
            context_type=ContextType.SKILL,
            abstract=target_skill.abstract or abstract,
            overview=target_skill.overview or "",
            content=target_skill.content,
            meta={
                "name": target_skill.name,
                "skill_id": target_skill.id,
                "category": target_skill.category.value if target_skill.category else "",
                "merged_from": skill_dict["name"],
            },
        )

        # 记录合并溯源关联
        try:
            from app.models.context_relation import ContextRelation
            relation = ContextRelation(
                source_uri=target_skill.uri or "",
                target_uri=build_skill_uri(skill_dict["name"]),
                relation_type="merged_from",
                reason=f"Knowledge '{skill_dict['name']}' merged into '{target_skill.name}'",
            )
            self._session.add(relation)
            await self._session.flush()
        except Exception as e:
            logger.warning(f"记录合并关联失败（非阻塞）: {e}")

        await self._enqueue_indexing(context)

        logger.info("合并完成", target_id=target_skill.id, target_name=target_skill.name)
        return ProcessResult(success=True, skill=target_skill, context=context)

    async def _parse_input(self, data: Any) -> dict[str, Any]:
        """解析多种输入格式"""
        if isinstance(data, dict):
            return data

        if isinstance(data, str):
            from pathlib import Path
            path = Path(data)
            if path.exists() and path.is_file():
                result = await self._registry.parse(path)
                return {
                    "name": result.title or path.stem,
                    "description": (result.content[:200] + "...") if len(result.content) > 200 else result.content,
                    "content": result.content,
                }
            # Raw content string
            return {
                "name": data[:50].strip().replace("\n", " "),
                "description": data[:200],
                "content": data,
            }

        raise ValueError(f"Unsupported data type: {type(data)}")

    async def _generate_abstract(self, skill_dict: dict[str, Any]) -> str:
        """生成 L0 摘要"""
        from app.core.config import settings
        if not settings.AUTO_GENERATE_L0:
            desc = skill_dict.get("description", "")
            return desc[:200] if desc else skill_dict.get("name", "")

        if self._llm:
            try:
                from langchain_core.messages import HumanMessage

                from app.prompts import render_prompt
                prompt = render_prompt("semantic.abstract_generation", {
                    "name": skill_dict.get("name", ""),
                    "description": skill_dict.get("description", ""),
                })
                if not prompt:
                    prompt = ABSTRACT_GENERATION_PROMPT.format(
                        name=skill_dict.get("name", ""),
                        description=skill_dict.get("description", ""),
                    )
                response = await self._llm.ainvoke([HumanMessage(content=prompt)])
                return str(response.content).strip()[:200]
            except Exception as e:
                logger.warning(f"LLM abstract 生成失败，使用降级方案: {e}")

        desc = skill_dict.get("description", "")
        return desc[:200] if desc else skill_dict.get("name", "")

    async def _generate_overview(self, skill_dict: dict[str, Any]) -> str:
        """生成 L1 概览"""
        from app.core.config import settings
        if not settings.AUTO_GENERATE_L1:
            return self._generate_overview_by_rules(skill_dict)

        if self._llm:
            try:
                from langchain_core.messages import HumanMessage

                from app.prompts import render_prompt
                content = skill_dict.get("content", "")
                if len(content) > 10000:
                    content = content[:10000] + "\n...[已截断]..."
                prompt = render_prompt("semantic.overview_generation", {
                    "name": skill_dict.get("name", ""),
                    "description": skill_dict.get("description", ""),
                    "content": content,
                })
                if not prompt:
                    prompt = OVERVIEW_GENERATION_PROMPT.format(
                        name=skill_dict.get("name", ""),
                        description=skill_dict.get("description", ""),
                        content=content,
                    )
                response = await self._llm.ainvoke([HumanMessage(content=prompt)])
                return str(response.content).strip()
            except Exception as e:
                logger.warning(f"LLM overview 生成失败，使用降级方案: {e}")

        return self._generate_overview_by_rules(skill_dict)

    @staticmethod
    def _generate_overview_by_rules(skill_dict: dict[str, Any]) -> str:
        """规则降级生成概览"""
        name = skill_dict.get("name", "未知技能")
        desc = skill_dict.get("description", "")
        content = skill_dict.get("content", "")

        parts = [f"# {name}", ""]
        if desc:
            parts.append(f"## 功能概述\n{desc}")
            parts.append("")

        lines = content.split("\n")
        headings = [line for line in lines if line.startswith("#")]
        if headings:
            parts.append("## 知识结构")
            for h in headings[:10]:
                parts.append(f"- {h.lstrip('#').strip()}")
            parts.append("")

        overview = "\n".join(parts)
        if len(overview) > 2000:
            overview = overview[:2000] + "\n\n...[已精炼]..."
        return overview
