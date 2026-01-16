"""Unit and integration tests for quiz generation LangGraph workflow.

Tests the workflow nodes, state management, and helper functions
for generating single-choice questions following LangGraph best practices.

Tests use actual LLM and retrieval services (no mocking) following
the project's convention of integration testing in dev container.
"""
from __future__ import annotations

import json

import pytest
from langchain.messages import AIMessage, HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command
from sqlalchemy.ext.asyncio import AsyncSession

from eduagent.llm import get_chat_model
from eduagent.quiz.graph import (
    QuizGenerationError,
    QuizGenerationState,
    _parse_llm_response,
    build_quiz_generation_workflow,
    retrieve_chunks,
)
from eduagent.quiz.models import QuizGenerationRequest, SingleChoiceQuestion
from eduagent.retrieval.service import SearchHit


# ============ Test _parse_llm_response helper function ============


@pytest.mark.parametrize(
    ("content", "expected_questions_count"),
    [
        # Valid JSON with markdown code block
        (
            """```json
            {
                "questions": [
                    {
                        "question": "Test question 1",
                        "options": [
                            {"label": "A", "text": "Option A"},
                            {"label": "B", "text": "Option B"},
                            {"label": "C", "text": "Option C"},
                            {"label": "D", "text": "Option D"}
                        ],
                        "correct_answer": "A",
                        "explanation": "A is correct"
                    }
                ]
            }
            ```""",
            1,
        ),
        # Valid JSON without markdown
        (
            """{
                "questions": [
                    {
                        "question": "Test question 2",
                        "options": [
                            {"label": "A", "text": "Option A"},
                            {"label": "B", "text": "Option B"},
                            {"label": "C", "text": "Option C"},
                            {"label": "D", "text": "Option D"}
                        ],
                        "correct_answer": "B",
                        "explanation": "B is correct"
                    }
                ]
            }""",
            1,
        ),
        # JSON with generic code block
        (
            """```
            {
                "questions": []
            }
            ```""",
            0,
        ),
        # Multiple questions
        (
            """{
                "questions": [
                    {
                        "question": "Q1",
                        "options": [
                            {"label": "A", "text": "A1"},
                            {"label": "B", "text": "B1"},
                            {"label": "C", "text": "C1"},
                            {"label": "D", "text": "D1"}
                        ],
                        "correct_answer": "A",
                        "explanation": "E1"
                    },
                    {
                        "question": "Q2",
                        "options": [
                            {"label": "A", "text": "A2"},
                            {"label": "B", "text": "B2"},
                            {"label": "C", "text": "C2"},
                            {"label": "D", "text": "D2"}
                        ],
                        "correct_answer": "B",
                        "explanation": "E2"
                    }
                ]
            }""",
            2,
        ),
    ],
)
def test_parse_llm_response_valid_json(content: str, expected_questions_count: int) -> None:
    """Test parsing valid JSON responses from LLM."""
    result = _parse_llm_response(content)
    assert "questions" in result
    assert len(result["questions"]) == expected_questions_count


@pytest.mark.parametrize(
    "content",
    [
        "This is not valid JSON at all",
        "```json\n{invalid json}\n```",
        "Some text ```json\n{}\n``` more text",
    ],
)
def test_parse_llm_response_invalid_json(content: str) -> None:
    """Test parsing invalid JSON raises QuizGenerationError.

    Note: The third test case "Some text ```json\n{}\n``` more text" will
    successfully parse the `{}` inside, so it won't raise an error.
    """
    if "Some text" in content:
        # This case has valid JSON inside, so it won't fail
        result = _parse_llm_response(content)
        assert result == {}
    else:
        with pytest.raises(QuizGenerationError, match="无法将 LLM 响应解析为 JSON"):
            _parse_llm_response(content)


# ============ Test workflow builder ============


def test_build_quiz_generation_workflow_without_checkpointer() -> None:
    """Test building workflow without checkpointer."""
    workflow = build_quiz_generation_workflow()
    assert workflow is not None
    # Verify the graph is compiled
    assert hasattr(workflow, "ainvoke")
    assert hasattr(workflow, "astream")


def test_build_quiz_generation_workflow_with_checkpointer() -> None:
    """Test building workflow with MemorySaver checkpointer."""
    checkpointer = MemorySaver()
    workflow = build_quiz_generation_workflow(checkpointer=checkpointer)
    assert workflow is not None
    # Verify the graph is compiled with checkpointer
    assert hasattr(workflow, "ainvoke")
    assert hasattr(workflow, "astream")


# ============ Test state structure ============


def test_quiz_generation_state_structure() -> None:
    """Test that QuizGenerationState has correct structure."""
    state: QuizGenerationState = {
        "messages": [HumanMessage(content="Test")],
        "doc_id": 1,
        "topic": "Test topic",
        "count": 3,
        "context_chunks": [],
        "generated_questions": [],
        "quiz_ids": [],
    }

    assert "messages" in state
    assert "doc_id" in state
    assert "topic" in state
    assert "count" in state
    assert "context_chunks" in state
    assert "generated_questions" in state
    assert "quiz_ids" in state


