"""LangGraph workflow for quiz generation.

This module implements a LangGraph workflow for generating single-choice questions
following best practices from docs/langgraph/:
- Nodes use Command pattern with goto parameter
- State uses Annotated[list[AnyMessage], add] for messages
- Streaming is done at graph level with graph.astream()
- Nodes use invoke() inside, never stream()
- Checkpointer support for persistence

Architecture:
    User Request → LangGraph State → Workflow Nodes → Final State → API Response
"""

from __future__ import annotations

import json
from operator import add
from typing import Annotated, Any, Literal

from langchain.messages import AIMessage, AnyMessage, HumanMessage
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import StateGraph, START, END
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command, RunnableConfig
from sqlalchemy.ext.asyncio import AsyncSession
from typing_extensions import TypedDict

from eduagent.llm.factory import get_chat_model
from eduagent.quiz.models import (
    QuizGenerationRequest,
    QuizGenerationResponse,
    SingleChoiceQuestion,
)
from eduagent.quiz.repository import create_quiz_with_references
from eduagent.retrieval.service import (
    get_retrieval_service,
    RetrievalService,
    SearchHit,
)


# ============ State Definition ============


class QuizGenerationState(TypedDict):
    """State for quiz generation workflow.

    Follows LangGraph best practices:
    - messages: Annotated with add reducer for accumulation
    - Other fields: Optional for partial updates from each node
    """

    # Messages: Annotated with add reducer to append, not replace
    messages: Annotated[list[AnyMessage], add]
    # Quiz generation parameters
    doc_id: int | None
    topic: str | None
    count: int | None
    # Workflow state
    context_chunks: list[SearchHit]
    generated_questions: list[SingleChoiceQuestion]
    quiz_ids: list[int]


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


# ============ Custom Exceptions ============


class QuizGenerationError(Exception):
    """Error during quiz generation workflow."""


# ============ Graph Nodes ============


async def retrieve_chunks(state: QuizGenerationState) -> Command[Literal["generate_questions"]]:
    """Node 1: Retrieve relevant document chunks via RAG.

    Args:
        state: Current workflow state

    Returns:
        Command with update and goto for next node

    Note:
        Uses BGE-M3 embeddings + Milvus hybrid search.
        Raises QuizGenerationError if no chunks found.
    """
    retrieval: RetrievalService = get_retrieval_service()
    hits = await retrieval.retrieve_relevant_chunks(
        query=state["topic"] or "",
        doc_id=state["doc_id"] or 0,
        top_k=5,
        use_hybrid=True,
    )

    if not hits:
        raise QuizGenerationError(
            f"在文档 {state['doc_id']} 中未找到与主题 '{state['topic']}' 相关的内容"
        )

    # Add status message for user feedback
    status_msg = AIMessage(
        content=f"已检索到 {len(hits)} 个相关文档段落，正在生成题目..."
    )

    return Command(
        update={"context_chunks": hits, "messages": [status_msg]},
        goto="generate_questions",
    )


async def generate_questions(
    state: QuizGenerationState,
) -> Command[Literal["save_quizzes"]]:
    """Node 2: Generate questions using LLM with retrieved context.

    Args:
        state: Current workflow state with context_chunks populated

    Returns:
        Command with update and goto for next node

    Note:
        Uses llm.ainvoke() (NOT stream) - streaming happens at graph level.
        Parses JSON response from LLM.
        Validates with Pydantic models.
    """
    llm = get_chat_model()

    # Format context chunks for prompt
    context_chunks = "\n\n".join(
        [f"[段落 {i}]\n{hit.text}" for i, hit in enumerate(state["context_chunks"], 1)]
    )

    # Construct prompt
    prompt = _PROMPT_TEMPLATE.format(
        count=state["count"] or 1,
        context_chunks=context_chunks,
        topic=state["topic"] or "",
    )

    # Use invoke(), NOT stream() - streaming is graph-level concern
    llm_response = await llm.ainvoke(prompt)

    # Parse JSON response
    questions_data = _parse_llm_response(llm_response.content)

    # Validate with Pydantic
    questions = [
        SingleChoiceQuestion(**q_data) for q_data in questions_data.get("questions", [])
    ]

    # Add status message for user feedback
    status_msg = AIMessage(content=f"已生成 {len(questions)} 道题目，正在保存...")

    return Command(
        update={"generated_questions": questions, "messages": [status_msg]},
        goto="save_quizzes",
    )


