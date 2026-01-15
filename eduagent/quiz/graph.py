"""LangGraph workflow for quiz generation.

This module implements a minimal LangGraph workflow for generating single-choice questions:
- Linear flow: retrieve_chunks → generate_questions → save_quizzes
- No branching or conditional logic (simplifies Milestone 5)
- Extensible: Easy to add nodes between existing ones

TODO: Enhancements for future milestones:
- Add async streaming for LLM calls (use .astream() and yield partial state)
- Add validation node between generate and save
- Add retry logic with conditional edges
- Use Command type instead of dict for complex control flow

Architecture:
    User Request → LangGraph State → Workflow Nodes → Final State → API Response
"""
from __future__ import annotations

import json
from typing_extensions import TypedDict

from langgraph.graph import StateGraph, END

from sqlalchemy.ext.asyncio import AsyncSession

from eduagent.llm.factory import get_chat_model
from eduagent.quiz.models import (
    QuizGenerationRequest,
    QuizGenerationResponse,
    SingleChoiceQuestion,
)
from eduagent.quiz.repository import create_quiz_with_references
from eduagent.retrieval.service import get_retrieval_service, RetrievalService, SearchHit


# ============ State Definition ============


class QuizGenerationState(TypedDict):
    """State for quiz generation workflow.

    Note: All fields are optional to allow partial updates from each node.
    """
    doc_id: int
    topic: str
    count: int
    context_chunks: list[SearchHit]  # Output of retrieve_chunks
    generated_questions: list[SingleChoiceQuestion]  # Output of generate_questions
    quiz_ids: list[int]  # Output of save_quizzes


# ============ Prompt Template ============


_PROMPT_TEMPLATE = """请根据以下教材内容，生成 {count} 道单选题。

教材内容：
{context_chunks}

主题：{topic}

要求：
1. 生成恰好 {count} 道有效的单选题
2. 每道题必须有 4 个选项（A、B、C、D）
3. 每道题只有一个正确答案
4. 为正确答案提供简要的解释
5. 题目应与提供的教材内容直接相关
6. 请严格按照以下 JSON 格式返回：
{{
  "questions": [
    {{
      "question": "题目内容",
      "options": [
        {{"label": "A", "text": "A选项内容"}},
        {{"label": "B", "text": "B选项内容"}},
        {{"label": "C", "text": "C选项内容"}},
        {{"label": "D", "text": "D选项内容"}}
      ],
      "correct_answer": "A",
      "explanation": "正确答案的简要解释"
    }}
  ]
}}

只返回 JSON，不要包含其他文字。"""


# ============ Graph Nodes ============


async def retrieve_chunks(state: QuizGenerationState) -> QuizGenerationState:
    """Node 1: Retrieve relevant document chunks via RAG.

    Args:
        state: Current workflow state

    Returns:
        Updated state with context_chunks populated

    Note:
        Uses BGE-M3 embeddings + Milvus hybrid search.
        Raises QuizGenerationError if no chunks found.
    """
    retrieval: RetrievalService = get_retrieval_service()
    hits = await retrieval.retrieve_relevant_chunks(
        query=state["topic"],
        doc_id=state["doc_id"],
        top_k=5,
        use_hybrid=True,
    )

    if not hits:
        raise QuizGenerationError(
            f"在文档 {state['doc_id']} 中未找到与主题 '{state['topic']}' 相关的内容"
        )

    return {"context_chunks": hits}


async def generate_questions(state: QuizGenerationState) -> QuizGenerationState:
    """Node 2: Generate questions using LLM with retrieved context.

    Args:
        state: Current workflow state with context_chunks populated

    Returns:
        Updated state with generated_questions populated

    Note:
        Constructs Chinese prompt with context chunks.
        Parses JSON response from LLM.
        Validates Pydantic models.
    """
    llm = get_chat_model()

    # Format context chunks for prompt
    context_chunks = "\n\n".join(
        [f"[段落 {i}]\n{hit.text}" for i, hit in enumerate(state["context_chunks"], 1)]
    )

    # Construct prompt
    prompt = _PROMPT_TEMPLATE.format(
        count=state["count"],
        context_chunks=context_chunks,
        topic=state["topic"],
    )

    # Generate questions
    llm_response = await llm.ainvoke(prompt)

    # Parse JSON response
    questions_data = _parse_llm_response(llm_response.content)

    # Validate with Pydantic
    questions = [
        SingleChoiceQuestion(**q_data) for q_data in questions_data.get("questions", [])
    ]

    return {"generated_questions": questions}


