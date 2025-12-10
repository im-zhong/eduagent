from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

import pytest

from eduagent.documents.repository import DocumentRepository
from eduagent.documents.services import EmbeddingBackend
from eduagent.quiz.workflow import (
    QuizGenerationWorkflow,
    QuizWorkflowConfig,
    QuizWorkflowRunner,
)
from eduagent.storage.engine import async_engine, async_session_maker
from eduagent.storage.milvus_store import EmbeddingRecord, milvus_store
from eduagent.user.models import Base

pytestmark = pytest.mark.integration
EXPECTED_QUESTION_COUNT = 2


def _fixed_vector() -> list[float]:
    return [0.01 * ((index % 7) + 1) for index in range(milvus_store.dim)]


@dataclass
class _StaticResponse:
    content: str


class _StaticLLM:
    def __init__(self) -> None:
        self.payload = [
            {"prompt": "What is photosynthesis?", "answer": "The plant energy cycle."},
            {"prompt": "Why is sunlight important?", "answer": "It powers growth."},
        ]

    def invoke(self, messages: list[Any]) -> _StaticResponse:
        assert messages  # ensure prompt is forwarded
        return _StaticResponse(json.dumps(self.payload))


class _FixedEmbedder(EmbeddingBackend):
    def __init__(self, vector: list[float]) -> None:
        self.vector = vector

    def embed_query(self, text: str) -> list[float]:
        _ = text
        return self.vector

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self.vector for _ in texts]


async def _ensure_schema() -> None:
    await async_engine.dispose()
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def _seed_ingestion_job() -> tuple[str, str, str]:
    await _ensure_schema()
    async with async_session_maker() as session:
        repo = DocumentRepository(session)
        job = await repo.create_job(
            source_filename="lesson.docx",
            file_path=f"/tmp/{uuid4().hex}.docx",
            subject="science",
            grade_level="grade-5",
            metadata={"source": "integration-test"},
        )
        chunk = await repo.add_chunk(
            job.id,
            chunk_index=0,
            content="Plants convert sunlight into energy using photosynthesis.",
            token_count=9,
            extras={"metadata": {"section": "biology"}},
        )
        assert chunk is not None
        await repo.set_chunk_vector_id(chunk.id, vector_id=chunk.id)
        return job.id, chunk.id, chunk.content


def _insert_vector(chunk_id: str, job_id: str, text: str, vector: list[float]) -> None:
    record = EmbeddingRecord(
        record_id=chunk_id,
        text=text,
        embedding=vector,
        metadata={"ingestion_job_id": job_id, "chunk_index": 0},
    )
    inserted = milvus_store.insert_records([record])
    assert inserted == 1


@pytest.mark.asyncio
async def test_quiz_workflow_runner_persists_artifact() -> None:
    job_id, chunk_id, chunk_text = await _seed_ingestion_job()
    vector = _fixed_vector()
    _insert_vector(chunk_id, job_id, chunk_text, vector)
    workflow = QuizGenerationWorkflow(
        QuizWorkflowConfig(
            vector_store=milvus_store,
            embedder=_FixedEmbedder(vector),
            llm=_StaticLLM(),
            retrieval_limit=3,
        )
    )
    async with async_session_maker() as session:
        repo = DocumentRepository(session)
        runner = QuizWorkflowRunner(repository=repo, workflow=workflow)
        result = await runner.run(job_id, "Generate a biology quiz")
        assert result["ingestion_job_id"] == job_id
        assert len(result["questions"]) == EXPECTED_QUESTION_COUNT
        artifacts = await repo.list_artifacts(job_id)
        assert artifacts
        latest = artifacts[-1]
        assert latest.payload.get("questions")
