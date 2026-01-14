"""Document API endpoints for file upload and list management."""
from fastapi import APIRouter, File, UploadFile, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from eduagent.documents.models import (
    DocumentCreate,
    DocumentResponse,
    SourceDocument,
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

    # Read file content
    file_data = await file.read()

    # Generate object name
    object_name = MinIOStorage.generate_object_name(file.filename or "unknown")

    # Upload to MinIO
    await minio_storage.upload_file(
        file_data=file_data,
        object_name=object_name,
        content_type=file.content_type or "application/octet-stream",
    )

    # Create document record
    document = SourceDocument(
        filename=file.filename or "unknown",
        storage_path=object_name,
        file_size=len(file_data),
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
        from fastapi import HTTPException

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with id {document_id} not found",
        )

    return DocumentResponse.model_validate(document)