async def save_quizzes(
    state: QuizGenerationState, session: AsyncSession
) -> QuizGenerationState:
    """Node 3: Save generated questions with references to database.

    Args:
        state: Current workflow state with generated_questions populated
        session: Database session for saving (commit handled by transactional dependency)

    Returns:
        Updated state with quiz_ids populated

    Note:
        Saves questions as JSON to quiz table.
        Creates quiz_reference records for each question.
    """
    quiz_ids: list[int] = []
    reference_texts = [
        (hit.text, i) for i, hit in enumerate(state["context_chunks"])
    ]

    for question in state["generated_questions"]:
        quiz_json = question.model_dump_json()
        quiz = await create_quiz_with_references(
            session,
            doc_id=state["doc_id"],
            source="generated",
            question_json=quiz_json,
            reference_texts=reference_texts,
        )
        quiz_ids.append(quiz.id)

    return {"quiz_ids": quiz_ids}


# ============ Helper Functions ============


def _parse_llm_response(content: str) -> dict:
    """Parse LLM response, extracting JSON from markdown code blocks.

    Args:
        content: Raw LLM response text

    Returns:
        Parsed JSON as dictionary

    Raises:
        QuizGenerationError: If JSON parsing fails
    """
    if "```json" in content:
        start = content.find("```json") + 7
        end = content.find("```", start)
        json_str = content[start:end].strip()
    elif "```" in content:
        start = content.find("```") + 3
        end = content.find("```", start)
        json_str = content[start:end].strip()
    else:
        json_str = content.strip()

    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        raise QuizGenerationError(f"无法将 LLM 响应解析为 JSON：{e}")


class QuizGenerationError(Exception):
    """Error during quiz generation workflow."""


# ============ Workflow Builder ============


def build_quiz_generation_workflow() -> StateGraph:
    """Build the quiz generation LangGraph workflow.

    Returns:
        Compiled LangGraph workflow

    Note:
        Linear workflow: retrieve_chunks → generate_questions → save_quizzes
        No branching or conditional logic for Milestone 5.
        Extensible: Can add nodes between existing ones in future milestones.
    """
    workflow = StateGraph(QuizGenerationState)

    # Add nodes
    workflow.add_node("retrieve_chunks", retrieve_chunks)
    workflow.add_node("generate_questions", generate_questions)
    workflow.add_node("save_quizzes", save_quizzes)

    # Add linear edges
    workflow.add_edge("retrieve_chunks", "generate_questions")
    workflow.add_edge("generate_questions", "save_quizzes")

    # Set entry and finish points
    workflow.set_entry_point("retrieve_chunks")
    workflow.set_finish_point("save_quizzes")

    return workflow.compile()


# ============ Runner ============


async def run_quiz_generation_workflow(
    request: QuizGenerationRequest, session: AsyncSession
) -> QuizGenerationResponse:
    """Run the quiz generation workflow.

    Args:
        request: Quiz generation request with doc_id, topic, count
        session: Database session (commit handled by transactional dependency)

    Returns:
        QuizGenerationResponse with generated questions and saved quiz IDs

    Raises:
        QuizGenerationError: If workflow fails at any node

    Note:
        Creates initial state and runs compiled LangGraph workflow.
    """
    # Create initial state
    initial_state: QuizGenerationState = {
        "doc_id": request.doc_id,
        "topic": request.topic,
        "count": request.count,
    }

    # Build and run workflow
    workflow = build_quiz_generation_workflow()
    final_state = await workflow.ainvoke(initial_state)

    return QuizGenerationResponse(
        doc_id=final_state["doc_id"],
        questions=final_state["generated_questions"],
        quiz_ids=final_state["quiz_ids"],
    )
