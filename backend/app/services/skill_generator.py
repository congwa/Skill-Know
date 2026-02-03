"""Skill 生成器

使用 LLM 将文档内容转换为结构化 Skill。
"""

import json
import re
from dataclasses import dataclass, field
from typing import Any

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from app.core.logging import get_logger
from app.models.skill import SkillCategory
from app.services.document_parser import ParsedDocument
from app.services.content_analyzer import ContentAnalysis

logger = get_logger("skill_generator")


@dataclass
class GeneratedSkill:
    """生成的 Skill"""
    name: str
    description: str
    content: str
    trigger_keywords: list[str] = field(default_factory=list)
    trigger_intents: list[str] = field(default_factory=list)
    category: SkillCategory = SkillCategory.RETRIEVAL
    always_apply: bool = False
    priority: int = 100


SKILL_GENERATION_PROMPT = '''你是一个 Skill 创建专家。根据以下文档内容，创建一个结构化的 Skill。

## 输入文档信息
- 标题: {title}
- 类型: {doc_type}
- 字数: {word_count}
- 复杂度: {complexity}
- 关键概念: {concepts}
- 主题: {topics}

## 文档内容
{content}

## Skill 创建原则

1. **简洁为王** - 只保留 AI 不知道的专有知识，删除通用知识
2. **渐进式披露** - 核心内容精炼，避免冗余
3. **明确触发条件** - description 中清楚描述何时使用此 Skill
4. **保留关键示例** - 代码示例和具体案例要保留

## 输出格式

请输出 JSON 格式：

```json
{{
  "name": "skill-name-kebab-case",
  "description": "详细描述此 Skill 的功能和用途。明确说明何时触发：当用户询问 XXX、需要 YYY 时使用此技能。",
  "content": "精炼后的技能内容（Markdown 格式），保留核心知识点和关键示例",
  "trigger_keywords": ["关键词1", "关键词2", "关键词3"],
  "trigger_intents": ["learn", "search"],
  "category": "retrieval",
  "always_apply": false,
  "priority": 100
}}
```

## 注意事项

1. name 使用 kebab-case 格式（如 python-decorator-guide）
2. content 必须是精炼后的版本：
   - 如果原文 > 3000 字，精炼到 1500 字以内
   - 移除冗余解释，保留核心知识点
   - 保留最有价值的代码示例
3. trigger_keywords 提取 3-8 个最相关的触发词
4. trigger_intents 可选值: learn, search, create, compare, ask
5. category 可选值: search, prompt, retrieval, tool, workflow
6. always_apply 通常为 false，除非是基础必备知识

只输出 JSON，不要其他内容。'''


