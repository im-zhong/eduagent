from __future__ import annotations

from typing import Any, TypedDict, cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from eduagent.quiz.enums import JobStatus, JobType
from eduagent.quiz.models import QuizPipelineJob
from eduagent.quiz.schemas import QuizJobDTO


class JobCreateData(TypedDict, total=False):
    source_filename: str
    file_path: str
    subject: str
    grade_level: str
    parent_job_id: str
    job_payload: dict[str, Any]


class QuizJobRepository:
    """Data access layer for quiz pipeline jobs."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_ingestion_job(
        self,
        *,
        source_filename: str,
        file_path: str,
        subject: str,
        grade_level: str,
        payload: dict[str, Any],
    ) -> QuizPipelineJob:
        return await self._create_job(
            JobType.INGESTION,
            {
                "source_filename": source_filename,
                "file_path": file_path,
                "subject": subject,
                "grade_level": grade_level,
                "job_payload": payload,
            },
        )

    async def create_generation_job(
        self,
        *,
        parent_job_id: str,
        payload: dict[str, Any],
    ) -> QuizPipelineJob:
        return await self._create_job(
            JobType.QUIZ_GENERATION,
            {
                "parent_job_id": parent_job_id,
                "job_payload": payload,
            },
        )

    async def create_evaluation_job(
        self,
        *,
        parent_job_id: str,
        payload: dict[str, Any],
    ) -> QuizPipelineJob:
        return await self._create_job(
            JobType.ANSWER_EVALUATION,
            {
                "parent_job_id": parent_job_id,
                "job_payload": payload,
            },
        )

    async def create_scoring_job(
        self,
        *,
        parent_job_id: str,
        payload: dict[str, Any],
    ) -> QuizPipelineJob:
        return await self._create_job(
            JobType.QUIZ_SCORING,
            {
                "parent_job_id": parent_job_id,
                "job_payload": payload,
            },
        )

    async def _create_job(
        self,
        job_type: JobType,
        job_data: JobCreateData,
    ) -> QuizPipelineJob:
        job_kwargs: dict[str, Any] = dict(job_data)
        payload = cast(dict[str, Any] | None, job_kwargs.pop("job_payload", None))
        job = QuizPipelineJob(
            job_type=job_type.value,
            job_payload=payload or {},
            **job_kwargs,
        )
        self.session.add(job)
        await self.session.commit()
        await self.session.refresh(job)
        return job

    async def get_job(self, job_id: str) -> QuizPipelineJob | None:
        stmt = select(QuizPipelineJob).where(QuizPipelineJob.id == job_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def set_task_id(self, job_id: str, task_id: str) -> QuizPipelineJob | None:
        job = await self.get_job(job_id)
        if job is None:
            return None
        job.task_id = task_id
        await self.session.commit()
        await self.session.refresh(job)
        return job

    async def update_status(
        self,
        job_id: str,
        status: JobStatus,
        *,
        result: dict[str, Any] | None = None,
        error_message: str | None = None,
    ) -> QuizPipelineJob | None:
        job = await self.get_job(job_id)
        if job is None:
            return None
        job.status = status.value
        if result is not None:
            job.result_payload = result
        if error_message:
            job.error_message = error_message
        await self.session.commit()
        await self.session.refresh(job)
        return job

    async def to_dto(self, job: QuizPipelineJob | None) -> QuizJobDTO | None:
        if job is None:
            return None
        return QuizJobDTO.model_validate(job)
