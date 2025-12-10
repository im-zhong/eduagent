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
from tests._paths import docs_file

pytestmark = pytest.mark.integration
EXPECTED_QUESTION_COUNT = 2
CLASSES_PATH = docs_file("classes.txt")


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


def _load_classes_sections(limit: int = 2) -> list[str]:
    text = CLASSES_PATH.read_text(encoding="utf-8")
    sections = [section.strip().replace("\n", " ") for section in text.split("\n\n")]
    minimum_length = 20
    filtered = [
        section for section in sections if len(section.strip()) >= minimum_length
    ]
    return filtered[:limit]


async def _seed_ingestion_job() -> tuple[str, list[tuple[str, str]]]:
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
        chunk_records: list[tuple[str, str]] = []
        for index, content in enumerate(_load_classes_sections()):
            chunk = await repo.add_chunk(
                job.id,
                chunk_index=index,
                content=content,
                token_count=len(content.split()),
                extras={"metadata": {"section": "classes", "paragraph": index}},
            )
            assert chunk is not None
            await repo.set_chunk_vector_id(chunk.id, vector_id=chunk.id)
            chunk_records.append((chunk.id, content))
        return job.id, chunk_records


def _insert_vectors(
    job_id: str, chunk_records: list[tuple[str, str]], vector: list[float]
) -> None:
    records = [
        EmbeddingRecord(
            record_id=chunk_id,
            text=text,
            embedding=vector,
            metadata={"ingestion_job_id": job_id, "chunk_index": idx},
        )
        for idx, (chunk_id, text) in enumerate(chunk_records)
    ]
    inserted = milvus_store.insert_records(records)
    assert inserted == len(records)


@pytest.mark.asyncio
async def test_quiz_workflow_runner_persists_artifact() -> None:
    job_id, chunk_records = await _seed_ingestion_job()
    vector = _fixed_vector()
    _insert_vectors(job_id, chunk_records, vector)
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
