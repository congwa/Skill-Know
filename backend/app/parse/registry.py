"""解析器注册表

参考 OpenViking ParserRegistry，提供基于文件扩展名的自动路由和可扩展注册机制。
"""

import logging
from pathlib import Path
from typing import Callable, Optional, Union

from app.parse.base import BaseParser, ParseResult

logger = logging.getLogger(__name__)


class _CallbackParserWrapper(BaseParser):
    """将回调函数包装为 BaseParser"""

    def __init__(self, extension: str, parse_fn: Callable, name: str = "callback"):
        self._extension = extension
        self._parse_fn = parse_fn
        self._name = name

    @property
    def supported_extensions(self) -> list[str]:
        return [self._extension]

    async def parse(self, source: Union[str, Path], **kwargs) -> ParseResult:
        return await self._parse_fn(source, **kwargs)


class ParserRegistry:
    """文档解析器注册表（单例）

    根据文件扩展名自动路由到对应的解析器。
    支持注册自定义解析器和回调函数。
    """

    def __init__(self):
        self._parsers: dict[str, BaseParser] = {}
        self._extension_map: dict[str, str] = {}
        self._register_builtins()

    def _register_builtins(self) -> None:
        from app.parse.parsers.docx import DocxParser
        from app.parse.parsers.markdown import MarkdownParser
        from app.parse.parsers.pdf import PDFParser
        from app.parse.parsers.text import TextParser

        self.register("text", TextParser())
        self.register("markdown", MarkdownParser())
        self.register("pdf", PDFParser())
        self.register("docx", DocxParser())

    def register(self, name: str, parser: BaseParser) -> None:
        """注册解析器"""
        self._parsers[name] = parser
        for ext in parser.supported_extensions:
            self._extension_map[ext.lower()] = name

    def register_callback(
        self,
        extension: str,
        parse_fn: Callable,
        name: str | None = None,
    ) -> None:
        """注册回调函数作为解析器"""
        if name is None:
            name = f"callback{extension}"
        wrapper = _CallbackParserWrapper(extension, parse_fn, name=name)
        self.register(name, wrapper)
        logger.info(f"Registered callback parser '{name}' for {extension}")

    def unregister(self, name: str) -> None:
        """移除解析器"""
        if name in self._parsers:
            parser = self._parsers[name]
            for ext in parser.supported_extensions:
                if self._extension_map.get(ext.lower()) == name:
                    del self._extension_map[ext.lower()]
            del self._parsers[name]

    def get_parser(self, name: str) -> Optional[BaseParser]:
        return self._parsers.get(name)

    def get_parser_for_file(self, path: Union[str, Path]) -> Optional[BaseParser]:
        """根据文件扩展名获取对应解析器"""
        ext = Path(str(path)).suffix.lower()
        parser_name = self._extension_map.get(ext)
        if parser_name:
            return self._parsers.get(parser_name)
        return None

    async def parse(self, source: Union[str, Path], **kwargs) -> ParseResult:
        """解析文件或字符串

        自动根据扩展名选择解析器，未知类型降级为文本解析。
        """
        source_str = str(source)
        is_potential_path = len(source_str) <= 1024 and "\n" not in source_str

        if is_potential_path:
            path = Path(source)
            if path.exists() and path.is_file():
                parser = self.get_parser_for_file(path)
                if parser:
                    return await parser.parse(path, **kwargs)
                return await self._parsers["text"].parse(path, **kwargs)

        return await self._parsers["text"].parse_content(source_str, **kwargs)

    def list_parsers(self) -> list[str]:
        return list(self._parsers.keys())

    def list_supported_extensions(self) -> list[str]:
        return list(self._extension_map.keys())


_default_registry: Optional[ParserRegistry] = None


def get_registry() -> ParserRegistry:
    """获取默认解析器注册表（单例）"""
    global _default_registry
    if _default_registry is None:
        _default_registry = ParserRegistry()
    return _default_registry


async def parse(source: Union[str, Path], **kwargs) -> ParseResult:
    """使用默认注册表解析文档"""
    return await get_registry().parse(source, **kwargs)
