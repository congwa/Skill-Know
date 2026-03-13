"""解析器基类和数据结构

参考 OpenViking ParserRegistry 设计，定义统一的解析器协议。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Union


@dataclass
class ParsedSection:
    """文档章节"""
    level: int
    title: str
    content: str
    start_pos: int = 0
    end_pos: int = 0


@dataclass
class ParseResult:
    """解析结果

    统一的文档解析输出格式，包含原始内容、章节结构和元数据。
    """
    content: str
    title: str | None = None
    sections: list[ParsedSection] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    source_format: str = ""
    parser_name: str = ""
    word_count: int = 0
    char_count: int = 0

    def __post_init__(self):
        if not self.word_count:
            self.word_count = len(self.content.split())
        if not self.char_count:
            self.char_count = len(self.content)


class BaseParser(ABC):
    """解析器基类

    所有格式解析器的抽象基类，子类需要实现 supported_extensions 和 parse 方法。
    """

    @property
    @abstractmethod
    def supported_extensions(self) -> list[str]:
        """返回支持的文件扩展名列表 (e.g., ['.txt', '.text'])"""
        ...

    def can_handle(self, source: Union[str, Path]) -> bool:
        """判断是否能处理该文件"""
        ext = Path(str(source)).suffix.lower()
        return ext in self.supported_extensions

    @abstractmethod
    async def parse(self, source: Union[str, Path], **kwargs: Any) -> ParseResult:
        """解析文件

        Args:
            source: 文件路径
            **kwargs: 额外参数

        Returns:
            ParseResult
        """
        ...

    async def parse_content(self, content: str, **kwargs: Any) -> ParseResult:
        """解析字符串内容（可选实现）"""
        return ParseResult(
            content=content,
            source_format="string",
            parser_name=self.__class__.__name__,
        )
