"""Document models for storing uploaded educational materials."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

# Use the global Base class from storage module
# This enables cross-module foreign key resolution (e.g., quiz.doc_id -> source_document.id)
from eduagent.storage.models import Base


class SourceDocument(Base):
    """Represents a source document uploaded to the system."""

    __tablename__ = "source_document"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<SourceDocument(id={self.id}, filename='{self.filename}')>"


class DocumentArtifact(Base):
    """Represents derived artifacts for a source document."""

    __tablename__ = "document_artifact"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    doc_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("source_document.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    artifact_type: Mapped[str] = mapped_column(String(50), nullable=False)
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<DocumentArtifact(id={self.id}, doc_id={self.doc_id})>"


class DocumentChunk(Base):
    """Represents parsed chunks for a source document."""

    __tablename__ = "document_chunk"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    doc_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("source_document.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<DocumentChunk(id={self.id}, doc_id={self.doc_id})>"

# Pydantic models for API serialization
class DocumentCreate(BaseModel):
    """Schema for creating a document."""

    filename: str = Field(..., description="Original filename")
    file_size: int = Field(..., gt=0, description="File size in bytes")
    content_type: str = Field(..., description="MIME content type")


class DocumentResponse(BaseModel):
    """Schema for document response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    file_size: int
    content_type: str
    created_at: datetime
    updated_at: datetime


class DocumentParseRequest(BaseModel):
    """Schema for parsing a document."""

    doc_id: int = Field(..., gt=0, description="Source document ID")


class DocumentParseResponse(BaseModel):
    """Schema for document parse response."""

    doc_id: int
    chunk_count: int
    artifact_id: int
    artifact_path: str
