from __future__ import annotations

# pyright: reportUntypedFunctionDecorator=false
# pyright: reportUnknownMemberType=false
import asyncio
from typing import Any

from loguru import logger

from eduagent.quiz.enums import JobStatus
from eduagent.quiz.repository import QuizJobRepository
from eduagent.storage.engine import async_session_maker
from eduagent.storage.milvus_store import milvus_store

from .app import celery_app


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


@celery_app.task(name="eduagent.quiz.process_upload")
def process_textbook_upload(
    job_id: str, file_path: str, metadata: dict[str, Any]
) -> dict[str, Any]:
    """Parse textbook, chunk content and populate vector store."""

    async def _run() -> dict[str, Any]:
        await _update_job_status(job_id, JobStatus.PROCESSING)
        try:
            # Placeholder logic for document parsing
            chunk_summary = {
                "chunks": metadata.get("estimated_chunks", 0),
                "subject": metadata.get("subject"),
                "grade_level": metadata.get("grade_level"),
                "file_path": file_path,
            }
            milvus_store.ensure_collection()
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.exception("Textbook upload job %s failed", job_id)
            await _update_job_status(job_id, JobStatus.FAILED, error=str(exc))
            raise
        else:
            await _update_job_status(job_id, JobStatus.COMPLETED, result=chunk_summary)
            return chunk_summary

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
