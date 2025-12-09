from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from eduagent.documents.repository import DocumentRepository
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


@pytest.mark.asyncio
async def test_document_repository_lifecycle(session: AsyncSession) -> None:
    repo = DocumentRepository(session)
    job = await repo.create_job(
        source_filename="lesson.docx",
        file_path="/tmp/lesson.docx",
        subject="history",
        grade_level="grade-7",
        metadata={"language": "zh"},
    )
    assert job.status == "pending"
    assert job.total_chunks == 0

    chunk = await repo.add_chunk(
        job.id,
        chunk_index=0,
        content="The Ming dynasty was known for maritime exploration.",
        token_count=12,
        extras={
            "metadata": {"section": "dynasty"},
            "milvus_vector_id": "vector-001",
        },
    )
    assert chunk is not None
    assert chunk.chunk_index == 0

    artifact = await repo.add_artifact(
        job.id,
        artifact_type="quiz",
        payload={"question_count": 5},
        quality_score=0.88,
    )
    assert artifact is not None
    assert artifact.artifact_type == "quiz"

    updated = await repo.update_status(
        job.id,
        status="completed",
        total_chunks=1,
    )
    assert updated is not None
    assert updated.status == "completed"
    assert updated.total_chunks == 1

    chunks = await repo.list_chunks(job.id)
    artifacts = await repo.list_artifacts(job.id)
    assert len(chunks) == 1
    assert len(artifacts) == 1
    assert chunks[0].milvus_vector_id == "vector-001"

    reassigned = await repo.set_chunk_vector_id(chunk.id, vector_id="vector-002")
    assert reassigned is not None
    assert reassigned.milvus_vector_id == "vector-002"


@pytest.mark.asyncio
async def test_repository_handles_missing_job(session: AsyncSession) -> None:
    repo = DocumentRepository(session)
    assert await repo.get_job("missing") is None
    assert (
        await repo.add_chunk(
            "missing",
            chunk_index=0,
            content="N/A",
            token_count=1,
        )
        is None
    )
    assert (
        await repo.add_artifact(
            "missing",
            artifact_type="quiz",
            payload={},
        )
        is None
    )
    assert await repo.update_status("missing", status="failed") is None
