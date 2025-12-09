from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from eduagent.quiz.enums import JobStatus, JobType


class QuizJobDTO(BaseModel):
    """Pydantic representation of a quiz pipeline job."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    job_type: JobType
    status: JobStatus
    source_filename: str | None = None
    file_path: str | None = None
    subject: str | None = None
    grade_level: str | None = None
    job_payload: dict[str, Any] = Field(default_factory=dict)
    result_payload: dict[str, Any] = Field(default_factory=dict)
    error_message: str | None = None
    task_id: str | None = None
    parent_job_id: str | None = None
    created_at: datetime
    updated_at: datetime
