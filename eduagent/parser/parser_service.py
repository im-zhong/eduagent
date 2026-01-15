"""Async document parsing service based on pypandoc."""
from __future__ import annotations

from pathlib import Path
import re

import anyio
from pydantic import BaseModel
import pypandoc


class DocumentNotFoundError(Exception):
    """Raised when the document file does not exist."""


class DocumentParseError(Exception):
    """Raised when pypandoc fails to parse the document."""


class ParsedChunk(BaseModel):
    index: int
    text: str


class ParsedDocument(BaseModel):
    path: str
    chunks: list[ParsedChunk]

    @property
    def chunk_count(self) -> int:
        return len(self.chunks)


def split_markdown(markdown: str) -> list[str]:
    normalized = markdown.replace("\r\n", "\n").strip()
    if not normalized:
        return []
    parts = re.split(r"\n{2,}", normalized)
    return [part.strip() for part in parts if part.strip()]


_MARKDOWN_SUFFIXES = {".md", ".markdown"}
_PANDOC_FORMATS = {
    ".txt": "markdown",
    ".docx": "docx",
    ".pdf": "pdf",
}


def _read_markdown(path: Path) -> str:
    # TODO(zhangzhong): detect and handle non-utf-8 encodings.
    return path.read_text(encoding="utf-8")


def _convert_to_markdown(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in _MARKDOWN_SUFFIXES:
        return _read_markdown(path)
    input_format = _PANDOC_FORMATS.get(suffix)
    if input_format:
        return pypandoc.convert_file(str(path), "md", format=input_format)
    return pypandoc.convert_file(str(path), "md")


async def parse_document(path: Path) -> ParsedDocument:
    if not path.exists():
        raise DocumentNotFoundError(f"Document file not found: {path}")

    try:
        # pypandoc invokes the pandoc binary, so the heavy work runs outside the GIL.
        # We still offload to a thread to avoid blocking the event loop.
        markdown = await anyio.to_thread.run_sync(_convert_to_markdown, path)
    except RuntimeError as exc:
        raise DocumentParseError(str(exc)) from exc

    chunks = split_markdown(markdown)
    parsed_chunks = [ParsedChunk(index=i, text=chunk) for i, chunk in enumerate(chunks)]
    return ParsedDocument(path=str(path), chunks=parsed_chunks)
