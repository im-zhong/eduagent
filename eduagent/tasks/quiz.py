from __future__ import annotations

# pyright: reportUntypedFunctionDecorator=false
# pyright: reportUnknownMemberType=false
import asyncio
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from datetime import UTC, datetime
from logging import Logger
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from celery.utils.log import (
    get_task_logger,  # pyright: ignore[reportUnknownVariableType]
)
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from eduagent.api.schemas import (
    CognitiveLevel,
    GeneratedQuestion,
    QuestionGenerationResponse,
    QuestionType,
    QuizAnswerItem,
    QuizEvaluationPayload,
    QuizEvaluationResponse,
    QuizGenerationPayload,
    QuizScoringPayload,
    QuizScoringResponse,
    SubjectArea,
    TextbookIngestionResult,
    TextbookUploadMetadata,
)
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
from eduagent.storage.minio_service import minio_service

from .app import celery_app

task_logger: Logger = get_task_logger(__name__)

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
    result: BaseModel | dict[str, Any] | None = None,
    error: str | None = None,
) -> None:
    async with async_session_maker() as session:
        repo = QuizJobRepository(session)
        serialized_result: dict[str, Any] | None
        if result is None:
            serialized_result = None
        elif isinstance(result, BaseModel):
            serialized_result = result.model_dump(mode="json")
        else:
            serialized_result = result
        await repo.update_status(
            job_id,
            status,
            result=serialized_result,
            error_message=error,
        )


async def run_textbook_ingestion_pipeline(
    job_id: str,
    file_path: str,
    metadata: TextbookUploadMetadata,
    *,
    options: TextbookPipelineOptions | None = None,
) -> TextbookIngestionResult:
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
            metadata_dict = metadata.model_dump(
                mode="json",
                exclude={"extra"},
                exclude_none=True,
            )
            metadata_dict.update(metadata.extra)
            document_job = await ingestion_service.ingest_docx(
                source_filename=metadata.original_filename or metadata.filename,
                file_path=file_path,
                subject=str(metadata.subject) if metadata.subject else None,
                grade_level=metadata.grade_level,
                metadata=metadata_dict,
            )
            embedded_count = await embedding_service.index_job_chunks(document_job.id)
        except Exception as exc:  # pragma: no cover - defensive
            await quiz_repo.update_status(
                job_id,
                JobStatus.FAILED,
                error_message=str(exc),
            )
            raise
        result = TextbookIngestionResult(
            document_job_id=document_job.id,
            chunks=document_job.total_chunks,
            embedded_records=embedded_count,
            subject=metadata.subject,
            grade_level=metadata.grade_level,
        )
        await quiz_repo.update_status(
            job_id,
            JobStatus.COMPLETED,
            result=result.model_dump(mode="json"),
        )
        return result


@celery_app.task(name="eduagent.quiz.process_upload", pydantic=True)
def process_textbook_upload(
    job_id: str, object_name: str, metadata: TextbookUploadMetadata
) -> TextbookIngestionResult:
    """Parse textbook, chunk content and populate vector store."""

    async def _run() -> TextbookIngestionResult:
        try:
            milvus_store.ensure_collection()
            with TemporaryDirectory() as tmp_dir:
                filename = metadata.filename or Path(object_name).name
                download_path = Path(tmp_dir) / filename
                minio_service.download_to_path(object_name, download_path)
                return await run_textbook_ingestion_pipeline(
                    job_id,
                    str(download_path),
                    metadata,
                )
        except Exception:  # pragma: no cover - log and re-raise
            task_logger.exception("Textbook upload job %s failed", job_id)
            raise

    return asyncio.run(_run())


@celery_app.task(name="eduagent.quiz.generate", pydantic=True)
def generate_quiz(
    job_id: str, payload: QuizGenerationPayload
) -> QuestionGenerationResponse:
    """Generate quiz items using parsed knowledge base context."""

    async def _run() -> QuestionGenerationResponse:
        await _update_job_status(job_id, JobStatus.PROCESSING)
        try:
            total_questions = payload.rules.total_questions
            subject = payload.subject or SubjectArea.GENERAL
            questions = [
                GeneratedQuestion(
                    id=f"{job_id}-q{idx + 1}",
                    question_text=f"{subject} question {idx + 1}",
                    question_type=payload.rules.question_types[0]
                    if payload.rules.question_types
                    else QuestionType.MULTIPLE_CHOICE,
                    difficulty=payload.rules.primary_difficulty,
                    cognitive_level=CognitiveLevel.MEMORY,
                    knowledge_point_ids=[],
                    options=None,
                    correct_answer=None,
                    explanation=None,
                    solution_steps=None,
                    estimated_difficulty=0.5,
                )
                for idx in range(total_questions)
            ]
            response = QuestionGenerationResponse(
                questions=questions,
                generation_id=job_id,
                generated_at=datetime.now(tz=UTC),
            )
        except Exception as exc:  # pragma: no cover
            task_logger.exception("Quiz generation job %s failed", job_id)
            await _update_job_status(job_id, JobStatus.FAILED, error=str(exc))
            raise
        else:
            await _update_job_status(job_id, JobStatus.COMPLETED, result=response)
            return response

    return asyncio.run(_run())


@celery_app.task(name="eduagent.quiz.evaluate", pydantic=True)
def evaluate_answers(
    job_id: str, payload: QuizEvaluationPayload
) -> QuizEvaluationResponse:
    """Evaluate quiz answers and provide simple analytics."""

    async def _run() -> QuizEvaluationResponse:
        await _update_job_status(job_id, JobStatus.PROCESSING)
        try:
            answers: list[QuizAnswerItem] = payload.answers
            score = sum(1 for answer in answers if answer.is_correct)
            response = QuizEvaluationResponse(
                score=score,
                total=len(answers),
                details=[answer.model_dump(mode="json") for answer in answers],
            )
        except Exception as exc:  # pragma: no cover
            task_logger.exception("Quiz evaluation job %s failed", job_id)
            await _update_job_status(job_id, JobStatus.FAILED, error=str(exc))
            raise
        else:
            await _update_job_status(job_id, JobStatus.COMPLETED, result=response)
            return response

    return asyncio.run(_run())


@celery_app.task(name="eduagent.quiz.score", pydantic=True)
def score_quiz_quality(job_id: str, payload: QuizScoringPayload) -> QuizScoringResponse:
    """Score quiz quality using an LLM rubric."""

    async def _run() -> QuizScoringResponse:
        await _update_job_status(job_id, JobStatus.PROCESSING)
        service = QuizScoringService()
        try:
            scoring_result = service.score(payload.model_dump())
            response = QuizScoringResponse(
                quality=scoring_result.quality,
                rationale=scoring_result.rationale,
                suggestions=scoring_result.suggestions,
            )
        except Exception as exc:
            task_logger.exception("Quiz scoring job %s failed", job_id)
            await _update_job_status(job_id, JobStatus.FAILED, error=str(exc))
            raise
        await _update_job_status(job_id, JobStatus.COMPLETED, result=response)
        return response

    return asyncio.run(_run())
