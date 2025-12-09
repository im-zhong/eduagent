from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

import pytest
import pytest_asyncio
from docx import Document as DocxDocument
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from eduagent.documents.services import EmbeddingBackend
from eduagent.quiz.enums import JobStatus
from eduagent.quiz.repository import QuizJobRepository
from eduagent.storage.milvus_store import EmbeddingRecord
from eduagent.tasks.quiz import (
    TextbookPipelineOptions,
    run_textbook_ingestion_pipeline,
)
from eduagent.user.models import Base


def _write_docx(path: Path, paragraphs: list[str]) -> None:
    doc = DocxDocument()
    for text in paragraphs:
        doc.add_paragraph(text)
    doc.save(str(path))


class MemoryVectorStore:
    def __init__(self) -> None:
        self.records: list[EmbeddingRecord] = []

    def insert_records(self, records: list[EmbeddingRecord]) -> int:
        self.records.extend(records)
        return len(records)


class DeterministicEmbeddingBackend(EmbeddingBackend):
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[float(idx)] * 3 for idx, _ in enumerate(texts, start=1)]


@pytest_asyncio.fixture
async def session_factory() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        yield factory
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_run_textbook_ingestion_pipeline_success(
    session_factory: async_sessionmaker[AsyncSession],
    tmp_path: Path,
) -> None:
    async with session_factory() as session:
        repo = QuizJobRepository(session)
        job = await repo.create_ingestion_job(
            source_filename="lesson.docx",
            file_path="placeholder",
            subject="science",
            grade_level="grade-8",
            payload={},
        )
    doc_path = tmp_path / "lesson.docx"
    _write_docx(
        doc_path,
        [
            "Energy cannot be created or destroyed.",
            "It can only change form.",
        ],
    )
    vector_store = MemoryVectorStore()
    summary = await run_textbook_ingestion_pipeline(
        job.id,
        str(doc_path),
        {"subject": "science", "grade_level": "grade-8", "filename": "lesson.docx"},
        options=TextbookPipelineOptions(
            session_factory=session_factory,
            vector_store=vector_store,  # type: ignore[arg-type]
            embedding_backend=DeterministicEmbeddingBackend(),
        ),
    )
    assert summary["chunks"] > 0
    assert summary["embedded_records"] == summary["chunks"]

    async with session_factory() as session:
        repo = QuizJobRepository(session)
        updated = await repo.get_job(job.id)
        assert updated is not None
        assert updated.status == JobStatus.COMPLETED.value


@pytest.mark.asyncio
async def test_run_textbook_ingestion_pipeline_failure_marks_job(
    session_factory: async_sessionmaker[AsyncSession],
    tmp_path: Path,
) -> None:
    async with session_factory() as session:
        repo = QuizJobRepository(session)
        job = await repo.create_ingestion_job(
            source_filename="blank.docx",
            file_path="placeholder",
            subject="math",
            grade_level="grade-4",
            payload={},
        )
    doc_path = tmp_path / "blank.docx"
    _write_docx(doc_path, [" "])

    vector_store = MemoryVectorStore()
    with pytest.raises(ValueError, match="No readable text"):
        await run_textbook_ingestion_pipeline(
            job.id,
            str(doc_path),
            {"subject": "math", "grade_level": "grade-4"},
            options=TextbookPipelineOptions(
                session_factory=session_factory,
                vector_store=vector_store,  # type: ignore[arg-type]
                embedding_backend=DeterministicEmbeddingBackend(),
            ),
        )

    async with session_factory() as session:
        repo = QuizJobRepository(session)
        failed_job = await repo.get_job(job.id)
        assert failed_job is not None
        assert failed_job.status == JobStatus.FAILED.value