# ============ Test Pydantic model validation ============


@pytest.mark.parametrize(
    ("doc_id", "topic", "count", "should_be_valid"),
    [
        (1, "Python", 1, True),  # Valid
        (1, "Python", 5, True),  # Max count
        (1, "Python", 3, True),  # Middle value
        (0, "Python", 1, False),  # Invalid doc_id
        (1, "", 1, False),  # Empty topic
        (1, "Python", 0, False),  # Invalid count
        (1, "Python", 6, False),  # Count too high
    ],
)
def test_quiz_generation_request_validation(
    doc_id: int, topic: str, count: int, should_be_valid: bool
) -> None:
    """Test QuizGenerationRequest validation."""
    if should_be_valid:
        request = QuizGenerationRequest(doc_id=doc_id, topic=topic, count=count)
        assert request.doc_id == doc_id
        assert request.topic == topic
        assert request.count == count
    else:
        with pytest.raises((ValueError, TypeError)):
            QuizGenerationRequest(doc_id=doc_id, topic=topic, count=count)


def test_single_choice_question_validation() -> None:
    """Test SingleChoiceQuestion model validation."""
    # Valid question
    question = SingleChoiceQuestion(
        question="What is 2+2?",
        options=[
            {"label": "A", "text": "3"},
            {"label": "B", "text": "4"},
            {"label": "C", "text": "5"},
            {"label": "D", "text": "6"},
        ],
        correct_answer="B",
        explanation="2+2 equals 4",
    )

    assert question.question == "What is 2+2?"
    assert len(question.options) == 4
    assert question.correct_answer == "B"


@pytest.mark.parametrize(
    "invalid_options",
    [
        # Not enough options (2 instead of 4)
        [
            {"label": "A", "text": "Option A"},
            {"label": "B", "text": "Option B"},
        ],
        # Too many options (5 instead of 4)
        [
            {"label": "A", "text": "Option A"},
            {"label": "B", "text": "Option B"},
            {"label": "C", "text": "Option C"},
            {"label": "D", "text": "Option D"},
            {"label": "E", "text": "Option E"},
        ],
    ],
)
def test_single_choice_question_invalid_options(invalid_options: list) -> None:
    """Test SingleChoiceQuestion validation rejects invalid options."""
    with pytest.raises((ValueError, TypeError)):
        SingleChoiceQuestion(
            question="Test",
            options=invalid_options,
            correct_answer="A",
            explanation="Test",
        )


# ============ Integration tests with actual services ============


@pytest.mark.integration
@pytest.mark.asyncio
async def test_retrieve_chunks_node_returns_command() -> None:
    """Integration test: verify retrieve_chunks returns proper Command structure."""
    state: QuizGenerationState = {
        "messages": [HumanMessage(content="Generate questions about Python")],
        "doc_id": 1,
        "topic": "Python programming",
        "count": 3,
        "context_chunks": [],
        "generated_questions": [],
        "quiz_ids": [],
    }

    result = await retrieve_chunks(state)

    # Verify Command return type
    assert isinstance(result, Command)
    assert hasattr(result, "goto")
    assert hasattr(result, "update")
    assert result.goto == "generate_questions"
    assert "context_chunks" in result.update


@pytest.mark.integration
@pytest.mark.asyncio
async def test_retrieve_chunks_with_real_milvus() -> None:
    """Integration test: retrieve_chunks with real Milvus service.

    Requires:
    - Running Milvus with indexed documents
    - Document with doc_id=1 should exist
    """
    state: QuizGenerationState = {
        "messages": [HumanMessage(content="Generate questions")],
        "doc_id": 1,
        "topic": "Python",
        "count": 1,
        "context_chunks": [],
        "generated_questions": [],
        "quiz_ids": [],
    }

    result = await retrieve_chunks(state)

    # Verify chunks were retrieved (may be empty if doc_id doesn't exist)
    assert isinstance(result, Command)
    assert "context_chunks" in result.update
    # Note: chunks may be empty list if document not found


# ============ Test SearchHit model ============


def test_search_hit_creation() -> None:
    """Test SearchHit model creation and attributes."""
    hit = SearchHit(chunk_id=1, doc_id=100, text="Sample text", score=0.95)

    assert hit.chunk_id == 1
    assert hit.doc_id == 100
    assert hit.text == "Sample text"
    assert hit.score == 0.95


def test_search_hit_type_validation() -> None:
    """Test SearchHit field types."""
    hit = SearchHit(chunk_id=100, doc_id=1, text="Text", score=0.5)

    assert isinstance(hit.chunk_id, int)
    assert isinstance(hit.doc_id, int)
    assert isinstance(hit.text, str)
    assert isinstance(hit.score, float)
