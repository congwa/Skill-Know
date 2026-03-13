"""LLM 辅助的知识去重与合并

参考 OpenViking MemoryDeduplicator，防止同一知识碎片化，自动整合相似文档或冗余 Skill。

核心流程:
  1. 向量初筛: 对即将入库的新 Context，用 Retriever 检索 Top-K 最相似的已有 Context
  2. LLM 决策: 将新旧知识拼接后交给 LLM 判断
  3. 执行动作: CREATE（创建新记录）/ SKIP（完全一致，放弃）/ MERGE（合并到旧记录）
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.core.logging import get_logger

logger = get_logger("knowledge_deduplicator")


class DedupDecision(str, Enum):
    SKIP = "skip"
    CREATE = "create"
    MERGE = "merge"


@dataclass
class DedupResult:
    """去重决策结果"""
    decision: DedupDecision
    reason: str = ""
    merge_target_uri: str | None = None
    merged_content: str | None = None


DEDUP_DECISION_PROMPT = """你是 Skill-Know 知识库的去重助手。请判断一条新知识是否与已有知识重复。

## 新知识
标题: {new_title}
摘要: {new_abstract}
内容:
{new_content}

## 已有相似知识
{existing_knowledge}

## 决策规则
1. **SKIP** — 新知识与某条已有知识内容几乎完全相同（语义和信息覆盖率 > 90%），无需重复入库
2. **CREATE** — 新知识虽有相似之处但包含独特信息，应作为独立条目入库
3. **MERGE** — 新知识与某条已有知识高度相关（覆盖率 50-90%），应将新信息合并到已有条目中

## 输出格式
输出 JSON，不要其他内容:
```json
{{
  "decision": "skip" | "create" | "merge",
  "reason": "简要说明理由",
  "merge_target_index": null,
  "merged_content": null
}}
```

- 如果 decision 为 "merge"，`merge_target_index` 填写应合并到的已有知识序号（1-based），`merged_content` 填写合并后的完整内容（Markdown 格式）。
- 如果 decision 为 "skip" 或 "create"，这两个字段设为 null。

只输出 JSON。"""


class KnowledgeDeduplicator:
    """知识去重器

    使用向量初筛 + LLM 精确决策，在知识入库前自动判断是否重复。
    """

    SIMILARITY_TOP_K = 3
    SIMILARITY_THRESHOLD = 0.3

    def __init__(self, llm: Any, vector_store: Any):
        self._llm = llm
        self._vector_store = vector_store

    async def check(
        self,
        title: str,
        abstract: str,
        content: str,
        context_type: str = "skill",
    ) -> DedupResult:
        """检查新知识是否与已有知识重复。

        Args:
            title: 新知识标题
            abstract: 新知识摘要 (L0)
            content: 新知识内容 (L2)
            context_type: 上下文类型过滤

        Returns:
            DedupResult 包含决策和可能的合并内容
        """
        query_text = f"{title} {abstract}"

        similar = await self._vector_store.search(
            query=query_text,
            context_type=context_type,
            level=0,
            limit=self.SIMILARITY_TOP_K,
            threshold=self.SIMILARITY_THRESHOLD,
        )

        if not similar:
            logger.info("去重检查: 无相似知识，直接创建", title=title)
            return DedupResult(decision=DedupDecision.CREATE, reason="无相似知识")

        existing_formatted = []
        for i, item in enumerate(similar):
            existing_formatted.append(
                f"{i+1}. URI: {item['uri']}\n"
                f"   相似度: {item['score']:.4f}\n"
                f"   摘要: {item['text']}\n"
            )

        from app.prompts import render_prompt
        prompt = render_prompt("compression.dedup_decision", {
            "new_title": title,
            "new_abstract": abstract,
            "new_content": content[:3000],
            "existing_knowledge": "\n".join(existing_formatted),
        })
        if not prompt:
            prompt = DEDUP_DECISION_PROMPT.format(
                new_title=title,
                new_abstract=abstract,
                new_content=content[:3000],
                existing_knowledge="\n".join(existing_formatted),
            )

        try:
            response = await self._llm.ainvoke([
                SystemMessage(content="你是知识库去重专家。"),
                HumanMessage(content=prompt),
            ])
            parsed = self._parse_response(str(response.content))
        except Exception as e:
            logger.warning(f"LLM 去重决策失败，默认创建: {e}")
            return DedupResult(decision=DedupDecision.CREATE, reason=f"LLM 失败: {e}")

        if parsed is None:
            return DedupResult(decision=DedupDecision.CREATE, reason="LLM 返回格式无法解析")

        decision_str = str(parsed.get("decision", "create")).lower().strip()
        decision_map = {
            "skip": DedupDecision.SKIP,
            "create": DedupDecision.CREATE,
            "merge": DedupDecision.MERGE,
        }
        decision = decision_map.get(decision_str, DedupDecision.CREATE)
        reason = parsed.get("reason", "")

        merge_target_uri = None
        merged_content = None

        if decision == DedupDecision.MERGE:
            merge_idx = parsed.get("merge_target_index")
            if isinstance(merge_idx, int) and 1 <= merge_idx <= len(similar):
                merge_target_uri = similar[merge_idx - 1]["uri"]
            elif similar:
                merge_target_uri = similar[0]["uri"]

            merged_content = parsed.get("merged_content")

        result = DedupResult(
            decision=decision,
            reason=reason,
            merge_target_uri=merge_target_uri,
            merged_content=merged_content,
        )

        logger.info(
            "去重决策完成",
            title=title,
            decision=decision.value,
            reason=reason[:100],
            merge_target=merge_target_uri,
        )

        return result

    @staticmethod
    def _parse_response(content: str) -> dict[str, Any] | None:
        content = content.strip()
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        return None
