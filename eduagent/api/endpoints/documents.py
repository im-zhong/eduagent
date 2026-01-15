"""Document API endpoints for file upload and list management."""
from datetime import datetime
from io import BytesIO
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from eduagent.documents.converter import parse_document_to_chunks
from eduagent.documents.models import (
    DocumentCreate,
    DocumentParseRequest,
    DocumentParseResponse,
    DocumentResponse,
    SourceDocument,
)
from eduagent.documents.repository import (
    create_document_artifact,
    create_document_chunks,
    fetch_source_document,
)
from eduagent.logger import get_logger
from eduagent.settings import settings
from eduagent.storage.engine import get_async_session
from eduagent.storage.minio_client import MinIOConfig, MinIOStorage

logger = get_logger(__name__, component="api.documents")

# Create MinIO storage instance
minio_storage = MinIOStorage(
    config=MinIOConfig(
        endpoint=settings.minio.endpoint,
        access_key=settings.minio.access_key,
        secret_key=settings.minio.secret_key,
        secure=settings.minio.secure,
        bucket=settings.minio.bucket,
    )
)

# Create router
router = APIRouter()


@router.post(
    "/documents",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a document",
)
async def upload_document(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_async_session),
) -> DocumentResponse:
    """
    Upload a document file to the system.

    - **file**: The document file to upload
    - Returns: Document metadata including id, filename, file_size, content_type
    """
    logger.info("Uploading document: %s", file.filename)

    # Generate object name
    object_name = MinIOStorage.generate_object_name(file.filename or "unknown")

    # Upload to MinIO using UploadFile.file (thread-safe BinaryIO)
    await minio_storage.upload_file(
        file_data=file.file,
        object_name=object_name,
        content_type=file.content_type or "application/octet-stream",
        length=file.size,
    )

    # Create document record
    document = SourceDocument(
        filename=file.filename or "unknown",
        storage_path=object_name,
        file_size=file.size,
        content_type=file.content_type or "application/octet-stream",
    )

    session.add(document)
    await session.commit()
    await session.refresh(document)

    logger.info("Document uploaded successfully: id=%d, filename=%s", document.id, document.filename)
    return DocumentResponse.model_validate(document)


@router.get(
    "/documents",
    response_model=list[DocumentResponse],
    summary="List all documents",
)
async def list_documents(
    session: AsyncSession = Depends(get_async_session),
) -> list[DocumentResponse]:
    """
    List all uploaded documents.

    - Returns: List of document metadata sorted by creation date (newest first)
    """
    logger.debug("Listing all documents")

    result = await session.execute(
        select(SourceDocument).order_by(SourceDocument.created_at.desc())
    )
    documents = result.scalars().all()

    logger.debug("Found %d documents", len(documents))
    return [DocumentResponse.model_validate(doc) for doc in documents]


@router.get(
    "/documents/{document_id}",
    response_model=DocumentResponse,
    summary="Get document by ID",
)
async def get_document(
    document_id: int,
    session: AsyncSession = Depends(get_async_session),
) -> DocumentResponse:
    """
    Get a specific document by its ID.

    - **document_id**: The ID of the document to retrieve
    - Returns: Document metadata
    """
    logger.debug("Getting document: id=%d", document_id)

    result = await session.execute(
        select(SourceDocument).where(SourceDocument.id == document_id)
    )
    document = result.scalar_one_or_none()

    if not document:
        logger.warning("Document not found: id=%d", document_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with id {document_id} not found",
        )

    return DocumentResponse.model_validate(document)


@router.post(
    "/documents/parse",
    response_model=DocumentParseResponse,
    summary="Parse a document into markdown and chunks",
)
async def parse_document(
    payload: DocumentParseRequest,
    session: AsyncSession = Depends(get_async_session),
) -> DocumentParseResponse:
    """
    Convert the stored document into markdown and chunk it for downstream RAG.

    Progress:
    1) Load the source document record.
    2) Download the source file from MinIO.
    3) Convert to markdown via pandoc (async thread offload).
    4) Persist markdown artifact to MinIO.
    5) Persist chunks to Postgres for easier dev/test and inspection.
    """
    document = await fetch_source_document(session, payload.doc_id)
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with id {payload.doc_id} not found",
        )

    # Use a temp file so pandoc can infer format by extension.
    source_bytes = await minio_storage.download_file(document.storage_path)
    suffix = Path(document.filename).suffix or ".bin"
    temp_path = Path(f"/tmp/doc_{document.id}{suffix}")
    temp_path.write_bytes(source_bytes)

    try:
        markdown, chunks = await parse_document_to_chunks(temp_path)
    finally:
        temp_path.unlink(missing_ok=True)

    # Store markdown artifact as a stable input for later RAG stages.
    object_name = (
        f"documents/{document.id}/parsed_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.md"
    )
    markdown_bytes = markdown.encode("utf-8")
    await minio_storage.upload_file(
        file_data=BytesIO(markdown_bytes),
        object_name=object_name,
        content_type="text/markdown",
        length=len(markdown_bytes),
    )

    artifact = await create_document_artifact(
        session,
        doc_id=document.id,
        artifact_type="parsed_markdown",
        storage_path=object_name,
    )
    await create_document_chunks(
        session,
        doc_id=document.id,
        chunks=chunks,
    )

    return DocumentParseResponse(
        doc_id=document.id,
        chunk_count=len(chunks),
        artifact_id=artifact.id,
        artifact_path=artifact.storage_path,
    )
