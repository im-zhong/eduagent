from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import JSON, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from eduagent.quiz.enums import JobStatus
from eduagent.user.models import Base


def _uuid_str() -> str:
    return str(uuid4())


class QuizPipelineJob(Base):
    """Generic job table to track ingestion, generation and evaluation tasks."""

    __tablename__ = "quiz_pipeline_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid_str)
    job_type: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(
        String(32), default=JobStatus.PENDING.value, nullable=False
    )
    source_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    file_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    subject: Mapped[str | None] = mapped_column(String(128), nullable=True)
    grade_level: Mapped[str | None] = mapped_column(String(128), nullable=True)
    job_payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    result_payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    task_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    parent_job_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
