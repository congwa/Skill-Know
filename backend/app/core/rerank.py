"""Rerank 客户端

参考 OpenViking rerank_client，支持模型级重排。
当前支持 OpenAI API 兼容的 rerank 接口（如 Jina Reranker、BGE-reranker）。
"""

from dataclasses import dataclass

import httpx

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("rerank")


@dataclass
class RerankResult:
    """重排结果"""

    index: int
    score: float


class RerankClient:
    """Rerank 客户端

    支持多种 rerank 模型后端（OpenAI 兼容格式）。
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
    ):
        self._api_key = api_key or settings.RERANK_API_KEY
        self._base_url = (base_url or settings.RERANK_BASE_URL).rstrip("/")
        self._model = model or settings.RERANK_MODEL

    @property
    def is_available(self) -> bool:
        return bool(self._api_key and self._model and self._base_url)

    async def rerank(
        self,
        query: str,
        documents: list[str],
        top_n: int | None = None,
    ) -> list[RerankResult]:
        """对文档列表进行重排序。

        Args:
            query: 查询文本
            documents: 待排序的文档文本列表
            top_n: 返回前 N 个结果

        Returns:
            按相关度降序排列的 RerankResult 列表
        """
        if not self.is_available:
            logger.debug("Rerank 不可用，跳过")
            return []

        if not documents:
            return []

        top_n = top_n or len(documents)

        try:
            return await self._do_rerank(query, documents, top_n)
        except Exception as e:
            logger.warning(f"Rerank 请求失败: {e}")
            return []

    async def _do_rerank(
        self, query: str, documents: list[str], top_n: int
    ) -> list[RerankResult]:
        """执行实际的 rerank HTTP 调用（支持重试）"""
        from app.core.retry import async_retry

        async def _call() -> list[RerankResult]:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self._base_url}/rerank",
                    headers={
                        "Authorization": f"Bearer {self._api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self._model,
                        "query": query,
                        "documents": documents,
                        "top_n": top_n,
                    },
                )
                response.raise_for_status()
                data = response.json()

            results = []
            for item in data.get("results", []):
                results.append(
                    RerankResult(
                        index=item["index"],
                        score=item.get("relevance_score", item.get("score", 0.0)),
                    )
                )

            results.sort(key=lambda r: r.score, reverse=True)
            logger.info(
                "Rerank 完成",
                query=query[:50],
                doc_count=len(documents),
                top_n=top_n,
            )
            return results[:top_n]

        return await async_retry(
            _call,
            max_retries=2,
            base_delay=1.0,
            exceptions=(httpx.HTTPError, httpx.TimeoutException),
        )


def get_rerank_client() -> RerankClient | None:
    """获取 Rerank 客户端（仅当配置启用时）"""
    if not settings.RERANK_ENABLED:
        return None
    client = RerankClient()
    if not client.is_available:
        return None
    return client
