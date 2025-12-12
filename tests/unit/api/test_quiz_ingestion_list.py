from __future__ import annotations

from collections.abc import AsyncIterator
from http import HTTPStatus

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from eduagent.api.endpoints.quiz import router as quiz_router
from eduagent.quiz.enums import JobStatus
from eduagent.quiz.repository import QuizJobRepository
from eduagent.storage.engine import get_async_session
from eduagent.user.models import Base


@pytest_asyncio.fixture
async def session_factory() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    try:
        yield factory
    finally:
        await engine.dispose()


@pytest.fixture
def quiz_app(session_factory: async_sessionmaker[AsyncSession]) -> FastAPI:
    app = FastAPI()

    async def _session_override() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_async_session] = _session_override
    app.include_router(quiz_router, prefix="/api/v1")
    return app


@pytest.mark.asyncio
async def test_list_ingestion_jobs_endpoint_returns_recent(
    session_factory: async_sessionmaker[AsyncSession],
    quiz_app: FastAPI,
) -> None:
    async with session_factory() as session:
        repo = QuizJobRepository(session)
        job_ids: list[str] = []
        for idx in range(3):
            ingestion = await repo.create_ingestion_job(
                source_filename=f"lesson-{idx}.docx",
                file_path=f"/tmp/lesson-{idx}.docx",
                subject="science",
                grade_level="grade-5",
                payload={},
            )
            status = JobStatus.COMPLETED if idx != 0 else JobStatus.PROCESSING
            await repo.update_status(
                ingestion.id,
                status,
                result={"document_job_id": f"doc-{idx}"},
            )
            if status is JobStatus.COMPLETED:
                job_ids.append(ingestion.id)

    transport = ASGITransport(app=quiz_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/quiz/ingestions", params={"limit": 5})

    assert response.status_code == HTTPStatus.OK
    payload = response.json()
    ids = {item["job_id"] for item in payload["items"]}
    assert ids == set(job_ids)
    assert all(item["document_job_id"].startswith("doc-") for item in payload["items"])
