"""文档解析模块

提供可扩展的文档解析注册表，支持多格式文档的自动路由和解析。
"""

from app.parse.base import BaseParser, ParsedSection, ParseResult
from app.parse.registry import ParserRegistry, get_registry, parse

__all__ = [
    "BaseParser",
    "ParseResult",
    "ParsedSection",
    "ParserRegistry",
    "get_registry",
    "parse",
]
