"""技能服务"""

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context import build_skill_uri
from app.core.logging import get_logger
from app.models.skill import Skill, SkillCategory, SkillType
from app.schemas.skill import SkillCreate, SkillUpdate

logger = get_logger("skill_service")


class SkillService:
    """技能服务"""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def create_skill(
        self,
        data: SkillCreate,
        skill_type: SkillType = SkillType.USER,
        source_document_id: str | None = None,
    ) -> Skill:
        """创建技能"""
        uri = build_skill_uri(data.name)
        abstract = data.description[:200] if data.description else ""

        skill = Skill(
            name=data.name,
            description=data.description,
            uri=uri,
            abstract=abstract,
            type=skill_type,
            category=data.category,
            content=data.content,
            trigger_keywords=data.trigger_keywords,
            trigger_intents=data.trigger_intents,
            always_apply=data.always_apply,
            folder_id=data.folder_id,
            priority=data.priority,
            config=data.config,
            source_document_id=source_document_id,
        )
        self._session.add(skill)
        await self._session.flush()
        logger.info("创建技能", skill_id=skill.id, name=skill.name, type=skill_type.value)
        return skill

    async def update_skill(self, skill_id: str, data: SkillUpdate) -> Skill | None:
        """更新技能"""
        skill = await self.get_skill(skill_id)
        if not skill or not skill.is_editable:
            return None

        if data.name is not None:
            skill.name = data.name
        if data.description is not None:
            skill.description = data.description
        if data.category is not None:
            skill.category = data.category
        if data.content is not None:
            skill.content = data.content
        if data.trigger_keywords is not None:
            skill.trigger_keywords = data.trigger_keywords
        if data.trigger_intents is not None:
            skill.trigger_intents = data.trigger_intents
        if data.always_apply is not None:
            skill.always_apply = data.always_apply
        if data.folder_id is not None:
            skill.folder_id = data.folder_id
        if data.priority is not None:
            skill.priority = data.priority
        if data.is_active is not None:
            skill.is_active = data.is_active
        if data.config is not None:
            skill.config = data.config

        await self._session.flush()
        return skill

    async def delete_skill(self, skill_id: str) -> bool:
        """删除技能及其关联的向量索引和关联记录"""
        skill = await self.get_skill(skill_id)
        if not skill or not skill.is_deletable:
            return False

        uri = skill.uri
        if uri:
            await self._cleanup_vector_index(uri)
            await self._cleanup_relations(uri)

        await self._session.delete(skill)
        await self._session.flush()
        logger.info("删除技能", skill_id=skill_id, uri=uri)
        return True

    async def _cleanup_vector_index(self, uri: str) -> None:
        """清理技能关联的向量索引"""
        try:
            from sqlalchemy import delete as sql_delete

            from app.models.vector_index import VectorIndex

            stmt = sql_delete(VectorIndex).where(VectorIndex.uri == uri)
            result = await self._session.execute(stmt)
            if result.rowcount:
                logger.info("清理向量索引", uri=uri, deleted=result.rowcount)
        except Exception as e:
            logger.warning(f"清理向量索引失败（非阻塞）: {e}")

    async def _cleanup_relations(self, uri: str) -> None:
        """清理技能关联的上下文关系"""
        try:
            from sqlalchemy import delete as sql_delete

            from app.models.context_relation import ContextRelation

            stmt = sql_delete(ContextRelation).where(
                or_(
                    ContextRelation.source_uri == uri,
                    ContextRelation.target_uri == uri,
                )
            )
            result = await self._session.execute(stmt)
            if result.rowcount:
                logger.info("清理上下文关联", uri=uri, deleted=result.rowcount)
        except Exception as e:
            logger.warning(f"清理上下文关联失败（非阻塞）: {e}")

    async def get_skill(self, skill_id: str) -> Skill | None:
        """获取技能"""
        stmt = select(Skill).where(Skill.id == skill_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_skill_by_name(self, name: str) -> Skill | None:
        """根据名称获取技能"""
        stmt = select(Skill).where(Skill.name == name)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_skills(
        self,
        skill_type: SkillType | None = None,
        category: SkillCategory | None = None,
        folder_id: str | None = None,
        is_active: bool | None = True,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Skill], int]:
        """列出技能"""
        stmt = select(Skill)

        if skill_type is not None:
            stmt = stmt.where(Skill.type == skill_type)
        if category is not None:
            stmt = stmt.where(Skill.category == category)
        if folder_id is not None:
            stmt = stmt.where(Skill.folder_id == folder_id)
        if is_active is not None:
            stmt = stmt.where(Skill.is_active == is_active)

        # 计算总数
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self._session.execute(count_stmt)).scalar() or 0

        # 分页排序
        stmt = stmt.order_by(Skill.priority, Skill.created_at.desc())
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)

        result = await self._session.execute(stmt)
        skills = list(result.scalars().all())

        return skills, total

    async def search_skills(
        self,
        query: str,
        category: SkillCategory | None = None,
        skill_type: SkillType | None = None,
        limit: int = 20,
    ) -> list[Skill]:
        """搜索技能"""
        stmt = select(Skill).where(
            Skill.is_active == True,
            or_(
                Skill.name.ilike(f"%{query}%"),
                Skill.description.ilike(f"%{query}%"),
                Skill.content.ilike(f"%{query}%"),
            ),
        )

        if category is not None:
            stmt = stmt.where(Skill.category == category)
        if skill_type is not None:
            stmt = stmt.where(Skill.type == skill_type)

        stmt = stmt.order_by(Skill.priority).limit(limit)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_active_skills(self) -> list[Skill]:
        """获取所有激活的技能"""
        stmt = (
            select(Skill)
            .where(Skill.is_active == True)
            .order_by(Skill.priority, Skill.created_at)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_always_apply_skills(self) -> list[Skill]:
        """获取始终应用的技能"""
        stmt = (
            select(Skill)
            .where(Skill.is_active == True, Skill.always_apply == True)
            .order_by(Skill.priority)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_skills_by_keyword(self, keyword: str) -> list[Skill]:
        """根据关键词获取技能"""
        # SQLite JSON 查询
        stmt = select(Skill).where(
            Skill.is_active == True,
            Skill.trigger_keywords.contains(keyword),
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def move_skill(self, skill_id: str, folder_id: str | None) -> Skill | None:
        """移动技能到文件夹"""
        skill = await self.get_skill(skill_id)
        if not skill or not skill.is_editable:
            return None

        skill.folder_id = folder_id
        await self._session.flush()
        logger.info("移动技能", skill_id=skill_id, folder_id=folder_id)
        return skill
