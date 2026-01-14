from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import uuid4

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Json
from pydantic import BaseModel, Field



from eduagent.quiz.enums import JobStatus, JobType
from eduagent.quiz.schemas import QuizJobDTO
from eduagent.settings import settings


def _default_dsn() -> str:
    db = settings.database
    return f"postgresql://{db.user}:{db.password}@{db.host}:{db.port}/{db.name}"


class QuizJobCreate(BaseModel):
    job_type: JobType = JobType.INGESTION
    status: JobStatus = JobStatus.PENDING
    source_filename: str | None = None
    file_path: str | None = None
    subject: str | None = None
    grade_level: str | None = None
    job_payload: dict[str, Any] = Field(default_factory=dict)
    result_payload: dict[str, Any] = Field(default_factory=dict)
    parent_job_id: str | None = None
    job_id: str | None = None


class DocumentJobCreate(BaseModel):
    source_filename: str
    file_path: str
    subject: str | None = None
    grade_level: str | None = None
    status: str = "pending"
    job_metadata: dict[str, Any] = Field(default_factory=dict)
    total_chunks: int = 0
    job_id: str | None = None


class DocumentJobRecord(BaseModel):
    id: str
    source_filename: str
    file_path: str
    subject: str | None
    grade_level: str | None
    status: str
    error_message: str | None
    job_metadata: dict[str, Any]
    total_chunks: int
    created_at: datetime
    updated_at: datetime


@dataclass
class DatabaseService:
    """Synchronous helper for PostgreSQL-backed integration tests."""

    dsn: str = _default_dsn()

    def _connect(self) -> psycopg.Connection[Any]:
        return psycopg.connect(self.dsn)

    def create_quiz_job(self, data: QuizJobCreate) -> QuizJobDTO:
        job_uuid = data.job_id or str(uuid4())
        with self._connect() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                INSERT INTO quiz_pipeline_jobs (
                    id,
                    job_type,
                    status,
                    source_filename,
                    file_path,
                    subject,
                    grade_level,
                    job_payload,
                    result_payload,
                    parent_job_id
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING *
                """,
                (
                    job_uuid,
                    data.job_type.value,
                    data.status.value,
                    data.source_filename,
                    data.file_path,
                    data.subject,
                    data.grade_level,
                    Json(data.job_payload),
                    Json(data.result_payload),
                    data.parent_job_id,
                ),
            )
            row = cur.fetchone()
            conn.commit()
        if row is None:
            msg = "Failed to create quiz job"
            raise RuntimeError(msg)
        return self._row_to_quiz_job(row)

    def get_quiz_job(self, job_id: str) -> QuizJobDTO:
        with self._connect() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute("SELECT * FROM quiz_pipeline_jobs WHERE id=%s", (job_id,))
            row = cur.fetchone()
        if row is None:
            msg = f"Quiz job {job_id} not found"
            raise LookupError(msg)
        return self._row_to_quiz_job(row)

    def list_quiz_jobs(self, *, job_type: JobType | None = None) -> list[QuizJobDTO]:
        query = "SELECT * FROM quiz_pipeline_jobs"
        params: tuple[Any, ...] = ()
        if job_type:
            query += " WHERE job_type=%s"
            params = (job_type.value,)
        with self._connect() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(query, params)
            rows = cur.fetchall()
        return [self._row_to_quiz_job(row) for row in rows]

    def delete_quiz_job(self, job_id: str) -> bool:
        with self._connect() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute("DELETE FROM quiz_pipeline_jobs WHERE id=%s", (job_id,))
            deleted = cur.rowcount
            conn.commit()
        return bool(deleted)

    def create_document_job(self, data: DocumentJobCreate) -> DocumentJobRecord:
        job_uuid = data.job_id or str(uuid4())
        with self._connect() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                INSERT INTO document_ingestion_jobs (
                    id,
                    source_filename,
                    file_path,
                    subject,
                    grade_level,
                    status,
                    job_metadata,
                    total_chunks
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING *
                """,
                (
                    job_uuid,
                    data.source_filename,
                    data.file_path,
                    data.subject,
                    data.grade_level,
                    data.status,
                    Json(data.job_metadata),
                    data.total_chunks,
                ),
            )
            row = cur.fetchone()
            conn.commit()
        if row is None:
            msg = "Failed to create document job"
            raise RuntimeError(msg)
        return self._row_to_document_job(row)

    def get_document_job(self, job_id: str) -> DocumentJobRecord:
        with self._connect() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT * FROM document_ingestion_jobs WHERE id=%s",
                (job_id,),
            )
            row = cur.fetchone()
        if row is None:
            msg = f"Document job {job_id} not found"
            raise LookupError(msg)
        return self._row_to_document_job(row)

    def delete_document_job(self, job_id: str) -> bool:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("DELETE FROM document_ingestion_jobs WHERE id=%s", (job_id,))
            deleted = cur.rowcount
            conn.commit()
        return bool(deleted)

    @staticmethod
    def _row_to_quiz_job(row: dict[str, Any]) -> QuizJobDTO:
        job_payload = DatabaseService._normalize_json(row.get("job_payload"))
        result_payload = DatabaseService._normalize_json(row.get("result_payload"))
        return QuizJobDTO(
            id=row["id"],
            job_type=JobType(row["job_type"]),
            status=JobStatus(row["status"]),
            source_filename=row["source_filename"],
            file_path=row["file_path"],
            subject=row["subject"],
            grade_level=row["grade_level"],
            job_payload=job_payload,
            result_payload=result_payload,
            error_message=row["error_message"],
            task_id=row["task_id"],
            parent_job_id=row["parent_job_id"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    @staticmethod
    def _row_to_document_job(row: dict[str, Any]) -> DocumentJobRecord:
        metadata = DatabaseService._normalize_json(row.get("job_metadata"))
        return DocumentJobRecord(
            id=row["id"],
            source_filename=row["source_filename"],
            file_path=row["file_path"],
            subject=row["subject"],
            grade_level=row["grade_level"],
            status=row["status"],
            error_message=row["error_message"],
            job_metadata=metadata,
            total_chunks=int(row["total_chunks"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    @staticmethod
    def _normalize_json(value: dict[str, Any] | str | None) -> dict[str, Any]:
        if value is None:
            return {}
        if isinstance(value, dict):
            return dict(value)
        return json.loads(value)
