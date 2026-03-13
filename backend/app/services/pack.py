"""知识包导出/导入服务

参考 OpenViking OVPack 模式，支持将 Skill + VectorIndex + ContextRelation 打包为 JSON 格式导出，
并支持从 JSON 文件导入恢复。
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.context_relation import ContextRelation
from app.models.skill import Skill, SkillCategory, SkillType
from app.models.vector_index import VectorIndex

logger = get_logger("pack")

PACK_VERSION = "1.0"


class PackService:
    """知识包服务"""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def export_skills(
        self,
        *,
        category: str | None = None,
        folder_id: str | None = None,
        skill_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        """导出技能数据包。

        Args:
            category: 按分类过滤
            folder_id: 按文件夹过滤
            skill_ids: 指定技能 ID 列表

        Returns:
            可序列化的 dict（pack 格式）
        """
        stmt = select(Skill).where(Skill.type != SkillType.SYSTEM)

        if skill_ids:
            stmt = stmt.where(Skill.id.in_(skill_ids))
        if category:
            stmt = stmt.where(Skill.category == category)
        if folder_id:
            stmt = stmt.where(Skill.folder_id == folder_id)

        result = await self._session.execute(stmt)
        skills = list(result.scalars().all())

        if not skills:
            return self._empty_pack()

        uris = [s.uri for s in skills if s.uri]

        vectors = await self._export_vectors(uris)
        relations = await self._export_relations(uris)

        pack = {
            "version": PACK_VERSION,
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "skills": [self._skill_to_dict(s) for s in skills],
            "vector_indices": vectors,
            "relations": relations,
            "stats": {
                "skill_count": len(skills),
                "vector_count": len(vectors),
                "relation_count": len(relations),
            },
        }

        logger.info(
            "导出知识包",
            skill_count=len(skills),
            vector_count=len(vectors),
            relation_count=len(relations),
        )
        return pack

    async def import_skills(
        self,
        pack_data: dict[str, Any],
        *,
        skip_duplicates: bool = True,
    ) -> dict[str, Any]:
        """导入技能数据包。

        Args:
            pack_data: pack 格式的 dict
            skip_duplicates: 遇到同名技能时跳过

        Returns:
            导入结果统计
        """
        skills_data = pack_data.get("skills", [])
        vectors_data = pack_data.get("vector_indices", [])
        relations_data = pack_data.get("relations", [])

        imported = 0
        skipped = 0
        errors = 0

        uri_mapping: dict[str, str] = {}

        for skill_dict in skills_data:
            try:
                existing = await self._find_existing_skill(skill_dict["name"])
                if existing and skip_duplicates:
                    if existing.uri and skill_dict.get("uri"):
                        uri_mapping[skill_dict["uri"]] = existing.uri
                    skipped += 1
                    continue

                skill = self._dict_to_skill(skill_dict)
                self._session.add(skill)
                await self._session.flush()

                if skill_dict.get("uri") and skill.uri:
                    uri_mapping[skill_dict["uri"]] = skill.uri
                imported += 1

            except Exception as e:
                logger.warning(f"导入技能失败: {skill_dict.get('name', '?')}, {e}")
                errors += 1

        vector_imported = await self._import_vectors(vectors_data, uri_mapping)
        relation_imported = await self._import_relations(relations_data, uri_mapping)

        result = {
            "imported": imported,
            "skipped": skipped,
            "errors": errors,
            "vectors_imported": vector_imported,
            "relations_imported": relation_imported,
        }
        logger.info("导入知识包完成", **result)
        return result

    def _empty_pack(self) -> dict[str, Any]:
        return {
            "version": PACK_VERSION,
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "skills": [],
            "vector_indices": [],
            "relations": [],
            "stats": {"skill_count": 0, "vector_count": 0, "relation_count": 0},
        }

    def _skill_to_dict(self, skill: Skill) -> dict[str, Any]:
        return {
            "name": skill.name,
            "description": skill.description,
            "uri": skill.uri,
            "type": skill.type.value,
            "category": skill.category.value,
            "abstract": skill.abstract,
            "overview": skill.overview,
            "content": skill.content,
            "trigger_keywords": skill.trigger_keywords or [],
            "trigger_intents": skill.trigger_intents or [],
            "always_apply": skill.always_apply,
            "version": skill.version,
            "author": skill.author,
            "priority": skill.priority,
            "config": skill.config or {},
        }

    def _dict_to_skill(self, data: dict[str, Any]) -> Skill:
        skill_id = str(uuid.uuid4())
        uri = f"sk://skills/{data['name'].lower().replace(' ', '_')}_{skill_id[:8]}"

        return Skill(
            id=skill_id,
            uri=uri,
            name=data["name"],
            description=data.get("description", ""),
            type=SkillType(data.get("type", "user")),
            category=SkillCategory(data.get("category", "prompt")),
            abstract=data.get("abstract"),
            overview=data.get("overview"),
            content=data.get("content", ""),
            trigger_keywords=data.get("trigger_keywords", []),
            trigger_intents=data.get("trigger_intents", []),
            always_apply=data.get("always_apply", False),
            version=data.get("version", "1.0.0"),
            author=data.get("author"),
            priority=data.get("priority", 100),
            config=data.get("config", {}),
        )

    async def _find_existing_skill(self, name: str) -> Skill | None:
        stmt = select(Skill).where(Skill.name == name)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def _export_vectors(self, uris: list[str]) -> list[dict[str, Any]]:
        if not uris:
            return []
        stmt = select(VectorIndex).where(VectorIndex.uri.in_(uris))
        result = await self._session.execute(stmt)
        records = result.scalars().all()
        return [
            {
                "uri": r.uri,
                "context_type": r.context_type,
                "level": r.level,
                "text": r.text,
                "meta": r.meta,
                "active_count": r.active_count,
            }
            for r in records
        ]

    async def _export_relations(self, uris: list[str]) -> list[dict[str, Any]]:
        if not uris:
            return []
        stmt = select(ContextRelation).where(
            or_(
                ContextRelation.source_uri.in_(uris),
                ContextRelation.target_uri.in_(uris),
            )
        )
        result = await self._session.execute(stmt)
        records = result.scalars().all()
        return [
            {
                "source_uri": r.source_uri,
                "target_uri": r.target_uri,
                "relation_type": r.relation_type,
                "reason": r.reason,
            }
            for r in records
        ]

    async def _import_vectors(
        self, vectors_data: list[dict], uri_mapping: dict[str, str]
    ) -> int:
        count = 0
        for v in vectors_data:
            old_uri = v.get("uri", "")
            new_uri = uri_mapping.get(old_uri, old_uri)
            if not new_uri:
                continue

            result = await self._session.execute(
                select(VectorIndex).where(
                    VectorIndex.uri == new_uri,
                    VectorIndex.level == v.get("level", 0),
                )
            )
            if result.scalar_one_or_none():
                continue

            record = VectorIndex(
                uri=new_uri,
                context_type=v.get("context_type", "skill"),
                level=v.get("level", 0),
                text=v.get("text", ""),
                meta=v.get("meta", {}),
                active_count=v.get("active_count", 0),
            )
            self._session.add(record)
            count += 1

        if count:
            await self._session.flush()
        return count

    async def _import_relations(
        self, relations_data: list[dict], uri_mapping: dict[str, str]
    ) -> int:
        count = 0
        for r in relations_data:
            source = uri_mapping.get(r.get("source_uri", ""), r.get("source_uri", ""))
            target = uri_mapping.get(r.get("target_uri", ""), r.get("target_uri", ""))
            if not source or not target:
                continue

            relation = ContextRelation(
                source_uri=source,
                target_uri=target,
                relation_type=r.get("relation_type", "related_to"),
                reason=r.get("reason", "imported"),
            )
            self._session.add(relation)
            count += 1

        if count:
            await self._session.flush()
        return count
