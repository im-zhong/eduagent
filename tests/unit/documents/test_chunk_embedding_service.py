from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass, field

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from eduagent.documents import services
from eduagent.documents.repository import DocumentRepository
from eduagent.documents.services import ChunkEmbeddingService, EmbeddingBackend
from eduagent.storage.milvus_store import EmbeddingRecord
from eduagent.user.models import Base


@pytest_asyncio.fixture
async def session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    await engine.dispose()


class FakeVectorStore:
    def __init__(self) -> None:
        self.records: list[EmbeddingRecord] = []

    def insert_records(self, records: list[EmbeddingRecord]) -> int:
        self.records.extend(records)
        return len(records)


def _vector_default() -> list[list[float]]:
    return []


@dataclass
class FakeEmbeddingBackend(EmbeddingBackend):
    vectors: list[list[float]] = field(default_factory=_vector_default)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if self.vectors:
            return self.vectors
        return [[float(i)] * 3 for i in range(len(texts))]

    def embed_query(self, text: str) -> list[float]:
        token_count = len(text.split())
        return [float(token_count)] * 3  # pragma: no cover - unused


@pytest.mark.asyncio
async def test_chunk_embedding_service_indexes_vectors(session: AsyncSession) -> None:
    repo = DocumentRepository(session)
    job = await repo.create_job(
        source_filename="lesson.docx",
        file_path="/tmp/lesson.docx",
        subject="math",
        grade_level="grade-6",
    )
    chunk = await repo.add_chunk(
        job.id,
        chunk_index=0,
        content="Area of a triangle equals half base times height.",
        token_count=11,
    )
    assert chunk is not None

    fake_store = FakeVectorStore()
    backend = FakeEmbeddingBackend()
    service = ChunkEmbeddingService(
        repo,
        vector_store=fake_store,  # type: ignore[arg-type]
        embedder=backend,
    )

    inserted = await service.index_job_chunks(job.id)
    assert inserted == 1
    assert fake_store.records[0].record_id == chunk.id
    stored_chunks = await repo.list_chunks(job.id)
    assert stored_chunks[0].milvus_vector_id == chunk.id
    assert fake_store.records[0].metadata["ingestion_job_id"] == job.id


@pytest.mark.asyncio
async def test_chunk_embedding_service_handles_empty_job(session: AsyncSession) -> None:
    repo = DocumentRepository(session)
    job = await repo.create_job(
        source_filename="empty.docx",
        file_path="/tmp/empty.docx",
        subject=None,
        grade_level=None,
    )
    fake_store = FakeVectorStore()
    service = ChunkEmbeddingService(
        repo,
        vector_store=fake_store,  # type: ignore[arg-type]
        embedder=FakeEmbeddingBackend(vectors=[]),
    )
    inserted = await service.index_job_chunks(job.id)
    assert inserted == 0


@pytest.mark.asyncio
async def test_chunk_embedding_service_validates_vector_count(
    session: AsyncSession,
) -> None:
    repo = DocumentRepository(session)
    job = await repo.create_job(
        source_filename="lesson.docx",
        file_path="/tmp/lesson.docx",
        subject="math",
        grade_level="grade-6",
    )
    await repo.add_chunk(
        job.id,
        chunk_index=0,
        content="Sample chunk",
        token_count=2,
    )
    backend = FakeEmbeddingBackend(vectors=[])
    backend.vectors = [[1.0, 1.0, 1.0], [2.0, 2.0, 2.0]]
    service = ChunkEmbeddingService(
        repo,
        vector_store=FakeVectorStore(),  # type: ignore[arg-type]
        embedder=backend,
    )
    with pytest.raises(ValueError, match="Embedding backend returned mismatched"):
        await service.index_job_chunks(job.id)


def test_embedding_backend_batches_requests(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []

    class StubModel:
        def embed_documents(self, texts: list[str]) -> list[list[float]]:
            calls.append(list(texts))
            return [[float(len(calls))]] * len(texts)

    monkeypatch.setattr(services, "get_embedding_model", lambda: StubModel())
    backend = EmbeddingBackend()
    texts = [f"chunk-{idx}" for idx in range(70)]
    vectors = backend.embed_documents(texts)
    assert len(vectors) == len(texts)
    expected_batches = 2
    assert len(calls) == expected_batches  # 64 + 6
    assert calls[0] == texts[:64]
    assert calls[1] == texts[64:]
