"""向量数据库适配层

参考 OpenViking CollectionAdapter 模式，抽象向量存储后端。
支持多种后端实现，通过工厂函数创建。
"""

from app.core.vector_backends.base import VectorBackend
from app.core.vector_backends.factory import create_backend

__all__ = ["VectorBackend", "create_backend"]
