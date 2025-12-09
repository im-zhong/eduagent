from __future__ import annotations

from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from eduagent.documents.models import (
    DocumentChunk,
    DocumentIngestionJob,
    QuizArtifact,
)
from eduagent.user.models import Base


@pytest.fixture
def session() -> Iterator[Session]:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    session = Session(bind=engine)
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def test_document_ingestion_job_relationships(session: Session) -> None:
    job = DocumentIngestionJob(
        source_filename="chapter1.docx",
        file_path="/tmp/chapter1.docx",
        subject="science",
        grade_level="grade-8",
        job_metadata={"language": "zh"},
    )
    job.chunks.append(
        DocumentChunk(
            chunk_index=0,
            content="Photosynthesis is the process by which plants convert light.",
            token_count=10,
            chunk_metadata={"section": "intro"},
            milvus_vector_id="vector-1",
        )
    )
    job.artifacts.append(
        QuizArtifact(
            artifact_type="quiz",
            payload={"questions": [{"prompt": "What is photosynthesis?"}]},
            quality_score=0.92,
        )
    )
    session.add(job)
    session.commit()

    stored = session.get(DocumentIngestionJob, job.id)
    assert stored is not None
    assert stored.status == "pending"
    assert stored.total_chunks == 0
    assert len(stored.chunks) == 1
    assert stored.chunks[0].ingestion_job_id == job.id
    assert stored.artifacts[0].artifact_type == "quiz"


def test_cascade_delete_removes_children(session: Session) -> None:
    job = DocumentIngestionJob(
        source_filename="history.docx",
        file_path="/tmp/history.docx",
    )
    job.chunks.append(
        DocumentChunk(chunk_index=0, content="World War II overview.", token_count=5)
    )
    job.artifacts.append(
        QuizArtifact(artifact_type="evaluation", payload={"score": 0.8})
    )
    session.add(job)
    session.commit()

    session.delete(job)
    session.commit()

    assert session.get(DocumentIngestionJob, job.id) is None
    assert session.query(DocumentChunk).count() == 0
    assert session.query(QuizArtifact).count() == 0
