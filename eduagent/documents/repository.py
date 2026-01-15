"""Document module repository helpers."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy import select

from eduagent.documents.models import DocumentArtifact, DocumentChunk, SourceDocument


async def fetch_source_document(
    session: AsyncSession,
    doc_id: int,
) -> SourceDocument | None:
    return await session.get(SourceDocument, doc_id)


async def create_document_artifact(
    session: AsyncSession,
    *,
    doc_id: int,
    artifact_type: str,
    storage_path: str,
) -> DocumentArtifact:
    artifact = DocumentArtifact(
        doc_id=doc_id,
        artifact_type=artifact_type,
        storage_path=storage_path,
    )
    session.add(artifact)
    await session.commit()
    await session.refresh(artifact)
    return artifact


async def create_document_chunks(
    session: AsyncSession,
    *,
    doc_id: int,
    chunks: list[str],
) -> list[DocumentChunk]:
    chunk_rows = [
        DocumentChunk(doc_id=doc_id, chunk_index=index, text=text)
        for index, text in enumerate(chunks)
    ]
    session.add_all(chunk_rows)
    await session.commit()
    for chunk in chunk_rows:
        await session.refresh(chunk)
    return chunk_rows


async def list_document_chunks(
    session: AsyncSession,
    doc_id: int,
) -> list[DocumentChunk]:
    result = await session.execute(
        select(DocumentChunk)
        .where(DocumentChunk.doc_id == doc_id)
        .order_by(DocumentChunk.chunk_index.asc())
    )
    return list(result.scalars().all())
