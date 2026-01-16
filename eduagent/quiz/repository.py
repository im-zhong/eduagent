"""Quiz repository for database operations.

Repository functions use flush() to get IDs but do NOT commit.
Commit/rollback is handled automatically by the transactional get_async_session() dependency.
See: docs/db/transactional-session.md
See: docs/db/flush-vs-commit.md
"""
from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from eduagent.quiz.models import (
    Quiz,
    QuizReference,
    QuizResponse,
    QuizWithReferenceResponse,
)


async def create_quiz(
    session: AsyncSession, doc_id: int, source: str, question_json: str
) -> Quiz:
    """Create a new quiz record.

    Args:
        session: Database session (commit handled by transactional dependency)
        doc_id: Source document ID
        source: Quiz source type (e.g., "generated", "extracted")
        question_json: Serialized question data as JSON string

    Returns:
        Created quiz record with ID populated (after flush)

    Note:
        Uses flush() to get auto-generated ID but does NOT commit.
        Commit is handled by get_async_session() dependency.
    """
    quiz = Quiz(doc_id=doc_id, source=source, question_json=question_json)
    session.add(quiz)
    await session.flush()  # Get ID from DB, but keep transaction open
    return quiz


async def create_quiz_with_references(
    session: AsyncSession,
    doc_id: int,
    source: str,
    question_json: str,
    reference_texts: list[tuple[str, int | None]],
) -> Quiz:
    """Create a quiz with associated reference texts.

    Args:
        session: Database session (commit handled by transactional dependency)
        doc_id: Source document ID
        source: Quiz source type
        question_json: Serialized question data
        reference_texts: List of (reference_text, chunk_index) tuples

    Returns:
        Created quiz record with ID populated

    Note:
        Flushes quiz first to get quiz.id, then creates references.
        All records committed together by get_async_session() dependency.
    """
    quiz = Quiz(doc_id=doc_id, source=source, question_json=question_json)
    session.add(quiz)
    await session.flush()  # Flush to get quiz.id for QuizReference foreign key

    for ref_text, chunk_idx in reference_texts:
        ref = QuizReference(
            quiz_id=quiz.id, reference_text=ref_text, chunk_index=chunk_idx
        )
        session.add(ref)

    return quiz


async def get_quiz_by_id(session: AsyncSession, quiz_id: int) -> Quiz | None:
    """Get a quiz by its ID.

    Args:
        session: Database session
        quiz_id: Quiz ID to fetch

    Returns:
        Quiz record or None if not found
    """
    result = await session.execute(select(Quiz).where(Quiz.id == quiz_id))
    return result.scalar_one_or_none()


async def get_quizzes_by_document(
    session: AsyncSession, doc_id: int
) -> Sequence[Quiz]:
    """Get all quizzes for a document.

    Args:
        session: Database session
        doc_id: Document ID to fetch quizzes for

    Returns:
        Sequence of quiz records, ordered by creation date (newest first)

    Note:
        Does NOT include reference texts. Use get_quizzes_with_references_by_document()
        if you need references.
    """
    result = await session.execute(
        select(Quiz).where(Quiz.doc_id == doc_id).order_by(Quiz.created_at.desc())
    )
    return result.scalars().all()


async def get_quizzes_with_references_by_document(
    session: AsyncSession, doc_id: int
) -> list[QuizWithReferenceResponse]:
    """Get all quizzes with their references for a document.

    Args:
        session: Database session
        doc_id: Document ID to fetch quizzes for

    Returns:
        List of quizzes with reference texts, ordered by creation date (newest first)

    Note:
        Uses joinedload for eager loading to avoid N+1 queries.
        Performs a LEFT JOIN, so quizzes without references are still included.
    """
    result = await session.execute(
        select(Quiz)
        .options(joinedload(Quiz.quiz_references))
        .where(Quiz.doc_id == doc_id)
        .order_by(Quiz.created_at.desc())
    )
    quizzes = result.scalars().unique().all()

    responses = []
    for quiz in quizzes:
        refs = (
            [ref.reference_text for ref in quiz.quiz_references]
            if quiz.quiz_references
            else []
        )
        responses.append(
            QuizWithReferenceResponse(
                id=quiz.id,
                doc_id=quiz.doc_id,
                source=quiz.source,
                question_json=quiz.question_json,
                references=refs,
                created_at=quiz.created_at,
            )
        )

    return responses


async def delete_quiz(session: AsyncSession, quiz_id: int) -> bool:
    """Delete a quiz by its ID.

    Args:
        session: Database session (commit handled by transactional dependency)
        quiz_id: Quiz ID to delete

    Returns:
        True if quiz was deleted, False if not found

    Note:
        QuizReference records are deleted automatically via CASCADE foreign key.
    """
    result = await session.execute(delete(Quiz).where(Quiz.id == quiz_id))
    return result.rowcount > 0


async def delete_quizzes_by_doc(session: AsyncSession, doc_id: int) -> int:
    """Delete all quizzes for a document.

    Args:
        session: Database session (commit handled by transactional dependency)
        doc_id: Document ID whose quizzes should be deleted

    Returns:
        Number of quizzes deleted

    Note:
        QuizReference records are deleted automatically via CASCADE foreign key.
    """
    result = await session.execute(delete(Quiz).where(Quiz.doc_id == doc_id))
    return result.rowcount


async def get_quizzes_by_doc(session: AsyncSession, doc_id: int) -> Sequence[Quiz]:
    """Get all quizzes for a document (alias for get_quizzes_by_document).

    Args:
        session: Database session
        doc_id: Document ID to fetch quizzes for

    Returns:
        Sequence of quiz records, ordered by creation date (newest first)
    """
    return await get_quizzes_by_document(session, doc_id)


async def get_quiz_with_references(
    session: AsyncSession, quiz_id: int
) -> QuizWithReferenceResponse | None:
    """Get a quiz with its references by ID.

    Args:
        session: Database session
        quiz_id: Quiz ID to fetch

    Returns:
        Quiz with references or None if not found

    Note:
        Uses unique() to deduplicate rows from joinedload.
    """
    result = await session.execute(
        select(Quiz)
        .options(joinedload(Quiz.quiz_references))
        .where(Quiz.id == quiz_id)
    )
    quiz = result.scalars().unique().one_or_none()

    if not quiz:
        return None

    refs = (
        [ref.reference_text for ref in quiz.quiz_references]
        if quiz.quiz_references
        else []
    )

    return QuizWithReferenceResponse(
        id=quiz.id,
        doc_id=quiz.doc_id,
        source=quiz.source,
        question_json=quiz.question_json,
        references=refs,
        created_at=quiz.created_at,
    )
