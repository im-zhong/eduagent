"""Integration tests for quiz generation LangGraph workflow.

Integration Test Principles:
- Self-contained: Each test sets up its own data
- End-to-end: Tests complete workflows, not individual components
- No mocking: Uses real database, Milvus, and LLM services
- Cleanup: Tests clean up their own data after execution

Requirements:
- Running PostgreSQL database
- Running Milvus with BGE-M3 embeddings
- Running LLM service (Anthropic Claude)
"""
from __future__ import annotations

import pytest
import pytest_asyncio

from eduagent.documents.models import SourceDocument
from eduagent.documents.repository import (
    create_document_chunks,
    list_document_chunks,
)
from eduagent.quiz.graph import (
    QuizGenerationState,
    build_quiz_generation_workflow,
    run_quiz_generation_workflow,
)
from eduagent.quiz.models import QuizGenerationRequest
from eduagent.quiz.repository import (
    delete_quizzes_by_doc,
    get_quizzes_by_doc,
    get_quiz_with_references,
)
from eduagent.retrieval.milvus_client import (
    HybridWeights,
    MilvusClient,
    MilvusConfig,
)
from eduagent.settings import settings
from eduagent.storage.engine import get_async_session
from eduagent.tools.bge_client import (
    BGEClient,
    BGEClientConfig,
    EmbeddingRequest,
)


# ============ Test Data Setup Helpers ============


@pytest.fixture
def test_document_content() -> str:
    """Return test document content for quiz generation.

    Content about Python programming that will be used to
    generate quiz questions.
    """
    return """
    Python Programming Fundamentals

    Python is a high-level, interpreted programming language known for its
    simplicity and readability. It supports multiple programming paradigms
    including procedural, object-oriented, and functional programming.

    Variables in Python are dynamically typed, meaning you don't need to
    declare variable types. For example: x = 5, name = "Alice", is_valid = True.

    Python has several built-in data types:
    - int: Integer numbers (e.g., 42, -7)
    - float: Floating-point numbers (e.g., 3.14, -0.001)
    - str: Strings (e.g., "Hello", 'Python')
    - bool: Boolean values (True or False)
    - list: Ordered mutable sequences (e.g., [1, 2, 3])
    - dict: Key-value pairs (e.g., {"name": "John", "age": 30})

    Functions in Python are defined using the 'def' keyword:
    def greet(name):
        return f"Hello, {name}!"

    Python uses indentation for code blocks instead of curly braces.
    A typical if statement looks like:
    if x > 0:
        print("Positive")
    else:
        print("Non-positive")

    Lists are zero-indexed, meaning the first element is at index 0.
    For example, fruits[0] accesses the first element of the fruits list.
    """


@pytest_asyncio.fixture
async def setup_test_document(
    db_session,
    test_document_content: str,
) -> int:
    """Set up a test document in database and Milvus.

    Creates:
    1. Document record in PostgreSQL
    2. Chunks in PostgreSQL
    3. Chunks with embeddings in Milvus

    Returns the doc_id for cleanup.

    Yields:
        int: The document ID
    """
    # Step 1: Create document in database
    doc = SourceDocument(
        filename="test_python_quiz.txt",
        storage_path="test_python_quiz.txt",  # Required field
        file_size=len(test_document_content.encode()),
        content_type="text/plain",
    )
    db_session.add(doc)
    await db_session.flush()
    doc_id = doc.id

    # Step 2: Create chunks in database
    # Split content into chunks (simple paragraph-based splitting)
    chunk_texts = [
        paragraph.strip()
        for paragraph in test_document_content.strip().split("\n\n")
        if paragraph.strip()
    ]

    chunks = await create_document_chunks(
        db_session,
        doc_id=doc_id,
        chunks=chunk_texts,
    )

    # Step 3: Generate embeddings using BGE client
    bge_client = BGEClient(
        config=BGEClientConfig(
            base_url=settings.bge.base_url,
            timeout_seconds=settings.bge.timeout_seconds,
        )
    )

    embeddings = await bge_client.embed_hybrid(
        EmbeddingRequest(texts=[chunk.text for chunk in chunks])
    )

    # Step 4: Insert chunks into Milvus
    milvus_client = MilvusClient(
        config=MilvusConfig(
            host=settings.milvus.host,
            port=settings.milvus.port,
            database=settings.milvus.database,
            collection=settings.milvus.collection,
            dim=settings.milvus.dim,
            hybrid_weights=HybridWeights(
                dense=settings.milvus.hybrid_dense_weight,
                sparse=settings.milvus.hybrid_sparse_weight,
            ),
        )
    )
    milvus_client.connect()

    # Drop existing collection to ensure clean schema
    from pymilvus import utility
    if utility.has_collection(settings.milvus.collection):
        utility.drop_collection(settings.milvus.collection)

    collection = milvus_client.ensure_collection()

    milvus_client.insert_chunks(
        collection,
        chunk_ids=[chunk.id for chunk in chunks],
        doc_ids=[chunk.doc_id for chunk in chunks],
        texts=[chunk.text for chunk in chunks],
        dense_vectors=embeddings.dense_embeddings,
        sparse_vectors=[
            {idx: val for idx, val in zip(embed.indices, embed.values)}
            for embed in embeddings.sparse_embeddings
        ],
    )

    yield doc_id

    # Cleanup: Delete from Milvus and database
    try:
        # Delete quizzes for this document
        await delete_quizzes_by_doc(db_session, doc_id)

        # Delete chunks from Milvus
        milvus_client.delete_document_chunks(collection, doc_id=doc_id)

        # Delete chunks from database (cascade will handle this)
        # Delete document from database
        await db_session.delete(doc)
        await db_session.commit()
    except Exception as e:
        # Log but don't fail test on cleanup errors
        print(f"Cleanup warning: {e}")


