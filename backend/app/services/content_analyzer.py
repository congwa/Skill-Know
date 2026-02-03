"""内容分析器

分析文档内容，提取关键信息用于 Skill 生成。
"""

import re
from dataclasses import dataclass, field
from typing import Any

from app.core.logging import get_logger
from app.services.document_parser import ParsedDocument

logger = get_logger("content_analyzer")


@dataclass
class ContentAnalysis:
    """内容分析结果"""
    doc_type: str                               # tutorial/api/reference/faq/guide
    concepts: list[str] = field(default_factory=list)  # 关键概念
    keywords: list[str] = field(default_factory=list)  # 关键词
    code_blocks: list[str] = field(default_factory=list)  # 代码块
    structure_summary: str = ""                 # 结构摘要
    complexity: str = "medium"                  # simple/medium/complex
    language: str = "zh"                        # 语言 zh/en
    topics: list[str] = field(default_factory=list)  # 主题
    word_count: int = 0                         # 字数
    estimated_read_time: int = 0                # 预计阅读时间（分钟）


class ContentAnalyzer:
    """内容分析器"""

    # 文档类型关键词
    DOC_TYPE_PATTERNS = {
        'tutorial': [
            r'教程', r'入门', r'学习', r'tutorial', r'learn', r'getting\s*started',
            r'第一步', r'step\s*by\s*step', r'如何', r'how\s*to',
        ],
        'api': [
            r'api', r'接口', r'endpoint', r'请求', r'响应', r'request', r'response',
            r'参数', r'parameter', r'返回值', r'return',
        ],
        'reference': [
            r'参考', r'手册', r'reference', r'manual', r'文档', r'documentation',
            r'规范', r'specification',
        ],
        'faq': [
            r'faq', r'常见问题', r'问答', r'q\s*&\s*a', r'frequently\s*asked',
        ],
        'guide': [
            r'指南', r'guide', r'最佳实践', r'best\s*practice', r'规范',
        ],
    }

    # 技术领域关键词
    TECH_KEYWORDS = {
        'python': ['python', 'pip', 'django', 'flask', 'fastapi', 'pytest'],
        'javascript': ['javascript', 'js', 'node', 'npm', 'react', 'vue', 'angular'],
        'database': ['sql', 'mysql', 'postgresql', 'mongodb', 'redis', '数据库'],
        'devops': ['docker', 'kubernetes', 'k8s', 'ci/cd', 'jenkins', 'github actions'],
        'ai': ['机器学习', 'ml', 'deep learning', '神经网络', 'llm', 'langchain'],
        'web': ['html', 'css', 'http', 'rest', 'graphql', 'websocket'],
    }

    async def analyze(self, document: ParsedDocument) -> ContentAnalysis:
        """分析文档内容

        Args:
            document: 解析后的文档

        Returns:
            ContentAnalysis
        """
        content = document.content
        content_lower = content.lower()

        # 检测文档类型
        doc_type = self._detect_doc_type(content_lower)

        # 提取关键概念
        concepts = self._extract_concepts(content)

        # 提取关键词
        keywords = self._extract_keywords(content)

        # 提取代码块
        code_blocks = self._extract_code_blocks(content)

        # 分析结构
        structure_summary = self._summarize_structure(document)

        # 评估复杂度
        complexity = self._evaluate_complexity(document, code_blocks)

        # 检测语言
        language = self._detect_language(content)

        # 提取主题
        topics = self._extract_topics(content_lower)

        # 计算阅读时间（中文 500 字/分钟，英文 200 词/分钟）
        if language == 'zh':
            estimated_read_time = max(1, document.char_count // 500)
        else:
            estimated_read_time = max(1, document.word_count // 200)

        analysis = ContentAnalysis(
            doc_type=doc_type,
            concepts=concepts,
            keywords=keywords,
            code_blocks=code_blocks,
            structure_summary=structure_summary,
            complexity=complexity,
            language=language,
            topics=topics,
            word_count=document.word_count,
            estimated_read_time=estimated_read_time,
        )

        logger.info(
            "内容分析完成",
            doc_type=doc_type,
            concept_count=len(concepts),
            keyword_count=len(keywords),
            code_block_count=len(code_blocks),
            complexity=complexity,
        )

        return analysis

    def _detect_doc_type(self, content_lower: str) -> str:
        """检测文档类型"""
        scores = {}

        for doc_type, patterns in self.DOC_TYPE_PATTERNS.items():
            score = 0
            for pattern in patterns:
                matches = re.findall(pattern, content_lower, re.IGNORECASE)
                score += len(matches)
            scores[doc_type] = score

        if not scores or max(scores.values()) == 0:
            return 'reference'

        return max(scores, key=scores.get)

    def _extract_concepts(self, content: str) -> list[str]:
        """提取关键概念"""
        concepts = []

        # 提取中文专有名词（连续中文字符 + 英文）
        zh_concepts = re.findall(r'[\u4e00-\u9fff]{2,}[A-Za-z]*[\u4e00-\u9fff]*', content)

        # 提取英文技术术语（大写开头或全大写）
        en_concepts = re.findall(r'\b[A-Z][a-zA-Z]{2,}\b|\b[A-Z]{2,}\b', content)

        # 提取反引号包裹的内容
        code_terms = re.findall(r'`([^`]+)`', content)

        # 合并并去重
        all_concepts = list(set(zh_concepts + en_concepts + code_terms))

        # 过滤常见词
        stopwords = {'The', 'This', 'That', 'These', 'Those', 'And', 'For', 'With'}
        concepts = [c for c in all_concepts if c not in stopwords and len(c) > 1]

        # 按出现频率排序
        freq = {}
        for c in concepts:
            freq[c] = content.count(c)
        
        concepts.sort(key=lambda x: freq.get(x, 0), reverse=True)

        return concepts[:20]  # 最多 20 个

    def _extract_keywords(self, content: str) -> list[str]:
        """提取关键词（用于触发）"""
        keywords = []
        content_lower = content.lower()

        # 检查技术领域关键词
        for domain, domain_keywords in self.TECH_KEYWORDS.items():
            for kw in domain_keywords:
                if kw.lower() in content_lower:
                    keywords.append(kw)

        # 提取高频名词
        words = re.findall(r'\b[\w\u4e00-\u9fff]{2,}\b', content)
        freq = {}
        for w in words:
            w_lower = w.lower()
            if len(w) >= 2 and not w.isdigit():
                freq[w_lower] = freq.get(w_lower, 0) + 1

        # 过滤低频词
        high_freq = [w for w, f in freq.items() if f >= 3]
        high_freq.sort(key=lambda x: freq[x], reverse=True)

        # 合并
        keywords = list(dict.fromkeys(keywords + high_freq[:10]))

        return keywords[:15]

    def _extract_code_blocks(self, content: str) -> list[str]:
        """提取代码块"""
        # Markdown 代码块
        md_blocks = re.findall(r'```[\w]*\n(.*?)```', content, re.DOTALL)

        # 缩进代码块（4 空格或 tab 开头的连续行）
        indent_blocks = re.findall(r'(?:^(?:    |\t).+$\n?)+', content, re.MULTILINE)

        all_blocks = md_blocks + indent_blocks

        # 过滤太短的代码块
        return [b.strip() for b in all_blocks if len(b.strip()) > 20]

    def _summarize_structure(self, document: ParsedDocument) -> str:
        """生成结构摘要"""
        if not document.sections:
            return "无明确章节结构"

        section_titles = [s.title for s in document.sections[:10]]
        
        summary_parts = [f"共 {len(document.sections)} 个章节"]
        if section_titles:
            summary_parts.append(f"主要内容: {', '.join(section_titles[:5])}")

        return "; ".join(summary_parts)

    def _evaluate_complexity(
        self,
        document: ParsedDocument,
        code_blocks: list[str],
    ) -> str:
        """评估文档复杂度"""
        score = 0

        # 字数
        if document.word_count > 5000:
            score += 2
        elif document.word_count > 2000:
            score += 1

        # 章节数
        if len(document.sections) > 10:
            score += 2
        elif len(document.sections) > 5:
            score += 1

        # 代码块数
        if len(code_blocks) > 10:
            score += 2
        elif len(code_blocks) > 3:
            score += 1

        if score >= 4:
            return 'complex'
        elif score >= 2:
            return 'medium'
        else:
            return 'simple'

    def _detect_language(self, content: str) -> str:
        """检测文档语言"""
        # 简单统计中文字符占比
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', content))
        total_chars = len(content)

        if total_chars == 0:
            return 'en'

        chinese_ratio = chinese_chars / total_chars

        return 'zh' if chinese_ratio > 0.1 else 'en'

    def _extract_topics(self, content_lower: str) -> list[str]:
        """提取主题"""
        topics = []

        for domain, keywords in self.TECH_KEYWORDS.items():
            for kw in keywords:
                if kw.lower() in content_lower:
                    topics.append(domain)
                    break

        return list(set(topics))
