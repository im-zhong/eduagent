from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from eduagent.quiz.enums import JobStatus, JobType
from eduagent.storage.database_service import (
    DatabaseService,
    DocumentJobCreate,
    QuizJobCreate,
)

service = DatabaseService()


def test_quiz_job_crud() -> None:
    unique_file = f"/tmp/{uuid4()}.docx"
    job = service.create_quiz_job(
        QuizJobCreate(
            job_type=JobType.INGESTION,
            status=JobStatus.PENDING,
            source_filename=Path(unique_file).name,
            file_path=unique_file,
            subject="Mathematics",
            grade_level="Grade 10",
            job_payload={"topic": "Algebra"},
        )
    )
    try:
        fetched = service.get_quiz_job(job.id)
        assert fetched.id == job.id
        assert fetched.job_payload["topic"] == "Algebra"

        jobs = service.list_quiz_jobs()
        assert any(record.id == job.id for record in jobs)
    finally:
        assert service.delete_quiz_job(job.id)


def test_document_job_crud() -> None:
    unique_path = f"/tmp/{uuid4()}.docx"
    record = service.create_document_job(
        DocumentJobCreate(
            source_filename=Path(unique_path).name,
            file_path=unique_path,
            subject="Physics",
            grade_level="Undergraduate",
            job_metadata={"unit": "Mechanics"},
        )
    )
    try:
        fetched = service.get_document_job(record.id)
        assert fetched.id == record.id
        assert fetched.job_metadata["unit"] == "Mechanics"
        assert fetched.total_chunks == 0
    finally:
        assert service.delete_document_job(record.id)
