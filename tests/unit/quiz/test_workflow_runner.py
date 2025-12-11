from __future__ import annotations

from collections.abc import AsyncIterator, Callable

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from eduagent.documents.repository import DocumentRepository
from eduagent.quiz.workflow import QuizWorkflowRunner, ReActEvent
from eduagent.user.models import Base


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


class StaticWorkflow:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload
        self.calls: list[tuple[str, str | None, str]] = []

    def run(
        self,
        prompt: str,
        ingestion_job_id: str | None = None,
        *,
        language: str = "zh",
        callback: Callable[[ReActEvent], None] | None = None,
    ) -> dict[str, object]:
        if callback is not None:
            callback(ReActEvent("plan", ingestion_job_id, {"mock": True}))
        self.calls.append((prompt, ingestion_job_id, language))
        return self.payload


@pytest.mark.asyncio
async def test_quiz_workflow_runner_persists_artifact(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        repo = DocumentRepository(session)
        job = await repo.create_job(
            source_filename="lesson.docx",
            file_path="/tmp/lesson.docx",
            subject="math",
            grade_level="grade-5",
        )
        runner = QuizWorkflowRunner(
            repository=repo,
            workflow=StaticWorkflow(
                {
                    "questions": [{"prompt": "Q1", "answer": "A1"}],
                    "answers": [{"prompt": "Q1", "answer": "A1"}],
                    "evaluation": {"total": 1, "approved": 1},
                }
            ),
        )
        result = await runner.run(job.id, "Generate a quiz")
        artifacts = await repo.list_artifacts(job.id)
        assert len(artifacts) == 1
        assert result["artifact_id"] == artifacts[0].id


@pytest.mark.asyncio
async def test_quiz_workflow_runner_missing_job(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        repo = DocumentRepository(session)
        runner = QuizWorkflowRunner(
            repository=repo,
            workflow=StaticWorkflow({"questions": [], "answers": [], "evaluation": {}}),
        )
        with pytest.raises(ValueError, match="Ingestion job not found"):
            await runner.run("missing", "prompt")
