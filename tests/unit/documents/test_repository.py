"""Unit tests for document repository operations.

Tests the CRUD functions in the documents repository module.
Uses real database from settings for integration-style testing in dev container.
"""
from __future__ import annotations

import pytest
import pytest_asyncio

from eduagent.documents.models import DocumentArtifact, DocumentChunk, SourceDocument
from eduagent.documents.repository import (
    create_document_artifact,
    create_document_chunks,
    fetch_source_document,
    list_document_chunks,
)


# ================================
# Test Fixtures
# ================================


@pytest_asyncio.fixture(scope="function")
async def test_document(db_session) -> SourceDocument:
    """Create a test document in the database."""
    doc = SourceDocument(
        filename="test_document.pdf",
        storage_path="documents/test.pdf",
        file_size=1024,
        content_type="application/pdf",
    )
    db_session.add(doc)
    await db_session.commit()
    await db_session.refresh(doc)
    return doc


# ================================
# fetch_source_document() Tests
# ================================


class TestFetchSourceDocument:
    """Test the fetch_source_document repository function."""

    @pytest.mark.asyncio
    async def test_fetch_existing_document(
        self, db_session, test_document: SourceDocument
    ) -> None:
        """Test fetching an existing document by ID."""
        result = await fetch_source_document(db_session, test_document.id)
        assert result is not None
        assert result.id == test_document.id
        assert result.filename == "test_document.pdf"
        assert result.file_size == 1024

    @pytest.mark.asyncio
    async def test_fetch_nonexistent_document(self, db_session) -> None:
        """Test fetching a non-existent document returns None."""
        result = await fetch_source_document(db_session, 99999)
        assert result is None


# ================================
# create_document_artifact() Tests
# ================================


class TestCreateDocumentArtifact:
    """Test the create_document_artifact repository function."""

    @pytest.mark.asyncio
    async def test_create_artifact_success(
        self, db_session, test_document: SourceDocument
    ) -> None:
        """Test successfully creating a document artifact."""
        artifact = await create_document_artifact(
            db_session,
            doc_id=test_document.id,
            artifact_type="markdown",
            storage_path="artifacts/test.md",
        )

        assert artifact.id > 0
        assert artifact.doc_id == test_document.id
        assert artifact.artifact_type == "markdown"
        assert artifact.storage_path == "artifacts/test.md"
        assert artifact.created_at is not None

    @pytest.mark.asyncio
    async def test_create_multiple_artifacts(
        self, db_session, test_document: SourceDocument
    ) -> None:
        """Test creating multiple artifacts for the same document."""
        artifact_types = ["markdown", "chunks", "metadata"]

        artifacts = []
        for artifact_type in artifact_types:
            artifact = await create_document_artifact(
                db_session,
                doc_id=test_document.id,
                artifact_type=artifact_type,
                storage_path=f"artifacts/{artifact_type}.json",
            )
            artifacts.append(artifact)

        assert len(artifacts) == 3
        assert all(a.doc_id == test_document.id for a in artifacts)
        assert artifacts[0].artifact_type == "markdown"
        assert artifacts[1].artifact_type == "chunks"
        assert artifacts[2].artifact_type == "metadata"


# ================================
# create_document_chunks() Tests
# ================================


class TestCreateDocumentChunks:
    """Test the create_document_chunks repository function."""

    @pytest.mark.asyncio
    async def test_create_chunks_success(
        self, db_session, test_document: SourceDocument
    ) -> None:
        """Test successfully creating document chunks."""
        chunks_text = ["First chunk", "Second chunk", "Third chunk"]

        chunks = await create_document_chunks(
            db_session,
            doc_id=test_document.id,
            chunks=chunks_text,
        )

        assert len(chunks) == 3
        assert chunks[0].chunk_index == 0
        assert chunks[0].text == "First chunk"
        assert chunks[1].chunk_index == 1
        assert chunks[1].text == "Second chunk"
        assert chunks[2].chunk_index == 2
        assert chunks[2].text == "Third chunk"
        assert all(c.doc_id == test_document.id for c in chunks)

    @pytest.mark.asyncio
    async def test_create_single_chunk(self, db_session, test_document: SourceDocument) -> None:
        """Test creating a single chunk."""
        chunks = await create_document_chunks(
            db_session,
            doc_id=test_document.id,
            chunks=["Only chunk"],
        )

        assert len(chunks) == 1
        assert chunks[0].chunk_index == 0
        assert chunks[0].text == "Only chunk"

    @pytest.mark.asyncio
    async def test_create_empty_chunks(self, db_session, test_document: SourceDocument) -> None:
        """Test creating empty chunks list."""
        chunks = await create_document_chunks(
            db_session,
            doc_id=test_document.id,
            chunks=[],
        )

        assert len(chunks) == 0

    @pytest.mark.asyncio
    async def test_create_chunks_with_unicode(
        self, db_session, test_document: SourceDocument
    ) -> None:
        """Test creating chunks with unicode content."""
        chunks_text = ["Hello 世界", "Test 中文", "Mix 合 mix"]

        chunks = await create_document_chunks(
            db_session,
            doc_id=test_document.id,
            chunks=chunks_text,
        )

        assert len(chunks) == 3
        assert chunks[0].text == "Hello 世界"
        assert chunks[1].text == "Test 中文"
        assert chunks[2].text == "Mix 合 mix"


