"""Database access for document records."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from eduagent.documents.models import SourceDocument


async def fetch_source_document(
    session: AsyncSession, doc_id: int
) -> SourceDocument | None:
    return await session.get(SourceDocument, doc_id)
