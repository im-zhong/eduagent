from __future__ import annotations

from pathlib import Path

import pytest

from eduagent.parser import DocxParser, ParsedDoc


def test_parse_docx_to_markdown(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    sample = tmp_path / "sample.docx"
    sample.write_text("dummy-content")

    markdown = "# Title\n\nFirst paragraph\n\nSecond paragraph line 1\nline 2"

    def fake_convert(
        _path: str, _to: str, *, extra_args: list[str] | None = None
    ) -> str:
        assert _path == str(sample)
        assert _to == "markdown"
        assert extra_args == []
        return markdown

    monkeypatch.setattr("eduagent.parser.docx.pypandoc.convert_file", fake_convert)

    parser = DocxParser()
    result = parser.parse(sample)

    assert isinstance(result, ParsedDoc)
    assert result.source == sample
    assert result.markdown == markdown
    assert result.paragraphs == [
        "# Title",
        "First paragraph",
        "Second paragraph line 1 line 2",
    ]


def test_missing_file_raises_file_not_found() -> None:
    parser = DocxParser()
    missing = Path("/nonexistent/doc.docx")
    with pytest.raises(FileNotFoundError):
        parser.parse(missing)


def test_download_pandoc_when_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    sample = tmp_path / "sample.docx"
    sample.write_text("dummy-content")

    calls: list[str] = []

    def fake_convert(
        _path: str, _to: str, *, _extra_args: list[str] | None = None
    ) -> str:
        _ = _extra_args
        calls.append("convert")
        if len(calls) == 1:
            msg = "No pandoc was found"
            raise OSError(msg)
        return "Content\n\nDone"

    def fake_download() -> None:
        calls.append("download")

    monkeypatch.setattr("eduagent.parser.docx.pypandoc.convert_file", fake_convert)
    monkeypatch.setattr("eduagent.parser.docx.pypandoc.download_pandoc", fake_download)

    parser = DocxParser(download_pandoc=True)
    result = parser.parse(sample)

    assert result.paragraphs == ["Content", "Done"]
    assert calls == ["convert", "download", "convert"]


def test_extract_media_args(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    sample = tmp_path / "sample.docx"
    sample.write_text("dummy-content")

    received_args: list[str | None] = []

    def fake_convert(
        _path: str, _to: str, *, extra_args: list[str] | None = None
    ) -> str:
        received_args.append(extra_args[0] if extra_args else None)
        return "Content"

    monkeypatch.setattr("eduagent.parser.docx.pypandoc.convert_file", fake_convert)

    parser = DocxParser(extract_media_dir="media")
    result = parser.parse(sample)

    assert result.paragraphs == ["Content"]
    assert received_args == ["--extract-media=media"]
