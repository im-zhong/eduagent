from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from eduagent.user.models import Base


def _uuid_str() -> str:
    return str(uuid4())


class DocumentIngestionJob(Base):
    """Tracks ingestion jobs for uploaded instructional documents."""

    __tablename__ = "document_ingestion_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid_str)
    source_filename: Mapped[str] = mapped_column(String(255))
    file_path: Mapped[str] = mapped_column(String(1024))
    subject: Mapped[str | None] = mapped_column(String(128), nullable=True)
    grade_level: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    job_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSON, default=dict, nullable=False
    )
    total_chunks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    chunks: Mapped[list[DocumentChunk]] = relationship(
        back_populates="ingestion_job",
        cascade="all, delete-orphan",
    )
    artifacts: Mapped[list[QuizArtifact]] = relationship(
        back_populates="ingestion_job",
        cascade="all, delete-orphan",
    )


class DocumentChunk(Base):
    """Stores extracted chunk metadata; embeddings live in Milvus."""

    __tablename__ = "document_chunks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid_str)
    ingestion_job_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("document_ingestion_jobs.id", ondelete="CASCADE"),
        nullable=False,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    chunk_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSON, default=dict, nullable=False
    )
    milvus_vector_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    ingestion_job: Mapped[DocumentIngestionJob] = relationship(back_populates="chunks")


class QuizArtifact(Base):
    """Artifacts generated from ingestion such as quizzes or evaluations."""

    __tablename__ = "quiz_artifacts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid_str)
    ingestion_job_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("document_ingestion_jobs.id", ondelete="CASCADE"),
        nullable=False,
    )
    pipeline_job_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True, doc="Link to quiz pipeline job if available."
    )
    artifact_type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    ingestion_job: Mapped[DocumentIngestionJob] = relationship(
        back_populates="artifacts"
    )
