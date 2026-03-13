"""PDF 解析器"""

from pathlib import Path
from typing import Any, Union

from app.core.logging import get_logger
from app.parse.base import BaseParser, ParseResult

logger = get_logger("parse.pdf")


class PDFParser(BaseParser):
    """PDF 文件解析器，优先使用 pdfplumber，降级到 pypdf"""

    @property
    def supported_extensions(self) -> list[str]:
        return [".pdf"]

    async def parse(self, source: Union[str, Path], **kwargs: Any) -> ParseResult:
        path = Path(source)

        import importlib.util

        if importlib.util.find_spec("pdfplumber"):
            return self._parse_with_pdfplumber(path)

        if importlib.util.find_spec("pypdf"):
            return self._parse_with_pypdf(path)

        raise ImportError("PDF 解析需要安装 pdfplumber 或 pypdf")

    def _parse_with_pdfplumber(self, path: Path) -> ParseResult:
        import pdfplumber

        parts: list[str] = []
        with pdfplumber.open(path) as pdf:
            page_count = len(pdf.pages)
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    parts.append(text)

        content = "\n\n".join(parts)
        title = self._extract_title(parts)

        return ParseResult(
            content=content,
            title=title,
            source_format="pdf",
            parser_name="PDFParser(pdfplumber)",
            metadata={"file_size": path.stat().st_size, "page_count": page_count},
        )

    def _parse_with_pypdf(self, path: Path) -> ParseResult:
        import pypdf

        parts: list[str] = []
        with open(path, "rb") as f:
            reader = pypdf.PdfReader(f)
            page_count = len(reader.pages)
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    parts.append(text)

        content = "\n\n".join(parts)
        title = self._extract_title(parts)

        return ParseResult(
            content=content,
            title=title,
            source_format="pdf",
            parser_name="PDFParser(pypdf)",
            metadata={"file_size": path.stat().st_size, "page_count": page_count},
        )

    @staticmethod
    def _extract_title(parts: list[str]) -> str | None:
        if not parts:
            return None
        for line in parts[0].split("\n")[:3]:
            stripped = line.strip()
            if len(stripped) > 5:
                return stripped
        return None
