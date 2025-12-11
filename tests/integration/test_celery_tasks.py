from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from docx import Document as DocxDocument

from eduagent.quiz.enums import JobStatus
from eduagent.storage.database_service import DatabaseService, QuizJobCreate
from eduagent.storage.engine import async_engine
from eduagent.storage.minio_service import minio_service
from eduagent.tasks import quiz as quiz_tasks

pytestmark = pytest.mark.integration


def _create_docx_from_classes(tmp_path: Path) -> Path:
    content = Path("docs/classes.txt").read_text(encoding="utf-8")
    document = DocxDocument()
    max_lines = 5
    max_chars_per_line = 400
    line_count = 0
    for line in content.splitlines():
        stripped = line.strip()
        if stripped:
            document.add_paragraph(stripped[:max_chars_per_line])
            line_count += 1
            if line_count >= max_lines:
                break
    output_path = tmp_path / "classes.docx"
    document.save(str(output_path))
    return output_path


db_service = DatabaseService()


def test_celery_pipeline_runs_with_real_services(tmp_path: Path) -> None:
    docx_path = _create_docx_from_classes(tmp_path)
    with docx_path.open("rb") as file_obj:
        stored = minio_service.store_file(
            file_obj,
            filename=docx_path.name,
            content_type=(
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            ),
        )
    metadata = {
        "subject": "Software Engineering",
        "grade_level": "Undergraduate",
        "filename": docx_path.name,
        "original_filename": "classes.docx",
        "file_path": str(docx_path),
    }
    job_record = db_service.create_quiz_job(
        QuizJobCreate(
            source_filename=metadata["filename"],
            file_path=metadata["file_path"],
            subject=metadata["subject"],
            grade_level=metadata["grade_level"],
            job_payload=metadata,
        )
    )
    job_id = job_record.id
    document_job_id: str | None = None
    try:
        asyncio.run(async_engine.dispose())
        ingestion_result = quiz_tasks.process_textbook_upload(
            job_id,
            stored.object_name,
            metadata,
        )
        assert ingestion_result["chunks"] >= 1
        assert ingestion_result["embedded_records"] == ingestion_result["chunks"]

        job_state = db_service.get_quiz_job(job_id)
        assert job_state.status == JobStatus.COMPLETED
        assert (
            job_state.result_payload["document_job_id"]
            == ingestion_result["document_job_id"]
        )

        document_job_id = ingestion_result["document_job_id"]
        assert isinstance(document_job_id, str)
        document_job = db_service.get_document_job(document_job_id)
        assert document_job.total_chunks == ingestion_result["chunks"]

        total_questions = 3
        asyncio.run(async_engine.dispose())
        quiz_payload = quiz_tasks.generate_quiz(
            job_id,
            {
                "quiz_rules": {"total_questions": total_questions},
                "subject": metadata["subject"],
            },
        )
        assert len(quiz_payload["questions"]) == total_questions

        asyncio.run(async_engine.dispose())
        scoring = quiz_tasks.score_quiz_quality(
            job_id,
            {
                "questions": quiz_payload["questions"],
                "rules": quiz_payload["rules"],
            },
        )
        assert 0 <= scoring["quality"] <= 1
    finally:
        db_service.delete_quiz_job(job_id)
        if document_job_id:
            db_service.delete_document_job(document_job_id)
