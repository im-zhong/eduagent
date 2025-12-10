from __future__ import annotations

# pyright: reportUntypedFunctionDecorator=false
# pyright: reportUnknownMemberType=false
import asyncio
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from typing import Any

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from eduagent.documents.repository import DocumentRepository
from eduagent.documents.services import (
    ChunkEmbeddingService,
    DocxIngestionService,
    EmbeddingBackend,
)
from eduagent.quiz.enums import JobStatus
from eduagent.quiz.repository import QuizJobRepository
from eduagent.quiz.scoring import QuizScoringService
from eduagent.storage.engine import async_session_maker
from eduagent.storage.milvus_store import MilvusVectorStore, milvus_store

from .app import celery_app

SessionFactory = Callable[[], AbstractAsyncContextManager[AsyncSession]]


@dataclass
class TextbookPipelineOptions:
    session_factory: SessionFactory | None = None
    vector_store: MilvusVectorStore | None = None
    embedding_backend: EmbeddingBackend | None = None


async def _update_job_status(
    job_id: str,
    status: JobStatus,
    *,
    result: dict[str, Any] | None = None,
    error: str | None = None,
) -> None:
    async with async_session_maker() as session:
        repo = QuizJobRepository(session)
        await repo.update_status(job_id, status, result=result, error_message=error)


async def run_textbook_ingestion_pipeline(
    job_id: str,
    file_path: str,
    metadata: dict[str, Any],
    *,
    options: TextbookPipelineOptions | None = None,
) -> dict[str, Any]:
    """Ingest DOCX file, chunk it, and index embeddings."""

    options = options or TextbookPipelineOptions()
    session_factory = options.session_factory or async_session_maker
    async with session_factory() as session:
        quiz_repo = QuizJobRepository(session)
        doc_repo = DocumentRepository(session)
        ingestion_service = DocxIngestionService(doc_repo)
        embedding_service = ChunkEmbeddingService(
            doc_repo,
            vector_store=options.vector_store,
            embedder=options.embedding_backend,
        )

        await quiz_repo.update_status(job_id, JobStatus.PROCESSING)
        try:
            document_job = await ingestion_service.ingest_docx(
                source_filename=metadata.get("filename", metadata.get("subject", "")),
                file_path=file_path,
                subject=metadata.get("subject"),
                grade_level=metadata.get("grade_level"),
                metadata=metadata,
            )
            embedded_count = await embedding_service.index_job_chunks(document_job.id)
        except Exception as exc:  # pragma: no cover - defensive
            await quiz_repo.update_status(
                job_id,
                JobStatus.FAILED,
                error_message=str(exc),
            )
            raise
        result = {
            "document_job_id": document_job.id,
            "chunks": document_job.total_chunks,
            "embedded_records": embedded_count,
            "subject": metadata.get("subject"),
            "grade_level": metadata.get("grade_level"),
        }
        await quiz_repo.update_status(job_id, JobStatus.COMPLETED, result=result)
        return result


@celery_app.task(name="eduagent.quiz.process_upload")
def process_textbook_upload(
    job_id: str, file_path: str, metadata: dict[str, Any]
) -> dict[str, Any]:
    """Parse textbook, chunk content and populate vector store."""

    async def _run() -> dict[str, Any]:
        try:
            milvus_store.ensure_collection()
            return await run_textbook_ingestion_pipeline(
                job_id,
                file_path,
                metadata,
            )
        except Exception:  # pragma: no cover - log and re-raise
            logger.exception("Textbook upload job %s failed", job_id)
            raise

    return asyncio.run(_run())


@celery_app.task(name="eduagent.quiz.generate")
def generate_quiz(job_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Generate quiz items using parsed knowledge base context."""

    async def _run() -> dict[str, Any]:
        await _update_job_status(job_id, JobStatus.PROCESSING)
        try:
            rules = payload.get("quiz_rules", {})
            total_questions = int(rules.get("total_questions", 5))
            questions = [
                {
                    "id": f"{job_id}-q{idx + 1}",
                    "prompt": f"Generated question {idx + 1}",
                    "difficulty": rules.get("primary_difficulty", "medium"),
                    "subject": payload.get("subject"),
                }
                for idx in range(total_questions)
            ]
            result = {"questions": questions, "rules": rules}
        except Exception as exc:  # pragma: no cover
            logger.exception("Quiz generation job %s failed", job_id)
            await _update_job_status(job_id, JobStatus.FAILED, error=str(exc))
            raise
        else:
            await _update_job_status(job_id, JobStatus.COMPLETED, result=result)
            return result

    return asyncio.run(_run())


@celery_app.task(name="eduagent.quiz.evaluate")
def evaluate_answers(job_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Evaluate quiz answers and provide simple analytics."""

    async def _run() -> dict[str, Any]:
        await _update_job_status(job_id, JobStatus.PROCESSING)
        try:
            answers: list[dict[str, Any]] = payload.get("answers", [])
            score = sum(1 for answer in answers if answer.get("is_correct", False))
            result = {
                "score": score,
                "total": len(answers),
                "details": answers,
            }
        except Exception as exc:  # pragma: no cover
            logger.exception("Quiz evaluation job %s failed", job_id)
            await _update_job_status(job_id, JobStatus.FAILED, error=str(exc))
            raise
        else:
            await _update_job_status(job_id, JobStatus.COMPLETED, result=result)
            return result

    return asyncio.run(_run())


@celery_app.task(name="eduagent.quiz.score")
def score_quiz_quality(job_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Score quiz quality using an LLM rubric."""

    async def _run() -> dict[str, Any]:
        await _update_job_status(job_id, JobStatus.PROCESSING)
        service = QuizScoringService()
        try:
            scoring_result = service.score(payload)
            result = {
                "quality": scoring_result.quality,
                "rationale": scoring_result.rationale,
                "suggestions": scoring_result.suggestions,
            }
        except Exception as exc:
            logger.exception("Quiz scoring job %s failed", job_id)
            await _update_job_status(job_id, JobStatus.FAILED, error=str(exc))
            raise
        await _update_job_status(job_id, JobStatus.COMPLETED, result=result)
        return result

    return asyncio.run(_run())
