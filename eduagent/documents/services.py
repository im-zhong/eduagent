from __future__ import annotations

from pathlib import Path
from typing import Any

from docx import Document as DocxDocument
from langchain_core.documents import Document as LCDocument
from langchain_text_splitters import RecursiveCharacterTextSplitter

from eduagent.documents.models import DocumentIngestionJob
from eduagent.documents.repository import DocumentRepository


class DocxIngestionService:
    """Parses DOCX files, chunks them, and stores chunks via the repository."""

    def __init__(
        self,
        repository: DocumentRepository,
        *,
        chunk_size: int = 800,
        chunk_overlap: int = 100,
    ) -> None:
        self.repository = repository
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", " "],
        )

    def _load_text(self, file_path: str | Path) -> list[str]:
        doc = DocxDocument(str(Path(file_path)))
        paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        if not paragraphs:
            msg = f"No readable text found in {file_path}"
            raise ValueError(msg)
        return paragraphs

    def _chunk_paragraphs(self, paragraphs: list[str]) -> list[LCDocument]:
        base_doc = LCDocument(
            page_content="\n\n".join(paragraphs),
            metadata={"paragraphs": len(paragraphs)},
        )
        return self.splitter.split_documents([base_doc])

    async def ingest_docx(
        self,
        *,
        source_filename: str,
        file_path: str,
        subject: str | None,
        grade_level: str | None,
        metadata: dict[str, Any] | None = None,
    ) -> DocumentIngestionJob:
        job = await self.repository.create_job(
            source_filename=source_filename,
            file_path=file_path,
            subject=subject,
            grade_level=grade_level,
            metadata=metadata,
        )
        try:
            paragraphs = self._load_text(file_path)
            chunks = self._chunk_paragraphs(paragraphs)
            total_paragraphs = len(paragraphs)
            for index, chunk in enumerate(chunks):
                chunk_metadata = {
                    "paragraphs": total_paragraphs,
                    "chunk_index": index,
                    "character_count": len(chunk.page_content),
                }
                await self.repository.add_chunk(
                    job.id,
                    chunk_index=index,
                    content=chunk.page_content,
                    token_count=len(chunk.page_content.split()),
                    extras={
                        "metadata": chunk_metadata,
                    },
                )
        except Exception as exc:  # pragma: no cover - defensive
            await self.repository.update_status(
                job.id,
                status="failed",
                error_message=str(exc),
            )
            raise
        else:
            updated = await self.repository.update_status(
                job.id,
                status="completed",
                total_chunks=len(chunks),
            )
            return updated or job
