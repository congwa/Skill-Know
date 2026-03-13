"""向量后端工厂

根据配置创建对应的向量后端实例。
"""

from typing import Any

from app.core.logging import get_logger
from app.core.vector_backends.base import VectorBackend

logger = get_logger("vector_backend.factory")


def create_backend(backend_type: str = "sqlite", **kwargs: Any) -> VectorBackend:
    """创建向量后端实例。

    Args:
        backend_type: 后端类型 ("sqlite", "qdrant", "chroma")
        **kwargs: 传递给后端构造函数的参数

    Returns:
        VectorBackend 实例
    """
    if backend_type == "sqlite":
        from app.core.vector_backends.sqlite_backend import SQLiteVectorBackend

        session = kwargs.get("session")
        if not session:
            raise ValueError("SQLiteVectorBackend requires 'session' parameter")
        return SQLiteVectorBackend(session=session)

    raise ValueError(f"Unknown vector backend type: {backend_type}")
