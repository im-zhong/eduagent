from __future__ import annotations

import json
from collections.abc import AsyncIterator, Callable
from http import HTTPStatus
from typing import Any, cast

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from eduagent.agents import ConversationTurn, RagChatResult
from eduagent.api.endpoints.quiz import get_rag_agent
from eduagent.api.endpoints.quiz import router as quiz_router
from eduagent.quiz.enums import JobStatus
from eduagent.quiz.repository import QuizJobRepository
from eduagent.storage.engine import get_async_session
from eduagent.user.models import Base


class StubRagAgent:
    def run(
        self,
        question: str,
        *,
        ingestion_ids: list[str] | None = None,
        history: list[ConversationTurn] | None = None,
        callback: Callable[[str, dict[str, Any]], None] | None = None,
    ) -> RagChatResult:
        _ = ingestion_ids
        if callback is not None:
            callback("ingest", {"todo": ["检索"]})
            callback("retrieve", {"references": [{"text": "片段", "metadata": {}}]})
        updated_history = list(history or [])
        updated_history.append({"role": "user", "content": question})
        updated_history.append({"role": "assistant", "content": "回答"})
        return RagChatResult(
            answer="回答",
            references=[{"text": "片段", "metadata": {"source": "doc"}}],
            history=updated_history,
        )


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
def rag_app(session_factory: async_sessionmaker[AsyncSession]) -> FastAPI:
    app = FastAPI()

    async def _session_override() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_async_session] = _session_override
    app.dependency_overrides[get_rag_agent] = lambda: StubRagAgent()
    app.include_router(quiz_router, prefix="/api/v1")
    return app


@pytest.mark.asyncio
async def test_rag_chat_stream_emits_events(
    session_factory: async_sessionmaker[AsyncSession],
    rag_app: FastAPI,
) -> None:
    async with session_factory() as session:
        repo = QuizJobRepository(session)
        job = await repo.create_ingestion_job(
            source_filename="lesson.docx",
            file_path="/tmp/lesson.docx",
            subject="science",
            grade_level="grade-5",
            payload={},
        )
        await repo.update_status(
            job.id, JobStatus.COMPLETED, result={"document_job_id": "doc-1"}
        )
        job_id = job.id
    payload = {
        "ingestion_ids": [job_id],
        "question": "解释惯性",
        "history": [],
    }
    transport = ASGITransport(app=rag_app)
    async with (
        AsyncClient(transport=transport, base_url="http://test") as client,
        client.stream("POST", "/api/v1/quiz/rag/chat/stream", json=payload) as response,
    ):
        assert response.status_code == HTTPStatus.OK
        events: list[dict[str, Any]] = []
        async for line in response.aiter_lines():
            if not line.startswith("data: "):
                continue
            data = json.loads(line.replace("data: ", "", 1))
            events.append(data)
    assert events[0]["phase"] == "ingest"
    assert events[1]["phase"] == "retrieve"
    final_event = events[-1]
    assert final_event["phase"] == "final"
    payload = cast(dict[str, Any], final_event["payload"])
    assert payload["answer"] == "回答"


@pytest.mark.asyncio
async def test_rag_chat_stream_validates_ingestion(
    rag_app: FastAPI,
) -> None:
    transport = ASGITransport(app=rag_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/quiz/rag/chat/stream",
            json={"ingestion_ids": ["missing"], "question": "hi"},
        )
    assert response.status_code == HTTPStatus.NOT_FOUND
