from __future__ import annotations

import asyncio
import math
from dataclasses import dataclass
from uuid import uuid4

import pytest

from eduagent.quiz.enums import JobStatus
from eduagent.quiz.models import QuizPipelineJob
from eduagent.quiz.repository import QuizJobRepository
from eduagent.quiz.scoring import QuizScoringResult
from eduagent.storage.engine import async_engine, async_session_maker
from eduagent.tasks.quiz import score_quiz_quality
from eduagent.user.models import Base

pytestmark = pytest.mark.integration


@dataclass
class _StubScoringService:
    result: QuizScoringResult

    def score(self, payload: dict[str, object]) -> QuizScoringResult:
        assert payload["questions"]
        return self.result


async def _ensure_schema() -> None:
    await async_engine.dispose()
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def _create_scoring_job() -> str:
    await _ensure_schema()
    async with async_session_maker() as session:
        repo = QuizJobRepository(session)
        ingestion_job = await repo.create_ingestion_job(
            source_filename="lesson.docx",
            file_path=f"/tmp/{uuid4().hex}.docx",
            subject="science",
            grade_level="grade-5",
            payload={"content_type": "application/docx"},
        )
        job = await repo.create_scoring_job(
            parent_job_id=ingestion_job.id,
            payload={"quiz_job_id": ingestion_job.id, "questions": []},
        )
    await async_engine.dispose()
    return job.id


async def _fetch_job(job_id: str) -> QuizPipelineJob:
    await async_engine.dispose()
    async with async_session_maker() as session:
        repo = QuizJobRepository(session)
        job = await repo.get_job(job_id)
        assert job is not None
        return job


@pytest.mark.asyncio
async def test_score_quiz_quality_updates_job(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    job_id = await _create_scoring_job()
    stub_service = _StubScoringService(
        QuizScoringResult(
            quality=0.92,
            rationale="Questions cover the learning objectives.",
            suggestions=["Add scenario-based prompts."],
        )
    )
    monkeypatch.setattr(
        "eduagent.tasks.quiz.QuizScoringService",
        lambda: stub_service,
    )
    payload = {
        "quiz_job_id": job_id,
        "questions": [{"prompt": "Q1", "answer": "A1"}],
        "rules": {"total_questions": 1},
    }
    result = await asyncio.to_thread(score_quiz_quality, job_id, payload)
    assert math.isclose(result["quality"], stub_service.result.quality, rel_tol=1e-6)
    saved_job = await _fetch_job(job_id)
    assert saved_job.status == JobStatus.COMPLETED.value
    assert saved_job.result_payload["quality"] == stub_service.result.quality
