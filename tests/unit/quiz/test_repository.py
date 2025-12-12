from __future__ import annotations

from collections.abc import AsyncIterator
from itertools import pairwise

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from eduagent.quiz import models as quiz_models
from eduagent.quiz.enums import JobStatus, JobType
from eduagent.quiz.repository import QuizJobRepository
from eduagent.user.models import Base

CHUNK_COUNT = 10
_ = quiz_models


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
async def test_quiz_job_repository_lifecycle(session: AsyncSession) -> None:
    repo = QuizJobRepository(session)
    job = await repo.create_ingestion_job(
        source_filename="demo.pdf",
        file_path="/tmp/demo.pdf",
        subject="math",
        grade_level="grade-9",
        payload={"content_type": "application/pdf"},
    )
    assert job.job_type == JobType.INGESTION.value
    assert job.status == JobStatus.PENDING.value

    await repo.set_task_id(job.id, "celery-task-id")
    updated = await repo.update_status(
        job.id,
        JobStatus.COMPLETED,
        result={"chunks": CHUNK_COUNT},
    )
    assert updated is not None
    assert updated.status == JobStatus.COMPLETED.value
    assert updated.result_payload["chunks"] == CHUNK_COUNT

    dto = await repo.to_dto(await repo.get_job(job.id))
    assert dto is not None
    assert dto.status == JobStatus.COMPLETED
    assert dto.job_type == JobType.INGESTION
    assert dto.result_payload["chunks"] == CHUNK_COUNT
    assert dto.task_id == "celery-task-id"


@pytest.mark.asyncio
async def test_list_completed_ingestions_filters_and_orders(
    session: AsyncSession,
) -> None:
    repo = QuizJobRepository(session)
    completed_ids: list[str] = []
    for idx in range(3):
        job = await repo.create_ingestion_job(
            source_filename=f"lesson-{idx}.docx",
            file_path=f"/tmp/lesson-{idx}.docx",
            subject=f"subject-{idx}",
            grade_level=f"grade-{idx}",
            payload={},
        )
        status = JobStatus.COMPLETED if idx != 1 else JobStatus.PROCESSING
        await repo.update_status(
            job.id,
            status,
            result={"document_job_id": f"doc-{idx}"},
        )
        if status is JobStatus.COMPLETED:
            completed_ids.append(job.id)

    jobs = await repo.list_completed_ingestions(limit=5)
    job_ids = [job.id for job in jobs]
    assert set(job_ids) == set(completed_ids)
    assert all(job.job_type == JobType.INGESTION.value for job in jobs)
    assert all(job.status == JobStatus.COMPLETED.value for job in jobs)
    for earlier, later in pairwise(jobs):
        assert earlier.updated_at >= later.updated_at

    most_recent = await repo.list_completed_ingestions(limit=1)
    assert len(most_recent) == 1
    assert most_recent[0].id in completed_ids
