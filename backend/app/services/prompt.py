"""提示词服务"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.prompt import Prompt, PromptCategory
from app.schemas.prompt import (
    PromptCreate,
    PromptUpdate,
    PromptResponse,
    PromptSource,
)

logger = get_logger("prompt_service")


# 默认提示词定义
DEFAULT_PROMPTS: dict[str, dict] = {
    "system.chat": {
        "category": PromptCategory.CHAT.value,
        "name": "系统聊天提示词",
        "description": "主聊天系统的系统提示词",
        "content": """你是一个基于 Skill-driven 的智能知识库助手。

## 工作原理
系统会根据用户问题自动匹配相关的知识技能（Skills），并将匹配到的技能内容提供给你。
你需要基于这些技能内容来回答用户的问题。

## 回答原则
1. **基于知识回答**：优先使用提供的技能内容来回答问题
2. **诚实透明**：如果提供的技能内容无法回答问题，请明确告知
3. **渐进式披露**：先给出核心答案，用户追问时再提供更多细节
4. **格式规范**：使用 Markdown 格式，保持结构清晰

## 输出风格
- 简洁准确，避免冗余
- 适当使用列表、代码块等格式
- 必要时引用技能内容的关键信息""",
        "variables": [],
    },
    "skill.search": {
        "category": PromptCategory.SEARCH.value,
        "name": "技能搜索提示词",
        "description": "用于技能搜索的提示词",
        "content": """根据用户的查询，搜索相关的技能。

搜索策略：
1. 首先尝试关键词匹配
2. 然后进行语义相似度搜索
3. 返回最相关的结果

查询: {query}""",
        "variables": ["query"],
    },
    "skill.generator": {
        "category": PromptCategory.SKILL.value,
        "name": "技能生成提示词",
        "description": "从文档生成技能的提示词",
        "content": """根据以下文档内容，提取并生成一个技能描述。

文档内容：
{content}

请按以下格式输出：
- 名称：简洁的技能名称
- 描述：技能的简要描述
- 关键词：触发此技能的关键词列表
- 内容：技能的详细内容（Markdown 格式）""",
        "variables": ["content"],
    },
    "classification.document": {
        "category": PromptCategory.CLASSIFICATION.value,
        "name": "文档分类提示词",
        "description": "用于文档自动分类的提示词",
        "content": """根据以下文档内容，判断其最合适的分类。

文档标题：{title}
文档内容：{content}

可选分类：
- 技术文档
- 业务流程
- 操作指南
- 知识科普
- 其他

