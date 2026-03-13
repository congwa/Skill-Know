"""Markdown 解析器"""

import re
from pathlib import Path
from typing import Any, Union

from app.parse.base import BaseParser, ParsedSection, ParseResult


class MarkdownParser(BaseParser):
    """Markdown 文件解析器"""

    @property
    def supported_extensions(self) -> list[str]:
        return [".md", ".markdown", ".mdown", ".mkd"]

    async def parse(self, source: Union[str, Path], **kwargs: Any) -> ParseResult:
        path = Path(source)
        content = path.read_text(encoding="utf-8")
        return self._parse_content(content, path.stat().st_size)

    async def parse_content(self, content: str, **kwargs: Any) -> ParseResult:
        return self._parse_content(content, len(content.encode("utf-8")))

    def _parse_content(self, content: str, file_size: int) -> ParseResult:
        title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        title = title_match.group(1).strip() if title_match else None
        sections = self._extract_sections(content)
        code_blocks = re.findall(r"```[\w]*\n(.*?)```", content, re.DOTALL)

        return ParseResult(
            content=content,
            title=title,
            sections=sections,
            source_format="markdown",
            parser_name="MarkdownParser",
            metadata={
                "file_size": file_size,
                "code_block_count": len(code_blocks),
                "section_count": len(sections),
            },
        )

    def _extract_sections(self, content: str) -> list[ParsedSection]:
        sections: list[ParsedSection] = []
        pattern = r"^(#{1,6})\s+(.+)$"
        matches = list(re.finditer(pattern, content, re.MULTILINE))

        for i, match in enumerate(matches):
            level = len(match.group(1))
            title = match.group(2).strip()
            start_pos = match.end()
            end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(content)
            section_content = content[start_pos:end_pos].strip()

            sections.append(ParsedSection(
                level=level,
                title=title,
                content=section_content,
                start_pos=match.start(),
                end_pos=end_pos,
            ))

        return sections
