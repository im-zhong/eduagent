"""Unified chat graph with intent-based agent routing.

This module implements a LangGraph workflow for unified chat that routes to
specialized agents based on user intent. Following best practices from
docs/langgraph/:
- Nodes use Command pattern with goto parameter
- State extends MessagesState from eduagent.agents.chat
- Streaming is done at graph level with graph.astream()
- Runtime dependencies (like session) passed via config
- Checkpointer support for persistence

Architecture:
    START → intent_router → {chat_agent, quiz_agent} → END
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from langchain.messages import AIMessage, AnyMessage, HumanMessage
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import StateGraph, START, END
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command
from sqlalchemy.ext.asyncio import AsyncSession
from typing_extensions import TypedDict

from eduagent.agents.chat import MessagesState
from eduagent.quiz.models import QuizGenerationRequest
from eduagent.quiz.graph import run_quiz_generation_workflow


# ============ Types ============


class Intent(str, Enum):
    """Supported agent intents for unified chat."""

    CHAT = "chat"
    QUIZ = "quiz"


# ============ State Definition ============


class UnifiedChatState(MessagesState):
    """Unified chat state extending MessagesState.

    Inherits messages with Annotated[list[AnyMessage], add] reducer.
    Adds intent and workspace for multi-agent coordination.
    """

    intent: Intent | None
    workspace: dict[str, Any]


# ============ Intent Router (L0 - Keyword Only) ============


def detect_intent(message: str) -> Intent:
    """Detect user intent from message content (L0 - keyword only).

    Args:
        message: User input message

    Returns:
        Detected intent (CHAT or QUIZ)

    Note:
        L1 (LLM) and L2 (agent self-correction) can be added later.
        Current implementation uses simple keyword matching.
    """
    keywords_quiz = ["出题", "生成题目", "quiz", "question"]
    keywords_chat = ["你好", "hello", "help", "帮助"]

    message_lower = message.lower()

    # Check quiz keywords first
    if any(kw in message_lower for kw in keywords_quiz):
        return Intent.QUIZ

    # Default to chat
    return Intent.CHAT


# ============ Graph Nodes ============


async def intent_router_node(
    state: UnifiedChatState,
) -> Command[Literal["chat_agent", "quiz_agent"]]:
    """Detect intent from the latest user message and route accordingly.

    Args:
        state: Current chat state

    Returns:
        Command with detected intent and goto to appropriate agent node

    Note:
        Uses keyword-based intent detection (L0).
        Routes directly to quiz_agent or chat_agent using Command.goto.
    """
    messages = state.get("messages", [])
    if not messages:
        return Command(
            update={"intent": Intent.CHAT, "workspace": {"type": "chat"}},
            goto="chat_agent",
        )

    last_msg = messages[-1]
    if isinstance(last_msg, HumanMessage):
        intent = detect_intent(last_msg.content)
        return Command(
            update={"intent": intent, "workspace": {"type": intent.value}},
            goto="quiz_agent" if intent == Intent.QUIZ else "chat_agent",
        )

    return Command(
        update={"intent": Intent.CHAT, "workspace": {"type": "chat"}},
        goto="chat_agent",
    )


async def chat_agent_node(
    state: UnifiedChatState,
    config: dict[str, Any],
) -> Command[Literal[END]]:
    """Handle conversational queries using the existing chat agent.

    Args:
        state: Current chat state with messages
        config: Runtime config containing the chat_agent

    Returns:
        Command with AI response and goto END

    Note:
        Extracts chat_agent from config["configurable"]["chat_agent"].
        This pattern allows the agent to be built once at app startup
        and passed at runtime via config.
    """
    # Extract chat agent from config (passed at runtime)
    chat_agent = config.get("configurable", {}).get("chat_agent")
    if not chat_agent:
        return Command(
            update={"messages": [AIMessage(content="Chat agent not available")]},
            goto=END,
        )

    messages = state.get("messages", [])
    if not messages:
        return Command(goto=END)

    last_msg = messages[-1]
    if not isinstance(last_msg, HumanMessage):
        return Command(goto=END)

    # Invoke the chat agent with the latest message
    result = await chat_agent.ainvoke({"messages": [last_msg]})

    # Extract AI messages from result
    ai_messages = [
        msg for msg in result.get("messages", []) if isinstance(msg, AIMessage)
    ]

    return Command(
        update={"messages": ai_messages},
        goto=END,
    )


async def quiz_agent_node(
    state: UnifiedChatState,
    config: dict[str, Any],
) -> Command[Literal[END]]:
    """Handle quiz generation requests.

    Args:
        state: Current chat state with messages
        config: Runtime config containing the session

    Returns:
        Command with quiz result and goto END

    Note:
        Extracts session from config["configurable"]["session"].
        This pattern allows the short-lived session to be passed at runtime.
        Parses topic from message and calls run_quiz_generation_workflow().
    """
    # Extract session from config (passed at runtime)
    session = config.get("configurable", {}).get("session")
    if not session:
        return Command(
            update={
                "messages": [AIMessage(content="Quiz agent not available (no database session)")],
                "workspace": {"type": "error", "message": "No database session"},
            },
            goto=END,
        )

    messages = state.get("messages", [])
    if not messages:
        return Command(goto=END)

    last_msg = messages[-1]
    if not isinstance(last_msg, HumanMessage):
        return Command(goto=END)

    text = last_msg.content
    # Extract topic from message
    topic = (
        text.replace("出题", "")
        .replace("生成题目", "")
        .replace("quiz", "")
        .strip()
    ) or "Python编程基础"

    if not topic or len(topic) < 2:
        topic = "Python编程基础"

    request = QuizGenerationRequest(doc_id=1, topic=topic, count=3)

    try:
        response = await run_quiz_generation_workflow(request, session)

        workspace = {
            "type": "quiz_result",
            "question_count": len(response.questions),
            "quiz_ids": response.quiz_ids,
        }

        result_msg = AIMessage(
            content=f"已生成 {len(response.questions)} 道题目，主题：{topic}\n"
            f"题目已保存到数据库，ID: {response.quiz_ids}"
        )

        return Command(
            update={"messages": [result_msg], "workspace": workspace},
            goto=END,
        )
    except Exception as e:
        error_msg = AIMessage(content=f"出题失败：{str(e)}")
        return Command(
            update={
                "messages": [error_msg],
                "workspace": {"type": "error", "message": str(e)},
            },
            goto=END,
        )


# ============ Graph Builder ============


def build_unified_chat_graph(
    checkpointer: BaseCheckpointSaver | None = None,
) -> CompiledStateGraph:
    """Build unified chat graph with intent-based routing.

    Args:
        checkpointer: Optional checkpointer for persistence (e.g., AsyncPostgresSaver)

    Returns:
        Compiled LangGraph workflow

    Graph Structure:
        START → intent_router → {chat_agent, quiz_agent} → END

    Note:
        Uses Command pattern for explicit routing from intent_router.
        Each agent node returns Command with goto=END.
        Runtime dependencies (chat_agent, session) passed via config at invoke time.
        Graph is built once at app startup, not per request.
    """
    workflow = StateGraph(UnifiedChatState)

    # Add nodes - note: nodes receive state and config
    workflow.add_node("intent_router", intent_router_node)
    workflow.add_node("chat_agent", chat_agent_node)
    workflow.add_node("quiz_agent", quiz_agent_node)

    # Add edges - nodes use Command.goto for routing
    workflow.add_edge(START, "intent_router")

    # Compile with optional checkpointer
    return workflow.compile(checkpointer=checkpointer)
