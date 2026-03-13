"""向量后端抽象基类"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class VectorRecord:
    """向量记录"""
    id: str
    uri: str
    text: str
    vector: list[float] | None = None
    context_type: str = ""
    level: int = 0
    meta: dict[str, Any] = field(default_factory=dict)
    active_count: int = 0
    score: float = 0.0


class VectorBackend(ABC):
    """向量存储后端抽象接口

    所有向量数据库实现都应继承此类，提供统一的 CRUD + 检索接口。
    """

    @abstractmethod
    async def upsert(self, record: VectorRecord) -> None:
        """插入或更新向量记录"""

    @abstractmethod
    async def query(
        self,
        vector: list[float],
        context_type: str | None = None,
        level: int = 0,
        limit: int = 10,
        threshold: float = 0.0,
    ) -> list[VectorRecord]:
        """向量相似度查询"""

    @abstractmethod
    async def text_query(
        self,
        text: str,
        context_type: str | None = None,
        level: int = 0,
        limit: int = 10,
        threshold: float = 0.0,
    ) -> list[VectorRecord]:
        """文本相似度查询（降级方案）"""

    @abstractmethod
    async def delete(self, uri: str, level: int | None = None) -> int:
        """删除记录。返回删除的数量。"""

    @abstractmethod
    async def update_activity(self, uri: str) -> None:
        """更新活跃度"""

    @abstractmethod
    async def count(self, context_type: str | None = None) -> int:
        """统计记录数"""

    @abstractmethod
    async def get_by_uri(self, uri: str, level: int | None = None) -> list[VectorRecord]:
        """按 URI 获取记录"""
