"""纯文本解析器"""

from pathlib import Path
from typing import Any, Union

from app.parse.base import BaseParser, ParseResult


class TextParser(BaseParser):
    """纯文本文件解析器"""

    @property
    def supported_extensions(self) -> list[str]:
        return [".txt", ".text", ".log", ".csv", ".tsv"]

    async def parse(self, source: Union[str, Path], **kwargs: Any) -> ParseResult:
        path = Path(source)
        content = path.read_text(encoding="utf-8")
        lines = content.split("\n")
        title = lines[0].strip() if lines else None

        return ParseResult(
            content=content,
            title=title,
            source_format="text",
            parser_name="TextParser",
            metadata={
                "file_size": path.stat().st_size,
                "line_count": len(lines),
            },
        )

    async def parse_content(self, content: str, **kwargs: Any) -> ParseResult:
        lines = content.split("\n")
        return ParseResult(
            content=content,
            title=lines[0].strip() if lines else None,
            source_format="text",
            parser_name="TextParser",
        )
