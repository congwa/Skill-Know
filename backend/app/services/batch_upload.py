"""批量上传服务

处理批量文件上传和转换。
"""

import asyncio
import uuid
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db_context
from app.core.logging import get_logger
from app.models.document import DocumentStatus
from app.schemas.document import DocumentCreate
from app.services.document import DocumentService
from app.services.document_parser import DocumentParser
from app.services.content_analyzer import ContentAnalyzer
from app.services.skill_generator import SkillGenerator
from app.services.skill import SkillService
from app.services.system_config import SystemConfigService
from app.services.upload_task import (
    task_manager,
    UploadStep,
    StepStatus,
)
from app.models.skill import SkillType
from app.schemas.skill import SkillCreate
from langchain_openai import ChatOpenAI

logger = get_logger("batch_upload")


class BatchUploadService:
    """批量上传服务"""

    def __init__(self, session: AsyncSession):
        self._session = session
        self._document_service = DocumentService(session)
        self._skill_service = SkillService(session)
        self._config_service = SystemConfigService(session)
        self._parser = DocumentParser()
        self._analyzer = ContentAnalyzer()
        self._generator = SkillGenerator()

    async def _get_llm(self) -> ChatOpenAI | None:
        """获取 LLM 实例"""
        try:
            config = await self._config_service.get_llm_config()
            if not config.get("api_key"):
                logger.warning("LLM API Key 未配置")
                return None
            return ChatOpenAI(
                api_key=config["api_key"],
                base_url=config["base_url"],
                model=config["chat_model"],
                temperature=0.7,
            )
        except Exception as e:
            logger.warning(f"获取 LLM 失败: {e}")
            return None

    async def start_batch_upload(
        self,
        files: list[UploadFile],
        folder_id: str | None = None,
        use_llm: bool = True,
    ) -> str:
        """启动批量上传任务

        Args:
            files: 上传的文件列表
            folder_id: 目标文件夹 ID
            use_llm: 是否使用 LLM

        Returns:
            task_id
        """
        # 创建任务
        filenames = [f.filename or "unknown" for f in files]
        task_id = task_manager.create_task(filenames)

        # 获取文件 ID 映射
        file_ids = task_manager.get_file_ids(task_id)
        file_map = dict(zip(file_ids, files))

        # 获取 LLM（如果需要）
        llm = await self._get_llm() if use_llm else None

        # 保存文件内容到内存（因为 UploadFile 不能跨任务）
        file_contents = {}
        for file_id, file in file_map.items():
            content = await file.read()
            file_contents[file_id] = {
                "filename": file.filename or "unknown",
                "content": content,
            }

        # 启动后台处理（使用独立的数据库会话）
        asyncio.create_task(
            self._process_files_with_new_session(
                task_id, file_contents, folder_id, use_llm
            )
        )

        logger.info(f"批量上传任务已启动: {task_id}, 文件数: {len(files)}")

        return task_id

    async def _process_files_with_new_session(
        self,
        task_id: str,
        file_contents: dict[str, dict],
        folder_id: str | None,
        use_llm: bool,
    ) -> None:
        """使用新的数据库会话处理所有文件（后台任务安全）

        Args:
            task_id: 任务 ID
            file_contents: 文件 ID 到内容的映射
            folder_id: 目标文件夹 ID
            use_llm: 是否使用 LLM
        """
        async with get_db_context() as session:
            try:
                # 在新会话中获取 LLM
                llm = None
                if use_llm:
                    try:
                        config_service = SystemConfigService(session)
                        config = await config_service.get_llm_config()
                        if config.get("api_key"):
                            llm = ChatOpenAI(
                                api_key=config["api_key"],
                                base_url=config["base_url"],
                                model=config["chat_model"],
                                temperature=0.7,
                            )
                    except Exception as e:
                        logger.warning(f"获取 LLM 失败: {e}")

                # 处理每个文件
                for file_id, file_data in file_contents.items():
                    try:
                        await self._process_single_file_with_session(
                            session=session,
                            task_id=task_id,
                            file_id=file_id,
                            filename=file_data["filename"],
                            content=file_data["content"],
                            folder_id=folder_id,
                            llm=llm,
                        )
                    except Exception as e:
                        logger.exception(f"文件处理失败: {file_data['filename']}")
                        await task_manager.update_progress(
                            task_id=task_id,
                            file_id=file_id,
                            step=UploadStep.FAILED,
                            status=StepStatus.FAILED,
                            error=str(e),
                        )

                # 提交所有更改
                await session.commit()
            except Exception as e:
                logger.exception(f"批量处理失败: {e}")
                await session.rollback()

    async def _process_single_file_with_session(
        self,
        session: AsyncSession,
        task_id: str,
        file_id: str,
        filename: str,
        content: bytes,
        folder_id: str | None,
        llm: ChatOpenAI | None,
    ) -> None:
        """处理单个文件（使用传入的会话）

        Args:
            session: 数据库会话
            task_id: 任务 ID
            file_id: 文件 ID
            filename: 文件名
            content: 文件内容
            folder_id: 目标文件夹 ID
            llm: LLM 实例
        """
        # Step 1: 上传
        await task_manager.update_progress(
            task_id=task_id,
            file_id=file_id,
            step=UploadStep.UPLOADING,
            status=StepStatus.RUNNING,
            progress=0,
            message="正在保存文件...",
        )

        # 保存文件
        upload_dir = settings.ensure_data_dir() / "uploads"
        upload_dir.mkdir(exist_ok=True)

        file_ext = Path(filename).suffix if filename else ""
        file_uuid = str(uuid.uuid4())
        file_path = upload_dir / f"{file_uuid}{file_ext}"

        with open(file_path, "wb") as f:
            f.write(content)

        await task_manager.update_progress(
            task_id=task_id,
            file_id=file_id,
            step=UploadStep.UPLOADING,
            status=StepStatus.COMPLETED,
            progress=100,
            message="文件保存完成",
        )

        # Step 2: 解析
        await task_manager.update_progress(
            task_id=task_id,
            file_id=file_id,
            step=UploadStep.PARSING,
            status=StepStatus.RUNNING,
            progress=0,
            message="正在解析文档...",
        )

        try:
            parsed = await self._parser.parse(str(file_path))
        except Exception as e:
            await task_manager.update_progress(
                task_id=task_id,
                file_id=file_id,
                step=UploadStep.FAILED,
                status=StepStatus.FAILED,
                error=f"解析失败: {str(e)}",
            )
            return

        await task_manager.update_progress(
            task_id=task_id,
            file_id=file_id,
            step=UploadStep.PARSING,
            status=StepStatus.COMPLETED,
            progress=100,
            message=f"解析完成: {parsed.word_count} 字",
        )

        # Step 3: 分析
        await task_manager.update_progress(
            task_id=task_id,
            file_id=file_id,
            step=UploadStep.ANALYZING,
            status=StepStatus.RUNNING,
            progress=0,
            message="正在分析内容...",
        )

        analysis = await self._analyzer.analyze(parsed)

        await task_manager.update_progress(
            task_id=task_id,
            file_id=file_id,
            step=UploadStep.ANALYZING,
            status=StepStatus.COMPLETED,
            progress=100,
            message=f"分析完成: {analysis.doc_type}",
        )

        # Step 4: 生成 Skill
        await task_manager.update_progress(
            task_id=task_id,
            file_id=file_id,
            step=UploadStep.GENERATING,
            status=StepStatus.RUNNING,
            progress=0,
            message="正在生成 Skill...",
        )

        generated = await self._generator.generate(parsed, analysis, llm)

        await task_manager.update_progress(
            task_id=task_id,
            file_id=file_id,
            step=UploadStep.GENERATING,
            status=StepStatus.COMPLETED,
            progress=100,
            message=f"Skill 生成完成: {generated.name}",
        )

        # Step 5: 保存
        await task_manager.update_progress(
            task_id=task_id,
            file_id=file_id,
            step=UploadStep.SAVING,
            status=StepStatus.RUNNING,
            progress=0,
            message="正在保存到数据库...",
        )

        # 创建服务实例（使用传入的会话）
        document_service = DocumentService(session)
        skill_service = SkillService(session)

        # 创建文档记录
        doc_data = DocumentCreate(
            title=parsed.title or filename,
            folder_id=folder_id,
        )
        document = await document_service.create_document(
            data=doc_data,
            filename=filename,
            file_path=str(file_path),
            file_size=len(content),
            file_type=file_ext.lstrip(".") or "unknown",
            content=parsed.content,
        )

        # 创建 Skill 记录
        skill_data = SkillCreate(
            name=generated.name,
            description=generated.description,
            content=generated.content,
            category=generated.category,
            trigger_keywords=generated.trigger_keywords,
            trigger_intents=generated.trigger_intents,
            always_apply=generated.always_apply,
            folder_id=folder_id,
            priority=generated.priority,
        )
        skill = await skill_service.create_skill(
            data=skill_data,
            skill_type=SkillType.DOCUMENT,
            source_document_id=document.id,
        )

        # 更新文档元数据
        document.extra_metadata = document.extra_metadata or {}
        document.extra_metadata["skill_id"] = skill.id
        document.extra_metadata["converted"] = True
        document.status = DocumentStatus.COMPLETED
        await session.flush()

        await task_manager.update_progress(
            task_id=task_id,
            file_id=file_id,
            step=UploadStep.SAVING,
            status=StepStatus.COMPLETED,
            progress=100,
            message="保存完成",
        )

        # 完成
        await task_manager.update_progress(
            task_id=task_id,
            file_id=file_id,
            step=UploadStep.COMPLETED,
            status=StepStatus.COMPLETED,
            progress=100,
            message="处理完成",
            result={
                "document_id": document.id,
                "skill_id": skill.id,
                "skill_name": skill.name,
            },
        )

        logger.info(
            f"文件处理完成: {filename} -> document_id={document.id}, skill_id={skill.id}"
        )
