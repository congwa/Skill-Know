"""Word 文档解析器"""

import re
from pathlib import Path
from typing import Any, Union

from app.parse.base import BaseParser, ParsedSection, ParseResult


class DocxParser(BaseParser):
    """Word (.docx/.doc) 文件解析器"""

    @property
    def supported_extensions(self) -> list[str]:
        return [".docx", ".doc"]

    async def parse(self, source: Union[str, Path], **kwargs: Any) -> ParseResult:
        try:
            from docx import Document as DocxDocument
        except ImportError:
            raise ImportError("Word 解析需要安装 python-docx: pip install python-docx")

        path = Path(source)
        doc = DocxDocument(path)

        paragraphs: list[str] = []
        title = None
        sections: list[ParsedSection] = []

        for para in doc.paragraphs:
            text = para.text.strip()
            if not text:
                continue
            paragraphs.append(text)

            if para.style and para.style.name:
                style_name = para.style.name.lower()
                if "heading" in style_name or "title" in style_name:
                    level = 1
                    level_match = re.search(r"(\d)", style_name)
                    if level_match:
                        level = int(level_match.group(1))
                    if title is None and level == 1:
                        title = text
                    sections.append(ParsedSection(level=level, title=text, content=""))

        content = "\n\n".join(paragraphs)
        if title is None and paragraphs:
            title = paragraphs[0]

        return ParseResult(
            content=content,
            title=title,
            sections=sections,
            source_format="docx",
            parser_name="DocxParser",
            metadata={
                "file_size": path.stat().st_size,
                "paragraph_count": len(paragraphs),
            },
        )
