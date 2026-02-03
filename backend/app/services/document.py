"""文档服务"""

import hashlib
from pathlib import Path

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.models.document import Document, DocumentFolder, DocumentStatus
from app.schemas.document import (
    DocumentCreate,
    DocumentUpdate,
    DocumentFolderCreate,
    DocumentFolderUpdate,
)

logger = get_logger("document_service")


class DocumentService:
    """文档服务"""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def create_folder(self, data: DocumentFolderCreate) -> DocumentFolder:
        """创建文件夹"""
        folder = DocumentFolder(
            name=data.name,
            description=data.description,
            parent_id=data.parent_id,
        )
        self._session.add(folder)
        await self._session.flush()
        logger.info("创建文件夹", folder_id=folder.id, name=folder.name)
        return folder

    async def update_folder(
        self, folder_id: str, data: DocumentFolderUpdate
    ) -> DocumentFolder | None:
        """更新文件夹"""
        folder = await self.get_folder(folder_id)
        if not folder:
            return None

        if data.name is not None:
            folder.name = data.name
        if data.description is not None:
            folder.description = data.description
        if data.parent_id is not None:
            folder.parent_id = data.parent_id
        if data.sort_order is not None:
            folder.sort_order = data.sort_order

        await self._session.flush()
        return folder

    async def delete_folder(self, folder_id: str) -> bool:
        """删除文件夹"""
        folder = await self.get_folder(folder_id)
        if not folder or folder.is_system:
            return False

        await self._session.delete(folder)
        await self._session.flush()
        logger.info("删除文件夹", folder_id=folder_id)
        return True

    async def get_folder(self, folder_id: str) -> DocumentFolder | None:
        """获取文件夹"""
        stmt = select(DocumentFolder).where(DocumentFolder.id == folder_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_folders(
        self, parent_id: str | None = None
    ) -> list[DocumentFolder]:
        """列出文件夹"""
        stmt = select(DocumentFolder).where(DocumentFolder.parent_id == parent_id)
        stmt = stmt.order_by(DocumentFolder.sort_order, DocumentFolder.name)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def create_document(
        self,
        data: DocumentCreate,
        filename: str,
        file_path: str,
        file_size: int,
        file_type: str,
        content: str | None = None,
    ) -> Document:
        """创建文档"""
        content_hash = None
        if content:
            content_hash = hashlib.sha256(content.encode()).hexdigest()

        document = Document(
            title=data.title,
            description=data.description,
            filename=filename,
            file_path=file_path,
            file_size=file_size,
            file_type=file_type,
            content=content,
            content_hash=content_hash,
            status=DocumentStatus.PENDING if not content else DocumentStatus.COMPLETED,
            folder_id=data.folder_id,
            tags=data.tags,
        )
        self._session.add(document)
        await self._session.flush()
        logger.info("创建文档", document_id=document.id, title=document.title)
        return document

    async def update_document(
        self, document_id: str, data: DocumentUpdate
    ) -> Document | None:
        """更新文档"""
        document = await self.get_document(document_id)
        if not document:
            return None

        if data.title is not None:
            document.title = data.title
        if data.description is not None:
            document.description = data.description
        if data.folder_id is not None:
            document.folder_id = data.folder_id
        if data.category is not None:
            document.category = data.category
        if data.tags is not None:
            document.tags = data.tags

        await self._session.flush()
        return document

    async def delete_document(self, document_id: str) -> bool:
        """删除文档"""
        document = await self.get_document(document_id)
        if not document:
            return False

        await self._session.delete(document)
        await self._session.flush()
        logger.info("删除文档", document_id=document_id)
        return True

    async def get_document(self, document_id: str) -> Document | None:
        """获取文档"""
        stmt = select(Document).where(Document.id == document_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_documents(
        self,
        folder_id: str | None = None,
        category: str | None = None,
        status: DocumentStatus | None = None,
        is_converted: bool | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Document], int]:
        """列出文档
        
        Args:
            is_converted: 过滤是否已转化为技能
        """
        stmt = select(Document)

        if folder_id is not None:
            stmt = stmt.where(Document.folder_id == folder_id)
        if category is not None:
            stmt = stmt.where(Document.category == category)
        if status is not None:
            stmt = stmt.where(Document.status == status)
        if is_converted is not None:
            stmt = stmt.where(Document.is_converted == is_converted)

        # 计算总数
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self._session.execute(count_stmt)).scalar() or 0

        # 分页
        stmt = stmt.order_by(Document.created_at.desc())
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)

        result = await self._session.execute(stmt)
        documents = list(result.scalars().all())

        return documents, total

    async def search_documents(
        self, query: str, limit: int = 20
    ) -> list[Document]:
        """搜索文档（全文搜索）"""
        stmt = select(Document).where(
            Document.title.ilike(f"%{query}%")
            | Document.content.ilike(f"%{query}%")
            | Document.description.ilike(f"%{query}%")
        )
        stmt = stmt.limit(limit)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def update_document_content(
        self,
        document_id: str,
        content: str,
        status: DocumentStatus = DocumentStatus.COMPLETED,
    ) -> Document | None:
        """更新文档内容"""
        document = await self.get_document(document_id)
        if not document:
            return None

        document.content = content
        document.content_hash = hashlib.sha256(content.encode()).hexdigest()
        document.status = status

        await self._session.flush()
        return document

    async def move_document(
        self, document_id: str, folder_id: str | None
    ) -> Document | None:
        """移动文档到文件夹"""
        document = await self.get_document(document_id)
        if not document:
            return None

        document.folder_id = folder_id
        await self._session.flush()
        logger.info("移动文档", document_id=document_id, folder_id=folder_id)
        return document
