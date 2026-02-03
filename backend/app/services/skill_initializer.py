"""系统技能初始化器

在应用启动时初始化系统级技能。
"""

from app.core.database import get_db_context
from app.core.logging import get_logger
from app.models.skill import Skill, SkillType, SkillCategory

logger = get_logger("skill_initializer")

# 系统技能定义
SYSTEM_SKILLS = [
    {
        "name": "SQL 搜索",
        "description": "使用 SQL 语句搜索知识库中的技能和文档",
        "category": SkillCategory.SEARCH,
        "content": """# SQL 搜索技能

## 功能描述
通过 SQL 语句搜索知识库中的技能（skills）和文档（documents）。

## 使用方法
调用 `/api/search/sql` 接口，传入 SELECT 语句。

## 可用表
- **skills**: 技能表
  - id, name, description, type, category, content, trigger_keywords, is_active, created_at
- **documents**: 文档表
  - id, title, description, content, category, tags, status, folder_id, created_at
- **document_folders**: 文件夹表
  - id, name, description, parent_id

## 示例查询
```sql
-- 搜索包含关键词的技能
SELECT id, name, description FROM skills WHERE content LIKE '%关键词%';

-- 搜索特定分类的文档
SELECT id, title, content FROM documents WHERE category = '技术文档';

-- 联合搜索
SELECT 'skill' as type, id, name as title FROM skills WHERE name LIKE '%搜索%'
UNION
SELECT 'document' as type, id, title FROM documents WHERE title LIKE '%搜索%';
```

## 安全限制
- 仅支持 SELECT 语句
- 禁止 DROP, DELETE, UPDATE, INSERT, ALTER, CREATE, TRUNCATE 操作
""",
        "trigger_keywords": ["sql", "查询", "搜索数据库"],
        "always_apply": False,
        "priority": 10,
    },
    {
        "name": "知识库搜索",
        "description": "在知识库中搜索相关的技能和文档",
        "category": SkillCategory.SEARCH,
        "content": """# 知识库搜索技能

## 功能描述
在知识库中进行全文搜索，查找相关的技能和文档。

## 使用方法
调用 `/api/search` 接口，传入搜索关键词。

## 参数
- `q`: 搜索关键词（必填）
- `type`: 搜索类型，可选值：skill, document, all（默认）
- `limit`: 返回结果数量限制（默认 20）

## 返回结果
返回匹配的技能和文档列表，包含预览内容。

## 示例
```
GET /api/search?q=Python&type=skill&limit=10
```
""",
        "trigger_keywords": ["搜索", "查找", "找"],
        "always_apply": True,
        "priority": 5,
    },
    {
        "name": "渐进式披露",
        "description": "根据用户需求逐步展示相关信息",
        "category": SkillCategory.PROMPT,
        "content": """# 渐进式披露技能

## 功能描述
根据用户的查询，逐步展示相关信息，避免信息过载。

## 策略
1. **首次响应**：提供简要概述和关键信息
2. **追问时**：提供更详细的内容
3. **深入时**：展示完整的技术细节

## 应用场景
- 用户询问某个概念时，先给出定义，再给出示例
- 用户搜索技能时，先展示匹配列表，再展示详情
- 用户查阅文档时，先展示目录，再展示具体章节

## 实现方式
在搜索结果中提供 `content_preview`（预览）和完整 `content`，
前端可以先展示预览，用户点击后再展示完整内容。
""",
        "trigger_keywords": [],
        "always_apply": True,
        "priority": 1,
    },
]


async def init_system_skills():
    """初始化系统技能"""
    async with get_db_context() as session:
        from sqlalchemy import select

        for skill_data in SYSTEM_SKILLS:
            # 检查是否已存在
            stmt = select(Skill).where(
                Skill.name == skill_data["name"],
                Skill.type == SkillType.SYSTEM,
            )
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()

            if existing:
                # 更新内容（系统技能可以被代码更新）
                existing.description = skill_data["description"]
                existing.content = skill_data["content"]
                existing.trigger_keywords = skill_data["trigger_keywords"]
                existing.always_apply = skill_data["always_apply"]
                existing.priority = skill_data["priority"]
                logger.debug("更新系统技能", name=skill_data["name"])
            else:
                # 创建新技能
                skill = Skill(
                    name=skill_data["name"],
                    description=skill_data["description"],
                    type=SkillType.SYSTEM,
                    category=skill_data["category"],
                    content=skill_data["content"],
                    trigger_keywords=skill_data["trigger_keywords"],
                    always_apply=skill_data["always_apply"],
                    priority=skill_data["priority"],
                    is_active=True,
                )
                session.add(skill)
                logger.info("创建系统技能", name=skill_data["name"])

        await session.commit()
        logger.info("系统技能初始化完成", count=len(SYSTEM_SKILLS))
