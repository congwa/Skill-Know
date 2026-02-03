"""Skill 相关工具定义

将 Skill 查询流程的每一步都设计为独立工具，供 Agent 自主调用。
"""

import json
from typing import TYPE_CHECKING, Any

from langchain_core.tools import Tool, StructuredTool
from pydantic import BaseModel, Field

from app.core.logging import get_logger

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession
    from app.services.skill_search.intent import IntentExtractor
    from app.services.skill_search.searcher import SkillSearcher

logger = get_logger("agent.tools.skill")


# ==================== 工具参数模型 ====================

class ExtractKeywordsInput(BaseModel):
    """关键词提取工具输入"""
    query: str = Field(description="用户的问题或查询文本")


class SearchSkillsInput(BaseModel):
    """技能检索工具输入"""
    keywords: list[str] = Field(description="用于检索的关键词列表")
    limit: int = Field(default=5, description="最大返回数量")


class GetSkillContentInput(BaseModel):
    """获取技能内容工具输入"""
    skill_id: str = Field(description="技能 ID")


# ==================== 工具工厂函数 ====================

def create_extract_keywords_tool(
    intent_extractor: "IntentExtractor",
    emitter: Any = None,
) -> StructuredTool:
    """创建关键词提取工具
    
    Step 1: LLM 语义分析提取关键词
    """
    async def extract_keywords(query: str) -> str:
        """从用户问题中提取关键词用于知识库检索"""
        try:
            result = await intent_extractor.extract(query)
            
            # 发送事件
            if emitter and hasattr(emitter, "aemit"):
                await emitter.aemit("intent.extracted", {
                    "keywords": result.keywords,
                    "intent": result.intent,
                    "original_query": query,
                })
            
            return json.dumps({
                "keywords": result.keywords,
                "intent": result.intent,
                "entities": result.entities,
            }, ensure_ascii=False)
        except Exception as e:
            logger.exception("关键词提取失败", error=str(e))
            return json.dumps({"error": str(e)})
    
    return StructuredTool.from_function(
        coroutine=extract_keywords,
        name="extract_keywords",
        description="从用户问题中提取关键词，用于后续的知识库检索。这是查询知识库的第一步。",
        args_schema=ExtractKeywordsInput,
    )


def create_search_skills_tool(
    skill_searcher: "SkillSearcher",
    emitter: Any = None,
) -> StructuredTool:
    """创建技能检索工具
    
    Step 2: 根据关键词全文检索知识库
    """
    async def search_skills(keywords: list[str], limit: int = 5) -> str:
        """根据关键词在知识库中检索相关技能"""
        try:
            from app.services.skill_search.query import QueryBuilder, SearchCondition
            
            # 构建查询
            query_builder = QueryBuilder()
            conditions = [
                SearchCondition(field="content", value=kw, weight=1.0)
                for kw in keywords
            ]
            search_query = query_builder.build_from_conditions(conditions, intent="search")
            
            # 执行检索
            result = await skill_searcher.search(search_query)
            
            # 发送事件
            if emitter and hasattr(emitter, "aemit"):
                await emitter.aemit("search.results.found", {
                    "count": len(result.matches),
                    "skills": [
                        {
                            "id": m.skill_id,
                            "name": m.name,
                            "description": m.description,
                            "category": m.category,
                            "score": m.score,
                        }
                        for m in result.matches[:limit]
                    ],
                })
            
            # 返回摘要信息
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
            
            return json.dumps({
                "count": len(skills_info),
                "skills": skills_info,
            }, ensure_ascii=False)
        except Exception as e:
            logger.exception("技能检索失败", error=str(e))
            return json.dumps({"error": str(e)})
    
    return StructuredTool.from_function(
        coroutine=search_skills,
        name="search_skills",
        description="根据关键词在知识库中检索相关技能。需要先调用 extract_keywords 获取关键词。",
        args_schema=SearchSkillsInput,
    )


def create_get_skill_content_tool(
    session: "AsyncSession",
    emitter: Any = None,
) -> StructuredTool:
    """创建获取技能内容工具
    
    Step 3: 获取技能的完整内容
    """
    async def get_skill_content(skill_id: str) -> str:
        """获取指定技能的完整内容"""
        try:
            from app.services.skill import SkillService
            
            skill_service = SkillService(session)
            skill = await skill_service.get(skill_id)
            
            if not skill:
                return json.dumps({"error": f"技能未找到: {skill_id}"})
            
            # 发送事件
            if emitter and hasattr(emitter, "aemit"):
                await emitter.aemit("skill.loaded", {
                    "skill_id": skill.id,
                    "skill_name": skill.name,
                })
            
            return json.dumps({
                "skill_id": skill.id,
                "name": skill.name,
                "description": skill.description,
                "category": skill.category.value if skill.category else None,
                "content": skill.content,
            }, ensure_ascii=False)
        except Exception as e:
            logger.exception("获取技能内容失败", error=str(e))
            return json.dumps({"error": str(e)})
    
    return StructuredTool.from_function(
        coroutine=get_skill_content,
        name="get_skill_content",
        description="获取指定技能的完整内容。需要先调用 search_skills 获取技能 ID。",
        args_schema=GetSkillContentInput,
    )


# ==================== 动态 Skill 内容工具 ====================

def create_skill_content_tool_from_skill(skill: Any) -> Tool:
    """从 Skill 对象创建直接返回内容的工具
    
    这种工具直接返回 Skill 内容，无需额外查询。
    """
    def get_content() -> str:
        return skill.content or f"技能「{skill.name}」暂无内容"
    
    return Tool(
        name=f"skill_{skill.id.replace('-', '_')}",
        description=f"获取「{skill.name}」的知识内容。{skill.description or ''}",
        func=get_content,
    )


def create_skill_content_tools(skills: list[Any]) -> list[Tool]:
    """批量创建 Skill 内容工具"""
    tools = []
    for skill in skills:
        try:
            tool = create_skill_content_tool_from_skill(skill)
            tools.append(tool)
        except Exception as e:
            logger.warning(f"创建 Skill 工具失败: {skill.name}, {e}")
    return tools
