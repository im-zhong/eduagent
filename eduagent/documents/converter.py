"""Document conversion helpers."""
from __future__ import annotations

from pathlib import Path

from eduagent.parser.parser_service import chunk_markdown, convert_document_to_markdown


async def parse_document_to_chunks(path: Path) -> tuple[str, list[str]]:
    markdown = await convert_document_to_markdown(path)
    chunks = chunk_markdown(markdown)
    return markdown, [chunk.text for chunk in chunks]


async def parse_document_to_markdown(path: Path) -> tuple[str, int]:
    markdown, chunks = await parse_document_to_chunks(path)
    return markdown, len(chunks)
