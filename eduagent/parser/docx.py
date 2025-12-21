from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, cast


class _PandocModule(Protocol):
    def convert_file(
        self,
        source_file: str,
        to: str,
        *,
        extra_args: Iterable[str],
    ) -> str: ...

    def download_pandoc(self) -> None: ...


try:
    import pypandoc as _pypandoc
except Exception as exc:  # pragma: no cover - handled at runtime
    _pypandoc: _PandocModule | None = None
    _pypandoc_import_error = exc
else:
    _pypandoc = cast(_PandocModule, _pypandoc)
    _pypandoc_import_error: Exception | None = None


def _convert_file(path: str, extra_args: list[str]) -> str:
    if _pypandoc is None:
        msg = "pypandoc is required to parse DOCX files"
        raise ImportError(msg) from _pypandoc_import_error
    return _pypandoc.convert_file(
        path,
        "markdown",
        extra_args=extra_args,
    )


def _download_pandoc() -> None:
    if _pypandoc is None:
        msg = "pypandoc is required to download pandoc"
        raise ImportError(msg) from _pypandoc_import_error
    _pypandoc.download_pandoc()


@dataclass
class ParsedDoc:
    """Structured result from parsing a DOCX file."""

    source: Path
    markdown: str
    paragraphs: list[str]


class DocxParser:
    """Convert DOCX files to Markdown and chunk into paragraphs."""

    def __init__(
        self,
        *,
        download_pandoc: bool = False,
        extract_media_dir: str | None = None,
    ) -> None:
        self.download_pandoc = download_pandoc
        self.extract_media_dir = extract_media_dir

    def parse(self, file_path: str | Path) -> ParsedDoc:
        path = Path(file_path)
        if not path.exists():
            msg = f"DOCX file not found: {path}"
            raise FileNotFoundError(msg)

        markdown = self._to_markdown(path)
        paragraphs = self._split_paragraphs(markdown)
        return ParsedDoc(source=path, markdown=markdown, paragraphs=paragraphs)

    def _to_markdown(self, path: Path) -> str:
        if _pypandoc is None:
            msg = "pypandoc is required to parse DOCX files"
            raise ImportError(msg) from _pypandoc_import_error

        extra_args: list[str] = []
        if self.extract_media_dir:
            extra_args.append(f"--extract-media={self.extract_media_dir}")

        try:
            return _convert_file(str(path), extra_args)
        except OSError as exc:
            # pypandoc raises OSError when the pandoc binary is missing.
            if "No pandoc was found" in str(exc) and self.download_pandoc:
                _download_pandoc()
                return _convert_file(str(path), extra_args)
            raise

    def _split_paragraphs(self, markdown: str) -> list[str]:
        def _flush(buffer: list[str], acc: list[str]) -> None:
            if buffer:
                acc.append(" ".join(buffer).strip())
                buffer.clear()

        lines: Iterable[str] = markdown.splitlines()
        buffer: list[str] = []
        paragraphs: list[str] = []
        for line in lines:
            stripped = line.strip()
            if stripped:
                buffer.append(stripped)
            else:
                _flush(buffer, paragraphs)
        _flush(buffer, paragraphs)
        return [p for p in paragraphs if p]
