from __future__ import annotations

import asyncio
from collections.abc import Generator
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from eduagent.quiz.enums import JobStatus
from eduagent.quiz.repository import QuizJobRepository
from eduagent.tasks import quiz as quiz_tasks
from eduagent.user.models import Base


@pytest.fixture
def sqlite_sessionmaker(
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[async_sessionmaker[AsyncSession]]:
    engine = create_async_engine("sqlite+aiosqlite://", future=True)

    async def _prepare() -> None:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(_prepare())
    session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    monkeypatch.setattr(quiz_tasks, "async_session_maker", session_factory)

    yield session_factory

    asyncio.run(engine.dispose())


def _create_job(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    subject: str,
    grade_level: str,
) -> str:
    async def _create() -> str:
        async with session_factory() as session:
            repo = QuizJobRepository(session)
            job = await repo.create_ingestion_job(
                source_filename="sample.docx",
                file_path="sample.docx",
                subject=subject,
                grade_level=grade_level,
                payload={},
            )
            return job.id

    return asyncio.run(_create())


def _get_job_status(
    session_factory: async_sessionmaker[AsyncSession], job_id: str
) -> tuple[str, dict[str, Any]]:
    async def _load() -> tuple[str, dict[str, object]]:
        async with session_factory() as session:
            repo = QuizJobRepository(session)
            job = await repo.get_job(job_id)
            assert job is not None
            return job.status, job.result_payload

    return asyncio.run(_load())


def test_generate_quiz_updates_job(
    sqlite_sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    job_id = _create_job(sqlite_sessionmaker, subject="Physics", grade_level="10")
    total_questions = 4
    payload = {"quiz_rules": {"total_questions": total_questions}, "subject": "Physics"}

    result = quiz_tasks.generate_quiz(job_id, payload)

    assert len(result["questions"]) == total_questions
    status, stored_result = _get_job_status(sqlite_sessionmaker, job_id)
    assert status == JobStatus.COMPLETED.value
    assert stored_result["rules"]["total_questions"] == total_questions


def test_evaluate_answers_updates_job(
    sqlite_sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    job_id = _create_job(sqlite_sessionmaker, subject="History", grade_level="11")
    payload = {"answers": [{"is_correct": True}, {"is_correct": False}]}

    result = quiz_tasks.evaluate_answers(job_id, payload)

    assert result["score"] == 1
    status, stored_result = _get_job_status(sqlite_sessionmaker, job_id)
    assert status == JobStatus.COMPLETED.value
    assert stored_result["total"] == len(payload["answers"])