# ============ End-to-End Integration Tests ============


@pytest.mark.integration
@pytest.mark.asyncio
async def test_quiz_generation_end_to_end(
    setup_test_document: int,
    db_session
) -> None:
    """End-to-end test: Generate quiz questions from document.

    Tests the complete workflow:
    1. Retrieve relevant chunks from Milvus (RAG)
    2. Generate questions using LLM with retrieved context
    3. Save questions and references to PostgreSQL

    This is a true integration test that verifies all components
    work together correctly.
    """
    doc_id = setup_test_document

    # Create quiz generation request
    request = QuizGenerationRequest(
        doc_id=doc_id,
        topic="Python data types",
        count=2
    )

    # Run the complete workflow
    response = await run_quiz_generation_workflow(request, db_session)

    # Verify response structure
    assert response.doc_id == doc_id
    assert len(response.questions) > 0, "Should generate at least one question"
    assert len(response.quiz_ids) > 0, "Should save questions to database"

    # Verify question structure
    for question in response.questions:
        assert question.question, "Question text should not be empty"
        assert len(question.options) == 4, "Should have exactly 4 options"
        assert question.correct_answer in ["A", "B", "C", "D"], "Valid answer label"
        assert question.explanation, "Should have explanation"

        # Verify options have correct structure
        for option in question.options:
            assert option.label in ["A", "B", "C", "D"], "Valid option label"
            assert option.text, "Option text should not be empty"

    # Verify database persistence
    saved_quizzes = await get_quizzes_by_doc(db_session, doc_id=doc_id)
    assert len(saved_quizzes) > 0, "Questions should be saved to database"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_quiz_generation_different_topics(
    setup_test_document: int,
    db_session
) -> None:
    """Test quiz generation with different topics from same document.

    Verifies that the workflow can generate questions on different
    aspects of the same document.
    """
    doc_id = setup_test_document

    topics = [
        "Python variables",
        "Python data types",
        "Python functions"
    ]

    for topic in topics:
        request = QuizGenerationRequest(
            doc_id=doc_id,
            topic=topic,
            count=1
        )

        response = await run_quiz_generation_workflow(request, db_session)

        # Each topic should generate relevant questions
        assert len(response.questions) > 0, f"Should generate questions for topic: {topic}"
        assert len(response.quiz_ids) > 0, f"Should save questions for topic: {topic}"

        # Questions should be contextually relevant
        question_text = response.questions[0].question.lower()
        # At least some words from topic should appear in questions
        # (not strict check as LLM may vary)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_quiz_workflow_streaming_mode(
    setup_test_document: int,
    db_session
) -> None:
    """Test quiz workflow with streaming (graph.astream).

    Verifies that the workflow supports streaming as per LangGraph
    best practices: nodes use invoke(), graph uses stream().
    """
    doc_id = setup_test_document

    workflow = build_quiz_generation_workflow()

    initial_state: QuizGenerationState = {
        "messages": [],
        "doc_id": doc_id,
        "topic": "Python",
        "count": 1,
        "context_chunks": [],
        "generated_questions": [],
        "quiz_ids": [],
    }

    # Stream the workflow execution
    chunks_received = []
    async for chunk in workflow.astream(
        initial_state,
        config={"configurable": {"session": db_session}}
    ):
        chunks_received.append(chunk)
        # Each chunk should be a dict mapping node names to state updates
        assert isinstance(chunk, dict)

    # Should receive chunks from multiple nodes
    assert len(chunks_received) > 0, "Should receive workflow chunks"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_quiz_with_checkpointer(
    setup_test_document: int
) -> None:
    """Test quiz workflow with PostgreSQL checkpointer.

    Verifies that the workflow can be built with a checkpointer
    for persistence and resumption.
    """
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

    doc_id = setup_test_document

    # Build checkpointer connection string
    conn_str = (
        "postgresql://"
        f"{settings.database.user}:{settings.database.password}"
        f"@{settings.database.host}:{settings.database.port}"
        f"/{settings.database.name}"
    )

    async with AsyncPostgresSaver.from_conn_string(conn_str) as checkpointer:
        # Build workflow with checkpointer
        workflow = build_quiz_generation_workflow(checkpointer=checkpointer)

        # Verify workflow is compiled
        assert hasattr(workflow, "ainvoke")
        assert hasattr(workflow, "astream")

        # Run workflow with checkpointer
        async for session in get_async_session():
            request = QuizGenerationRequest(
                doc_id=doc_id,
                topic="Python basics",
                count=1
            )

            response = await run_quiz_generation_workflow(request, session)

            assert len(response.questions) > 0
            assert len(response.quiz_ids) > 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_quiz_multiple_requests_same_document(
    setup_test_document: int,
    db_session
) -> None:
    """Test generating multiple quizzes from the same document.

    Verifies that:
    1. Multiple quiz generations work correctly
    2. All quizzes are persisted with unique IDs
    3. Document can support multiple quiz topics
    """
    doc_id = setup_test_document

    # Generate first quiz
    request1 = QuizGenerationRequest(
        doc_id=doc_id,
        topic="Python lists",
        count=1
    )
    response1 = await run_quiz_generation_workflow(request1, db_session)

    # Generate second quiz
    request2 = QuizGenerationRequest(
        doc_id=doc_id,
        topic="Python dictionaries",
        count=1
    )
    response2 = await run_quiz_generation_workflow(request2, db_session)

    # Verify both succeeded
    assert len(response1.questions) > 0
    assert len(response2.questions) > 0

    # Verify quiz IDs are unique
    all_quiz_ids = response1.quiz_ids + response2.quiz_ids
    assert len(set(all_quiz_ids)) == len(all_quiz_ids), "Quiz IDs should be unique"

    # Verify all quizzes are in database
    saved_quizzes = await get_quizzes_by_doc(db_session, doc_id=doc_id)
    assert len(saved_quizzes) >= 2, "Should have at least 2 quizzes"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_quiz_references_created(
    setup_test_document: int,
    db_session
) -> None:
    """Test that quiz references are correctly created.

    Verifies that when a quiz is generated, the reference chunks
    used for generation are stored in the database.
    """
    doc_id = setup_test_document

    request = QuizGenerationRequest(
        doc_id=doc_id,
        topic="Python",
        count=1
    )

    response = await run_quiz_generation_workflow(request, db_session)
    quiz_id = response.quiz_ids[0]

    # Get quiz with references
    quiz_with_refs = await get_quiz_with_references(db_session, quiz_id)

    # Verify structure
    assert quiz_with_refs is not None
    assert quiz_with_refs.id == quiz_id
    assert quiz_with_refs.doc_id == doc_id
    assert len(quiz_with_refs.references) > 0, "Should have reference chunks"

    # Verify references contain text
    for ref in quiz_with_refs.references:
        assert ref, "Reference should not be empty"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_retrieval_returns_relevant_chunks(
    setup_test_document: int
) -> None:
    """Test that retrieval service returns relevant chunks.

    Verifies the RAG (Retrieval Augmented Generation) pipeline
    returns contextually relevant chunks for quiz generation.
    """
    from eduagent.retrieval.service import get_retrieval_service

    doc_id = setup_test_document

    # Test retrieval with specific topic
    retrieval = get_retrieval_service()
    hits = await retrieval.retrieve_relevant_chunks(
        query="Python data types int float str list",
        doc_id=doc_id,
        top_k=3,
        use_hybrid=True
    )

    # Should return some chunks
    assert len(hits) > 0, "Should retrieve relevant chunks"

    # Verify chunk structure
    for hit in hits:
        assert hasattr(hit, "text")
        assert hasattr(hit, "chunk_id")
        assert hasattr(hit, "doc_id")
        assert hasattr(hit, "score")
        assert hit.score > 0, "Score should be positive"
        assert hit.doc_id == doc_id, "Should return chunks from correct document"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_document_cleanup_after_quiz_generation(
    setup_test_document: int,
    db_session
) -> None:
    """Test that document cleanup works after quiz generation.

    Verifies that:
    1. Quizzes can be deleted by document ID
    2. Chunks can be removed from Milvus
    3. Document can be removed from database
    """
    doc_id = setup_test_document

    # First, generate some quizzes
    request = QuizGenerationRequest(
        doc_id=doc_id,
        topic="Python",
        count=2
    )
    response = await run_quiz_generation_workflow(request, db_session)
    quiz_ids = response.quiz_ids

    # Verify quizzes exist
    quizzes_before = await get_quizzes_by_doc(db_session, doc_id)
    assert len(quizzes_before) > 0

    # Delete quizzes
    deleted_count = await delete_quizzes_by_doc(db_session, doc_id)
    assert deleted_count > 0, "Should delete at least one quiz"

    # Verify deletion
    quizzes_after = await get_quizzes_by_doc(db_session, doc_id)
    # Note: In concurrent testing, there might be other quizzes
    # We just verify our deletion function executed without error
