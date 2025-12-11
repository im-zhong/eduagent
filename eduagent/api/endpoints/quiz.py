from __future__ import annotations

from typing import Annotated, Any, Protocol, cast, runtime_checkable
from uuid import uuid4

from celery.result import AsyncResult
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from eduagent.api.schemas import (
    QuizEvaluationPayload,
    QuizEvaluationRequest,
    QuizGenerationPayload,
    QuizGenerationRequest,
    QuizJobDetailResponse,
    QuizJobHandleResponse,
    QuizScoringPayload,
    QuizScoringRequest,
    QuizWorkflowRequest,
    QuizWorkflowResponse,
    SubjectArea,
    TextbookUploadMetadata,
)
from eduagent.documents.repository import DocumentRepository
from eduagent.logger import get_logger
from eduagent.quiz.enums import JobStatus, JobType
from eduagent.quiz.repository import QuizJobRepository
from eduagent.quiz.schemas import QuizJobDTO
from eduagent.quiz.workflow import QuizWorkflowRunner
from eduagent.storage.engine import get_async_session
from eduagent.storage.minio_service import minio_service
from eduagent.tasks.quiz import (
    evaluate_answers,
    generate_quiz,
    process_textbook_upload,
    score_quiz_quality,
)


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
api_logger = get_logger(__name__, component="api.quiz")


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

    api_logger.info(
        f"Received quiz upload request subject={subject.value} grade={grade_level}"
    )
    original_filename = file.filename or "uploaded_textbook"
    stored_object = minio_service.store_file(
        file.file,
        filename=original_filename,
        content_type=file.content_type,
        metadata={
            "subject": subject.value,
            "grade_level": grade_level,
            "uuid": uuid4().hex,
        },
    )

    repo = QuizJobRepository(session)
    job = await repo.create_ingestion_job(
        source_filename=original_filename,
        file_path=f"minio://{stored_object.bucket}/{stored_object.object_name}",
        subject=subject.value,
        grade_level=grade_level,
        payload={
            "content_type": file.content_type,
            "subject": subject.value,
            "grade_level": grade_level,
            "object_id": stored_object.object_id,
        },
    )
    upload_task = cast(SupportsDelay, process_textbook_upload)
    metadata = TextbookUploadMetadata(
        filename=stored_object.object_name,
        original_filename=original_filename,
        subject=subject,
        grade_level=grade_level,
        extra={
            "content_type": file.content_type or "application/octet-stream",
            "object_id": stored_object.object_id,
        },
    )
    task = upload_task.delay(
        job.id,
        stored_object.object_id,
        metadata,
    )
    await repo.set_task_id(job.id, _extract_task_id(task))
    dto = await repo.to_dto(job)
    if dto is None:  # pragma: no cover - safety guard
        raise HTTPException(status_code=500, detail="Failed to create ingestion job")
    api_logger.info(f"Queued ingestion job {job.id} for {original_filename}")
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
        api_logger.warning(f"Quiz job {job_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Job not found"
        )
    api_logger.debug(f"Returning quiz job details for {job_id}")
    return _detail_response(dto)


@router.post(
    "/workflow",
    response_model=QuizWorkflowResponse,
    status_code=status.HTTP_200_OK,
)
async def run_quiz_workflow_endpoint(
    request: QuizWorkflowRequest,
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> QuizWorkflowResponse:
    doc_repo = DocumentRepository(session)
    runner = QuizWorkflowRunner(doc_repo)
    try:
        result = await runner.run(request.ingestion_job_id, request.prompt)
    except ValueError as exc:
        api_logger.warning(
            f"Workflow run failed for ingestion job {request.ingestion_job_id}: {exc}"
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    api_logger.info(f"Workflow completed for ingestion job {request.ingestion_job_id}")
    return QuizWorkflowResponse(**result)


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
        api_logger.warning(
            f"Quiz generation requested for missing ingestion job {request.ingestion_job_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Ingestion job not found"
        )
    if JobType(ingestion_job.job_type) != JobType.INGESTION:
        api_logger.warning(
            f"Invalid job type for generation request {request.ingestion_job_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provided job is not an ingestion job",
        )
    if JobStatus(ingestion_job.status) != JobStatus.COMPLETED:
        api_logger.warning(
            f"Generation requested before completion for job {request.ingestion_job_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ingestion job has not completed",
        )

    generation_payload = QuizGenerationPayload(
        job_id=request.ingestion_job_id,
        query=request.query,
        rules=request.quiz_rules,
        subject=request.subject,
    )
    job = await repo.create_generation_job(
        parent_job_id=request.ingestion_job_id,
        payload=generation_payload.model_dump(mode="json"),
    )
    generation_task = cast(SupportsDelay, generate_quiz)
    task = generation_task.delay(job.id, generation_payload)
    await repo.set_task_id(job.id, _extract_task_id(task))
    dto = await repo.to_dto(job)
    if dto is None:  # pragma: no cover
        raise HTTPException(status_code=500, detail="Failed to create quiz job")
    api_logger.info(
        f"Queued quiz generation job {job.id} from ingestion job {request.ingestion_job_id}"
    )
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
        api_logger.warning(
            f"Evaluation requested for missing quiz job {request.quiz_job_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Quiz job not found"
        )
    if JobType(quiz_job.job_type) != JobType.QUIZ_GENERATION:
        api_logger.warning(
            f"Evaluation request {request.quiz_job_id} is not a generation job"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provided job is not a quiz generation job",
        )
    if JobStatus(quiz_job.status) != JobStatus.COMPLETED:
        api_logger.warning(
            f"Evaluation requested before completion for quiz job {request.quiz_job_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Quiz generation job has not completed",
        )

    evaluation_payload = QuizEvaluationPayload(
        job_id=request.quiz_job_id,
        answers=request.answers,
    )
    job = await repo.create_evaluation_job(
        parent_job_id=request.quiz_job_id,
        payload=evaluation_payload.model_dump(mode="json"),
    )
    evaluation_task = cast(SupportsDelay, evaluate_answers)
    task = evaluation_task.delay(job.id, evaluation_payload)
    await repo.set_task_id(job.id, _extract_task_id(task))
    dto = await repo.to_dto(job)
    if dto is None:  # pragma: no cover
        raise HTTPException(status_code=500, detail="Failed to create evaluation job")
    api_logger.info(
        f"Queued quiz evaluation job {job.id} for quiz job {request.quiz_job_id}"
    )
    return _handle_response(dto)


@router.post(
    "/score",
    response_model=QuizJobHandleResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def request_quiz_scoring(
    request: QuizScoringRequest,
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> QuizJobHandleResponse:
    repo = QuizJobRepository(session)
    quiz_job = await repo.get_job(request.quiz_job_id)
    if quiz_job is None:
        api_logger.warning(
            f"Scoring requested for missing quiz job {request.quiz_job_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Quiz job not found"
        )
    scoring_payload = QuizScoringPayload(
        job_id=request.quiz_job_id,
        questions=request.questions,
        rules=request.rules,
    )
    job = await repo.create_scoring_job(
        parent_job_id=request.quiz_job_id,
        payload=scoring_payload.model_dump(mode="json"),
    )
    scoring_task = cast(SupportsDelay, score_quiz_quality)
    task = scoring_task.delay(job.id, scoring_payload)
    await repo.set_task_id(job.id, _extract_task_id(task))
    dto = await repo.to_dto(job)
    if dto is None:  # pragma: no cover
        raise HTTPException(status_code=500, detail="Failed to create scoring job")
    api_logger.info(
        f"Queued quiz scoring job {job.id} for quiz job {request.quiz_job_id}"
    )
    return _handle_response(dto)