class SkillGenerator:
    """Skill 生成器"""

    def __init__(self, llm: ChatOpenAI | None = None):
        self._llm = llm

    async def generate(
        self,
        document: ParsedDocument,
        analysis: ContentAnalysis,
        llm: ChatOpenAI | None = None,
    ) -> GeneratedSkill:
        """生成 Skill

        Args:
            document: 解析后的文档
            analysis: 内容分析结果
            llm: LLM 实例（可选，覆盖初始化时的 LLM）

        Returns:
            GeneratedSkill
        """
        llm = llm or self._llm
        
        if not llm:
            # 无 LLM 时使用规则生成
            logger.warning("未提供 LLM，使用规则生成")
            return self._generate_by_rules(document, analysis)

        # 准备内容（如果太长则截断）
        content = document.content
        if len(content) > 15000:
            content = content[:15000] + "\n\n...[内容已截断]..."

        # 构建 prompt
        prompt = SKILL_GENERATION_PROMPT.format(
            title=document.title or "未知标题",
            doc_type=analysis.doc_type,
            word_count=analysis.word_count,
            complexity=analysis.complexity,
            concepts=", ".join(analysis.concepts[:10]),
            topics=", ".join(analysis.topics),
            content=content,
        )

        messages = [
            SystemMessage(content="你是一个专业的 Skill 创建助手，擅长将文档转换为结构化的知识技能。"),
            HumanMessage(content=prompt),
        ]

        try:
            response = await llm.ainvoke(messages)
            result = self._parse_response(str(response.content))
            
            logger.info(
                "Skill 生成完成",
                name=result.name,
                keyword_count=len(result.trigger_keywords),
            )
            
            return result

        except Exception as e:
            logger.exception(f"LLM 生成失败: {e}")
            return self._generate_by_rules(document, analysis)

    def _parse_response(self, response: str) -> GeneratedSkill:
        """解析 LLM 响应"""
        # 提取 JSON
        json_match = re.search(r'\{[\s\S]*\}', response)
        if not json_match:
            raise ValueError("无法从响应中提取 JSON")

        try:
            data = json.loads(json_match.group())
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON 解析失败: {e}")

        # 解析 category
        category_str = data.get("category", "retrieval").lower()
        category_map = {
            "search": SkillCategory.SEARCH,
            "prompt": SkillCategory.PROMPT,
            "retrieval": SkillCategory.RETRIEVAL,
            "tool": SkillCategory.TOOL,
            "workflow": SkillCategory.WORKFLOW,
        }
        category = category_map.get(category_str, SkillCategory.RETRIEVAL)

        return GeneratedSkill(
            name=data.get("name", "unnamed-skill"),
            description=data.get("description", ""),
            content=data.get("content", ""),
            trigger_keywords=data.get("trigger_keywords", []),
            trigger_intents=data.get("trigger_intents", []),
            category=category,
            always_apply=data.get("always_apply", False),
            priority=data.get("priority", 100),
        )

    def _generate_by_rules(
        self,
        document: ParsedDocument,
        analysis: ContentAnalysis,
    ) -> GeneratedSkill:
        """使用规则生成 Skill（无 LLM 时的降级方案）"""
        # 生成名称
        title = document.title or "unknown"
        name = self._to_kebab_case(title)

        # 生成描述
        description = self._generate_description(document, analysis)

        # 精炼内容
        content = self._condense_content(document, analysis)

        # 推断 category
        category = self._infer_category(analysis)

        return GeneratedSkill(
            name=name,
            description=description,
            content=content,
            trigger_keywords=analysis.keywords[:8],
            trigger_intents=self._infer_intents(analysis),
            category=category,
            always_apply=False,
            priority=100,
        )

    def _to_kebab_case(self, text: str) -> str:
        """转换为 kebab-case"""
        # 移除特殊字符
        text = re.sub(r'[^\w\s\u4e00-\u9fff-]', '', text)
        # 空格转连字符
        text = re.sub(r'\s+', '-', text)
        # 小写
        text = text.lower()
        # 限制长度
        return text[:50]

    def _generate_description(
        self,
        document: ParsedDocument,
        analysis: ContentAnalysis,
    ) -> str:
        """生成描述"""
        title = document.title or "文档"
        doc_type = {
            'tutorial': '教程',
            'api': 'API 文档',
            'reference': '参考手册',
            'faq': '常见问题',
            'guide': '指南',
        }.get(analysis.doc_type, '知识文档')

        topics = ", ".join(analysis.topics[:3]) if analysis.topics else "技术"
        keywords = ", ".join(analysis.keywords[:5]) if analysis.keywords else ""

        desc = f"{title} - {topics}相关{doc_type}。"
        if keywords:
            desc += f" 当用户询问 {keywords} 相关问题时触发此技能。"

        return desc

    def _condense_content(
        self,
        document: ParsedDocument,
        analysis: ContentAnalysis,
    ) -> str:
        """精炼内容"""
        content = document.content

        # 如果内容较短，直接返回
        if len(content) <= 2000:
            return content

        # 提取重要部分
        parts = []

        # 1. 保留标题和前言
        lines = content.split('\n')
        intro = '\n'.join(lines[:20])
        parts.append(intro)

        # 2. 保留章节标题
        if document.sections:
            section_titles = "\n## 目录\n"
            for s in document.sections[:10]:
                section_titles += f"- {s.title}\n"
            parts.append(section_titles)

        # 3. 保留代码块
        if analysis.code_blocks:
            code_section = "\n## 代码示例\n"
            for block in analysis.code_blocks[:3]:
                if len(block) <= 500:
                    code_section += f"```\n{block}\n```\n\n"
            parts.append(code_section)

        # 4. 添加关键概念
        if analysis.concepts:
            concepts_section = "\n## 关键概念\n"
            concepts_section += ", ".join(analysis.concepts[:15])
            parts.append(concepts_section)

        condensed = '\n\n'.join(parts)

        # 限制最终长度
        if len(condensed) > 3000:
            condensed = condensed[:3000] + "\n\n...[内容已精炼]..."

        return condensed

    def _infer_category(self, analysis: ContentAnalysis) -> SkillCategory:
        """推断 Skill 类别"""
        if analysis.doc_type == 'api':
            return SkillCategory.TOOL
        elif analysis.doc_type == 'tutorial':
            return SkillCategory.RETRIEVAL
        elif analysis.doc_type == 'guide':
            return SkillCategory.PROMPT
        else:
            return SkillCategory.RETRIEVAL

    def _infer_intents(self, analysis: ContentAnalysis) -> list[str]:
        """推断触发意图"""
        intents = []

        if analysis.doc_type == 'tutorial':
            intents.append('learn')
        if analysis.doc_type == 'api':
            intents.append('search')
        if analysis.doc_type == 'faq':
            intents.append('ask')
        if analysis.doc_type == 'guide':
            intents.extend(['learn', 'search'])

        return intents or ['search']