请只返回分类名称。""",
        "variables": ["title", "content"],
    },
}


class PromptService:
    """提示词服务

    支持默认值 + 数据库覆盖的模式。
    """

    def __init__(self, session: AsyncSession):
        self._session = session

    async def get(self, key: str) -> PromptResponse | None:
        """获取提示词（优先数据库，fallback 默认值）"""
        db_prompt = await self._get_from_db(key)
        default = DEFAULT_PROMPTS.get(key)

        if db_prompt:
            return PromptResponse(
                key=db_prompt.key,
                category=db_prompt.category.value,
                name=db_prompt.name,
                description=db_prompt.description,
                content=db_prompt.content,
                variables=db_prompt.variables or [],
                source=PromptSource.CUSTOM,
                is_active=db_prompt.is_active,
                default_content=default["content"] if default else None,
                created_at=db_prompt.created_at,
                updated_at=db_prompt.updated_at,
            )
        elif default:
            return PromptResponse(
                key=key,
                category=default["category"],
                name=default["name"],
                description=default.get("description"),
                content=default["content"],
                variables=default.get("variables", []),
                source=PromptSource.DEFAULT,
                is_active=True,
                default_content=None,
                created_at=None,
                updated_at=None,
            )

        return None

    async def get_content(self, key: str, **kwargs) -> str | None:
        """获取提示词内容字符串（支持变量替换）"""
        prompt = await self.get(key)
        if not prompt:
            return None

        content = prompt.content
        if kwargs and prompt.variables:
            try:
                content = content.format(**kwargs)
            except KeyError as e:
                logger.warning("提示词格式化失败", key=key, missing_var=str(e))

        return content

    async def list_all(
        self, category: str | None = None, include_inactive: bool = False
    ) -> list[PromptResponse]:
        """列出所有提示词"""
        result: list[PromptResponse] = []

        # 获取数据库中的自定义提示词
        stmt = select(Prompt)
        if category:
            stmt = stmt.where(Prompt.category == category)
        if not include_inactive:
            stmt = stmt.where(Prompt.is_active == True)

        db_result = await self._session.execute(stmt)
        db_prompts = {p.key: p for p in db_result.scalars().all()}

        # 合并默认值和数据库值
        for key, default in DEFAULT_PROMPTS.items():
            if category and default["category"] != category:
                continue

            if key in db_prompts:
                db_prompt = db_prompts[key]
                if not include_inactive and not db_prompt.is_active:
                    continue
                result.append(
                    PromptResponse(
                        key=key,
                        category=db_prompt.category.value,
                        name=db_prompt.name,
                        description=db_prompt.description,
                        content=db_prompt.content,
                        variables=db_prompt.variables or [],
                        source=PromptSource.CUSTOM,
                        is_active=db_prompt.is_active,
                        default_content=default["content"],
                        created_at=db_prompt.created_at,
                        updated_at=db_prompt.updated_at,
                    )
                )
            else:
                result.append(
                    PromptResponse(
                        key=key,
                        category=default["category"],
                        name=default["name"],
                        description=default.get("description"),
                        content=default["content"],
                        variables=default.get("variables", []),
                        source=PromptSource.DEFAULT,
                        is_active=True,
                        default_content=None,
                        created_at=None,
                        updated_at=None,
                    )
                )

        result.sort(key=lambda p: p.key)
        return result

    async def update(self, key: str, data: PromptUpdate) -> PromptResponse:
        """更新提示词"""
        db_prompt = await self._get_from_db(key)
        default = DEFAULT_PROMPTS.get(key)

        if db_prompt:
            if data.name is not None:
                db_prompt.name = data.name
            if data.description is not None:
                db_prompt.description = data.description
            if data.content is not None:
                db_prompt.content = data.content
            if data.is_active is not None:
                db_prompt.is_active = data.is_active

            await self._session.flush()
            logger.info("更新提示词", key=key)
        else:
            if not default:
                raise ValueError(f"提示词 {key} 不存在")

            db_prompt = Prompt(
                key=key,
                category=PromptCategory(default["category"]),
                name=data.name or default["name"],
                description=data.description or default.get("description"),
                content=data.content or default["content"],
                variables=default.get("variables", []),
                is_active=data.is_active if data.is_active is not None else True,
            )
            self._session.add(db_prompt)
            await self._session.flush()
            logger.info("创建自定义提示词", key=key)

        return PromptResponse(
            key=db_prompt.key,
            category=db_prompt.category.value,
            name=db_prompt.name,
            description=db_prompt.description,
            content=db_prompt.content,
            variables=db_prompt.variables or [],
            source=PromptSource.CUSTOM,
            is_active=db_prompt.is_active,
            default_content=default["content"] if default else None,
            created_at=db_prompt.created_at,
            updated_at=db_prompt.updated_at,
        )

    async def reset(self, key: str) -> PromptResponse:
        """重置提示词为默认值"""
        default = DEFAULT_PROMPTS.get(key)
        if not default:
            raise ValueError(f"提示词 {key} 无默认值")

        db_prompt = await self._get_from_db(key)
        if db_prompt:
            await self._session.delete(db_prompt)
            await self._session.flush()
            logger.info("重置提示词为默认值", key=key)

        return PromptResponse(
            key=key,
            category=default["category"],
            name=default["name"],
            description=default.get("description"),
            content=default["content"],
            variables=default.get("variables", []),
            source=PromptSource.DEFAULT,
            is_active=True,
            default_content=None,
            created_at=None,
            updated_at=None,
        )

    async def _get_from_db(self, key: str) -> Prompt | None:
        """从数据库获取提示词"""
        stmt = select(Prompt).where(Prompt.key == key)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()