# ================================
# list_document_chunks() Tests
# ================================


class TestListDocumentChunks:
    """Test the list_document_chunks repository function."""

    @pytest.mark.asyncio
    async def test_list_chunks_ordered_by_index(
        self, db_session, test_document: SourceDocument
    ) -> None:
        """Test that chunks are returned in order by chunk_index."""
        # Create chunks
        chunks_text = ["First", "Second", "Third"]
        await create_document_chunks(
            db_session,
            doc_id=test_document.id,
            chunks=chunks_text,
        )

        # List chunks
        chunks = await list_document_chunks(db_session, test_document.id)

        assert len(chunks) == 3
        assert chunks[0].chunk_index == 0
        assert chunks[1].chunk_index == 1
        assert chunks[2].chunk_index == 2
        assert chunks[0].text == "First"
        assert chunks[1].text == "Second"
        assert chunks[2].text == "Third"

    @pytest.mark.asyncio
    async def test_list_chunks_for_nonexistent_document(self, db_session) -> None:
        """Test listing chunks for non-existent document returns empty list."""
        chunks = await list_document_chunks(db_session, 99999)
        assert chunks == []

    @pytest.mark.asyncio
    async def test_list_chunks_when_none_exist(
        self, db_session, test_document: SourceDocument
    ) -> None:
        """Test listing chunks when document has no chunks."""
        chunks = await list_document_chunks(db_session, test_document.id)
        assert chunks == []


# ================================
# End-to-End Workflow Tests
# ================================


class TestDocumentWorkflows:
    """Test complete document workflows."""

    @pytest.mark.asyncio
    async def test_full_document_processing_workflow(self, db_session) -> None:
        """Test complete workflow: create document -> add chunks -> add artifact."""
        # Step 1: Create document
        doc = SourceDocument(
            filename="workflow_test.pdf",
            storage_path="documents/workflow.pdf",
            file_size=2048,
            content_type="application/pdf",
        )
        db_session.add(doc)
        await db_session.commit()
        await db_session.refresh(doc)

        # Step 2: Verify document can be fetched
        fetched_doc = await fetch_source_document(db_session, doc.id)
        assert fetched_doc is not None
        assert fetched_doc.filename == "workflow_test.pdf"

        # Step 3: Create chunks
        chunks_text = ["Chunk 1", "Chunk 2", "Chunk 3", "Chunk 4"]
        chunks = await create_document_chunks(
            db_session,
            doc_id=doc.id,
            chunks=chunks_text,
        )
        assert len(chunks) == 4

        # Step 4: List chunks and verify
        listed_chunks = await list_document_chunks(db_session, doc.id)
        assert len(listed_chunks) == 4
        assert [c.text for c in listed_chunks] == chunks_text

        # Step 5: Create artifact
        artifact = await create_document_artifact(
            db_session,
            doc_id=doc.id,
            artifact_type="processed",
            storage_path="artifacts/processed.json",
        )
        assert artifact.doc_id == doc.id
        assert artifact.artifact_type == "processed"

    @pytest.mark.asyncio
    async def test_multiple_documents_with_chunks(self, db_session) -> None:
        """Test handling multiple documents, each with their own chunks."""
        # Create multiple documents
        docs = []
        for i in range(3):
            doc = SourceDocument(
                filename=f"doc_{i}.pdf",
                storage_path=f"documents/doc_{i}.pdf",
                file_size=1000 + i,
                content_type="application/pdf",
            )
            db_session.add(doc)
            await db_session.commit()
            await db_session.refresh(doc)
            docs.append(doc)

        # Add chunks to each document
        for doc in docs:
            await create_document_chunks(
                db_session,
                doc_id=doc.id,
                chunks=[f"{doc.filename} chunk {j}" for j in range(2)],
            )

        # Verify each document has correct chunks
        for doc in docs:
            chunks = await list_document_chunks(db_session, doc.id)
            assert len(chunks) == 2
            assert all(c.doc_id == doc.id for c in chunks)
            assert doc.filename in chunks[0].text
