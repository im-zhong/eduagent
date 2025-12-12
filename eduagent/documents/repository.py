from __future__ import annotations

from collections.abc import Sequence
from typing import Any, TypedDict

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from eduagent.documents.models import DocumentChunk, DocumentIngestionJob, QuizArtifact


class ChunkExtras(TypedDict, total=False):
    metadata: dict[str, Any]
    milvus_vector_id: str | None


class DocumentRepository:
    """Data access methods for document ingestion workflow."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_job(
        self,
        *,
        source_filename: str,
        file_path: str,
        subject: str | None,
        grade_level: str | None,
        metadata: dict[str, Any] | None = None,
    ) -> DocumentIngestionJob:
        job = DocumentIngestionJob(
            source_filename=source_filename,
            file_path=file_path,
            subject=subject,
            grade_level=grade_level,
            job_metadata=metadata or {},
        )
        self.session.add(job)
        await self.session.commit()
        await self.session.refresh(job)
        return job

    async def get_job(self, job_id: str) -> DocumentIngestionJob | None:
        stmt = select(DocumentIngestionJob).where(DocumentIngestionJob.id == job_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_status(
        self,
        job_id: str,
        *,
        status: str,
        error_message: str | None = None,
        total_chunks: int | None = None,
    ) -> DocumentIngestionJob | None:
        job = await self.get_job(job_id)
        if job is None:
            return None
        job.status = status
        if error_message is not None:
            job.error_message = error_message
        if total_chunks is not None:
            job.total_chunks = total_chunks
        await self.session.commit()
        await self.session.refresh(job)
        return job

    async def add_chunk(
        self,
        job_id: str,
        *,
        chunk_index: int,
        content: str,
        token_count: int,
        extras: ChunkExtras | None = None,
    ) -> DocumentChunk | None:
        job = await self.get_job(job_id)
        if job is None:
            return None
        extras = extras or {}
        chunk = DocumentChunk(
            ingestion_job_id=job_id,
            chunk_index=chunk_index,
            content=content,
            token_count=token_count,
            chunk_metadata=extras.get("metadata") or {},
            milvus_vector_id=extras.get("milvus_vector_id"),
        )
        self.session.add(chunk)
        job.total_chunks += 1
        await self.session.commit()
        await self.session.refresh(chunk)
        return chunk

    async def set_chunk_vector_id(
        self,
        chunk_id: str,
        *,
        vector_id: str | None,
    ) -> DocumentChunk | None:
        stmt = select(DocumentChunk).where(DocumentChunk.id == chunk_id)
        result = await self.session.execute(stmt)
        chunk = result.scalar_one_or_none()
        if chunk is None:
            return None
        chunk.milvus_vector_id = vector_id
        await self.session.commit()
        await self.session.refresh(chunk)
        return chunk

    async def list_chunks(self, job_id: str) -> Sequence[DocumentChunk]:
        stmt = (
            select(DocumentChunk)
            .where(DocumentChunk.ingestion_job_id == job_id)
            .order_by(DocumentChunk.chunk_index.asc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def add_artifact(
        self,
        job_id: str,
        *,
        artifact_type: str,
        payload: dict[str, Any],
        pipeline_job_id: str | None = None,
        quality_score: float | None = None,
    ) -> QuizArtifact | None:
        job = await self.get_job(job_id)
        if job is None:
            return None
        artifact = QuizArtifact(
            ingestion_job_id=job_id,
            artifact_type=artifact_type,
            payload=payload,
            pipeline_job_id=pipeline_job_id,
            quality_score=quality_score,
        )
        self.session.add(artifact)
        await self.session.commit()
        await self.session.refresh(artifact)
        return artifact

    async def list_artifacts(self, job_id: str) -> Sequence[QuizArtifact]:
        stmt = (
            select(QuizArtifact)
            .where(QuizArtifact.ingestion_job_id == job_id)
            .order_by(QuizArtifact.created_at.asc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def delete_all(self) -> None:
        """Remove all ingestion data (artifacts, chunks, jobs) from the database."""
        await self.session.execute(delete(QuizArtifact))
        await self.session.execute(delete(DocumentChunk))
        await self.session.execute(delete(DocumentIngestionJob))
        await self.session.commit()
