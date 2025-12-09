from __future__ import annotations

from shutil import copyfileobj
from typing import Annotated, Any, Protocol, cast, runtime_checkable
from uuid import uuid4

from celery.result import AsyncResult
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from eduagent.api.schemas import (
    QuizEvaluationRequest,
    QuizGenerationRequest,
    QuizJobDetailResponse,
    QuizJobHandleResponse,
    SubjectArea,
)
from eduagent.defs import defs
from eduagent.quiz.enums import JobStatus, JobType
from eduagent.quiz.repository import QuizJobRepository
from eduagent.quiz.schemas import QuizJobDTO
from eduagent.storage.engine import get_async_session
from eduagent.tasks.quiz import evaluate_answers, generate_quiz, process_textbook_upload


@runtime_checkable
class SupportsDelay(Protocol):
    def delay(
        self, *args: object, **kwargs: object
    ) -> AsyncResult: ...  # pragma: no cover


def _extract_task_id(result: AsyncResult) -> str:
    task_id = cast(str | None, cast(Any, result).id)
    if not isinstance(task_id, str):
        msg = "Celery task returned an invalid identifier"
        raise TypeError(msg)
    return task_id


router = APIRouter(prefix="/quiz", tags=["Quiz Pipeline"])


def _handle_response(dto: QuizJobDTO) -> QuizJobHandleResponse:
    return QuizJobHandleResponse(
        job_id=dto.id,
        job_type=dto.job_type,
        status=dto.status,
        task_id=dto.task_id,
    )


def _detail_response(dto: QuizJobDTO) -> QuizJobDetailResponse:
    return QuizJobDetailResponse(
        job_id=dto.id,
        job_type=dto.job_type,
        status=dto.status,
        task_id=dto.task_id,
        parent_job_id=dto.parent_job_id,
        subject=SubjectArea(dto.subject) if dto.subject else None,
        grade_level=dto.grade_level,
        payload=dto.job_payload or {},
        result=dto.result_payload or {},
        error_message=dto.error_message,
    )


@router.post(
    "/upload",
    response_model=QuizJobHandleResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def upload_textbook_for_quiz(
    subject: Annotated[SubjectArea, Form(...)],
    grade_level: Annotated[str, Form(...)],
    file: Annotated[UploadFile, File(...)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> QuizJobHandleResponse:
    """Upload a textbook/document for asynchronous ingestion."""

    destination_dir = defs.pathes.uploads_dir
    destination_dir.mkdir(parents=True, exist_ok=True)
    unique_prefix = uuid4()
    original_filename = file.filename or "uploaded_textbook"
    stored_path = destination_dir / f"{unique_prefix}_{original_filename}"
    with stored_path.open("wb") as buffer:
        copyfileobj(file.file, buffer)

    repo = QuizJobRepository(session)
    job = await repo.create_ingestion_job(
        source_filename=original_filename,
        file_path=str(stored_path),
        subject=subject.value,
        grade_level=grade_level,
        payload={
            "content_type": file.content_type,
            "subject": subject.value,
            "grade_level": grade_level,
        },
    )
    upload_task = cast(SupportsDelay, process_textbook_upload)
    task = upload_task.delay(
        job.id,
        str(stored_path),
        {
            "subject": subject.value,
            "grade_level": grade_level,
            "filename": original_filename,
            "content_type": file.content_type,
        },
    )
    await repo.set_task_id(job.id, _extract_task_id(task))
    dto = await repo.to_dto(job)
    if dto is None:  # pragma: no cover - safety guard
        raise HTTPException(status_code=500, detail="Failed to create ingestion job")
    return _handle_response(dto)


@router.get(
    "/jobs/{job_id}",
    response_model=QuizJobDetailResponse,
    status_code=status.HTTP_200_OK,
)
async def get_quiz_job(
    job_id: str,
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> QuizJobDetailResponse:
    repo = QuizJobRepository(session)
    job = await repo.get_job(job_id)
    dto = await repo.to_dto(job)
    if dto is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Job not found"
        )
    return _detail_response(dto)


@router.post(
    "/generate",
    response_model=QuizJobHandleResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def request_quiz_generation(
    request: QuizGenerationRequest,
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> QuizJobHandleResponse:
    repo = QuizJobRepository(session)
    ingestion_job = await repo.get_job(request.ingestion_job_id)
    if ingestion_job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Ingestion job not found"
        )
    if JobType(ingestion_job.job_type) != JobType.INGESTION:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provided job is not an ingestion job",
        )
    if JobStatus(ingestion_job.status) != JobStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ingestion job has not completed",
        )

    generation_payload = request.model_dump(mode="json")
    job = await repo.create_generation_job(
        parent_job_id=request.ingestion_job_id,
        payload=generation_payload,
    )
    generation_task = cast(SupportsDelay, generate_quiz)
    task = generation_task.delay(job.id, generation_payload)
    await repo.set_task_id(job.id, _extract_task_id(task))
    dto = await repo.to_dto(job)
    if dto is None:  # pragma: no cover
        raise HTTPException(status_code=500, detail="Failed to create quiz job")
    return _handle_response(dto)


@router.post(
    "/evaluate",
    response_model=QuizJobHandleResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def request_quiz_evaluation(
    request: QuizEvaluationRequest,
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> QuizJobHandleResponse:
    repo = QuizJobRepository(session)
    quiz_job = await repo.get_job(request.quiz_job_id)
    if quiz_job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Quiz job not found"
        )
    if JobType(quiz_job.job_type) != JobType.QUIZ_GENERATION:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provided job is not a quiz generation job",
        )
    if JobStatus(quiz_job.status) != JobStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Quiz generation job has not completed",
        )

    evaluation_payload = request.model_dump(mode="json")
    job = await repo.create_evaluation_job(
        parent_job_id=request.quiz_job_id,
        payload=evaluation_payload,
    )
    evaluation_task = cast(SupportsDelay, evaluate_answers)
    task = evaluation_task.delay(job.id, evaluation_payload)
    await repo.set_task_id(job.id, _extract_task_id(task))
    dto = await repo.to_dto(job)
    if dto is None:  # pragma: no cover
        raise HTTPException(status_code=500, detail="Failed to create evaluation job")
    return _handle_response(dto)