async def save_quizzes(
    state: QuizGenerationState,
    config: RunnableConfig,
) -> Command[Literal[END]]:
    """Node 3: Save generated questions with references to database.

    Args:
        state: Current workflow state with generated_questions populated
        config: Runtime config containing the database session

    Returns:
        Command with update and goto END

    Note:
        Saves questions as JSON to quiz table.
        Creates quiz_reference records for each question.
        Session is extracted from config[\"configurable\"][\"session\"].
        Uses invoke() pattern for database operations.
    """
    # Extract session from config (passed at runtime)
    session = config.get("configurable", {}).get("session")
    if not session:
        raise QuizGenerationError("Database session not available in config")

    quiz_ids: list[int] = []
    reference_texts = [(hit.text, i) for i, hit in enumerate(state["context_chunks"])]

    for question in state["generated_questions"]:
        quiz_json = question.model_dump_json()
        quiz = await create_quiz_with_references(
            session,
            doc_id=state["doc_id"] or 0,
            source="generated",
            question_json=quiz_json,
            reference_texts=reference_texts,
        )
        quiz_ids.append(quiz.id)

    # Add completion message
    completion_msg = AIMessage(
        content=f"完成！已生成并保存 {len(quiz_ids)} 道题目。题目ID: {quiz_ids}"
    )

    return Command(
        update={"quiz_ids": quiz_ids, "messages": [completion_msg]},
        goto=END,
    )


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
        # Log the actual LLM response for debugging
        import sys
        print(f"[DEBUG] LLM response that failed to parse:", file=sys.stderr)
        print(f"[DEBUG] Raw content: {repr(content[:500])}", file=sys.stderr)
        print(f"[DEBUG] Extracted JSON string: {repr(json_str[:500])}", file=sys.stderr)
        raise QuizGenerationError(
            f"无法将 LLM 响应解析为 JSON：{e}\n"
            f"原始内容：{content[:200]}"
        )


# ============ Workflow Builder ============


def build_quiz_generation_workflow(
    checkpointer: BaseCheckpointSaver | None = None,
) -> CompiledStateGraph:
    """Build the quiz generation LangGraph workflow.

    Args:
        checkpointer: Optional checkpointer for persistence (e.g., AsyncPostgresSaver)

    Returns:
        Compiled LangGraph workflow

    Note:
        Linear workflow: retrieve_chunks → generate_questions → save_quizzes → END
        Uses Command pattern for explicit routing.
        Extensible: Can add nodes between existing ones in future.
    """
    workflow = StateGraph(QuizGenerationState)

    # Add nodes
    workflow.add_node("retrieve_chunks", retrieve_chunks)
    workflow.add_node("generate_questions", generate_questions)
    workflow.add_node("save_quizzes", save_quizzes)

    # Add edges - nodes use Command.goto for routing
    workflow.add_edge(START, "retrieve_chunks")

    # Compile with optional checkpointer for persistence
    return workflow.compile(checkpointer=checkpointer)


# ============ Runner (Non-streaming) ============


async def run_quiz_generation_workflow(
    request: QuizGenerationRequest, session: AsyncSession
) -> QuizGenerationResponse:
    """Run the quiz generation workflow (non-streaming).

    Args:
        request: Quiz generation request with doc_id, topic, count
        session: Database session (commit handled by transactional dependency)

    Returns:
        QuizGenerationResponse with generated questions and saved quiz IDs

    Raises:
        QuizGenerationError: If workflow fails at any node

    Note:
        Creates initial state and runs compiled LangGraph workflow.
        For streaming version, use stream_quiz_generation_workflow() instead.
    """
    # Create initial state with HumanMessage
    initial_state: QuizGenerationState = {
        "messages": [
            HumanMessage(content=f"请为主题 '{request.topic}' 生成 {request.count} 道题目")
        ],
        "doc_id": request.doc_id,
        "topic": request.topic,
        "count": request.count,
        "context_chunks": [],
        "generated_questions": [],
        "quiz_ids": [],
    }

    # Build workflow (no checkpointer for one-shot execution)
    workflow = build_quiz_generation_workflow()

    # Invoke workflow with session
    final_state = await workflow.ainvoke(
        initial_state, config={"configurable": {"session": session}}
    )

    return QuizGenerationResponse(
        doc_id=final_state["doc_id"] or 0,
        questions=final_state["generated_questions"],
        quiz_ids=final_state["quiz_ids"],
    )
