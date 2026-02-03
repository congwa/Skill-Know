"""文档转 Skill 服务

整合文档解析、内容分析和 Skill 生成的完整流程。
"""

from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.skill import Skill, SkillType
from app.schemas.skill import SkillCreate
from langchain_openai import ChatOpenAI

from app.services.document import DocumentService
from app.services.document_parser import DocumentParser, ParsedDocument
from app.services.content_analyzer import ContentAnalyzer, ContentAnalysis
from app.services.skill_generator import SkillGenerator, GeneratedSkill
from app.services.skill import SkillService
from app.services.system_config import SystemConfigService

logger = get_logger("document_to_skill")


@dataclass
class ConvertOptions:
    """转换选项"""
    use_llm: bool = True               # 是否使用 LLM 生成
    auto_activate: bool = True         # 自动激活 Skill
    folder_id: str | None = None       # 目标文件夹
    priority: int = 100                # 优先级


@dataclass
class ConvertResult:
    """转换结果"""
    success: bool
    skill: Skill | None = None
    document_id: str | None = None
    error: str | None = None
    analysis: ContentAnalysis | None = None
    generated: GeneratedSkill | None = None


class DocumentToSkillService:
    """文档转 Skill 服务"""

    def __init__(self, session: AsyncSession):
        self._session = session
        self._document_service = DocumentService(session)
        self._skill_service = SkillService(session)
        self._config_service = SystemConfigService(session)
        self._parser = DocumentParser()
        self._analyzer = ContentAnalyzer()
        self._generator = SkillGenerator()

    async def _get_llm(self) -> ChatOpenAI:
        """获取 LLM 实例"""
        config = await self._config_service.get_llm_config()
        return ChatOpenAI(
            api_key=config["api_key"],
            base_url=config["base_url"],
            model=config["chat_model"],
            temperature=0.7,
        )

    async def convert(
        self,
        document_id: str,
        options: ConvertOptions | None = None,
    ) -> ConvertResult:
        """将文档转换为 Skill

        Args:
            document_id: 文档 ID
            options: 转换选项

        Returns:
            ConvertResult
        """
        options = options or ConvertOptions()

        logger.info(f"开始转换文档: {document_id}")

        # 1. 获取文档
        document = await self._document_service.get_document(document_id)
        if not document:
            return ConvertResult(
                success=False,
                document_id=document_id,
                error="文档不存在",
            )

        if not document.file_path:
            return ConvertResult(
                success=False,
                document_id=document_id,
                error="文档文件路径为空",
            )

        try:
            # 2. 解析文档
            parsed = await self._parser.parse(document.file_path)
            logger.info(f"文档解析完成: {parsed.word_count} 字")

            # 3. 分析内容
            analysis = await self._analyzer.analyze(parsed)
            logger.info(f"内容分析完成: 类型={analysis.doc_type}, 概念数={len(analysis.concepts)}")

            # 4. 生成 Skill
            llm = None
            if options.use_llm:
                try:
                    llm = await self._get_llm()
                except Exception as e:
                    logger.warning(f"获取 LLM 失败，使用规则生成: {e}")

            generated = await self._generator.generate(parsed, analysis, llm)
            logger.info(f"Skill 生成完成: {generated.name}")

            # 5. 创建或更新 Skill 记录
            skill = None
            if document.skill_id:
                # 重新转化：更新已有的 Skill
                skill = await self._skill_service.get_skill(document.skill_id)
                if skill:
                    skill.name = generated.name
                    skill.description = generated.description
                    skill.content = generated.content
                    skill.category = generated.category
                    skill.trigger_keywords = generated.trigger_keywords
                    skill.trigger_intents = generated.trigger_intents
                    skill.always_apply = generated.always_apply
                    await self._session.flush()
                    logger.info(f"更新已有 Skill: {skill.id}")
            
            if not skill:
                # 首次转化：创建新 Skill
                skill_data = SkillCreate(
                    name=generated.name,
                    description=generated.description,
                    content=generated.content,
                    category=generated.category,
                    trigger_keywords=generated.trigger_keywords,
                    trigger_intents=generated.trigger_intents,
                    always_apply=generated.always_apply,
                    folder_id=options.folder_id or document.folder_id,
                    priority=options.priority,
                )

                skill = await self._skill_service.create_skill(
                    data=skill_data,
                    skill_type=SkillType.DOCUMENT,
                    source_document_id=document_id,
                )

            # 6. 更新文档状态
            from datetime import datetime
            document.skill_id = skill.id
            document.is_converted = True
            document.converted_at = datetime.now().isoformat()
            await self._session.flush()

            logger.info(f"文档转换成功: document_id={document_id}, skill_id={skill.id}")

            return ConvertResult(
                success=True,
                skill=skill,
                document_id=document_id,
                analysis=analysis,
                generated=generated,
            )

        except Exception as e:
            logger.exception(f"文档转换失败: {e}")
            return ConvertResult(
                success=False,
                document_id=document_id,
                error=str(e),
            )

    async def convert_from_content(
        self,
        content: str,
        title: str | None = None,
        options: ConvertOptions | None = None,
    ) -> ConvertResult:
        """从文本内容直接生成 Skill（不需要先上传文档）

        Args:
            content: 文本内容
            title: 标题
            options: 转换选项

        Returns:
            ConvertResult
        """
        options = options or ConvertOptions()

        logger.info(f"从内容生成 Skill: {len(content)} 字符")

        try:
            # 构造 ParsedDocument
            parsed = ParsedDocument(
                content=content,
                title=title,
                file_type='text',
                word_count=len(content.split()),
                char_count=len(content),
            )

            # 分析内容
            analysis = await self._analyzer.analyze(parsed)

            # 生成 Skill
            llm = None
            if options.use_llm:
                try:
                    llm = await self._get_llm()
                except Exception as e:
                    logger.warning(f"获取 LLM 失败: {e}")

            generated = await self._generator.generate(parsed, analysis, llm)

            # 创建 Skill
            skill_data = SkillCreate(
                name=generated.name,
                description=generated.description,
                content=generated.content,
                category=generated.category,
                trigger_keywords=generated.trigger_keywords,
                trigger_intents=generated.trigger_intents,
                always_apply=generated.always_apply,
                folder_id=options.folder_id,
                priority=options.priority,
            )

            skill = await self._skill_service.create_skill(
                data=skill_data,
                skill_type=SkillType.USER,
            )

            return ConvertResult(
                success=True,
                skill=skill,
                analysis=analysis,
                generated=generated,
            )

        except Exception as e:
            logger.exception(f"内容转换失败: {e}")
            return ConvertResult(
                success=False,
                error=str(e),
            )

    async def batch_convert(
        self,
        document_ids: list[str],
        options: ConvertOptions | None = None,
    ) -> list[ConvertResult]:
        """批量转换文档

        Args:
            document_ids: 文档 ID 列表
            options: 转换选项

        Returns:
            ConvertResult 列表
        """
        results = []
        for doc_id in document_ids:
            result = await self.convert(doc_id, options)
            results.append(result)
        return results
