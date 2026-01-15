"""Quick prototype for unified chat with multi-agent routing.

This prototype demonstrates:
- Intent-based routing (keyword L0 only)
- Chat agent (existing) and Quiz agent (existing workflow)
- Simple workspace state for artifact tracking
- Unified state extending MessagesState

Architecture: Linear router to agent nodes for quick prototyping.
"""
from __future__ import annotations

from enum import Enum
from typing import Any

from langchain.messages import HumanMessage, AIMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.state import CompiledStateGraph

from eduagent.agents.chat import get_agent, MessagesState
from eduagent.llm import get_chat_model
from eduagent.quiz.graph import run_quiz_generation_workflow
from eduagent.quiz.models import QuizGenerationRequest
from sqlalchemy.ext.asyncio import AsyncSession


# ============ Types ============


class Intent(str, Enum):
    """Supported agent intents for quick prototype."""

    CHAT = "chat"
    QUIZ = "quiz"


# Extend MessagesState for unified chat
class UnifiedChatState(MessagesState):
    """Unified chat state extending MessagesState.

    Adds intent and workspace for multi-agent coordination.
    """

    intent: Intent | None
    workspace: dict[str, Any]


# ============ Intent Router (L0 - Keyword Only) ============


def detect_intent(message: str) -> Intent:
    """Simple keyword-based intent detection (L0).

    Args:
        message: User input message

    Returns:
        Detected intent (CHAT or QUIZ)

    Note:
        L1 (LLM) and L2 (agent self-correction) not implemented yet.
        Quick prototype uses only keywords.
    """
    keywords_quiz = ["出题", "生成题目", "quiz", "question"]
    keywords_chat = ["你好", "hello", "help", "帮助"]

    message_lower = message.lower()

    # Check quiz keywords first
    if any(kw in message_lower for kw in keywords_quiz):
        return Intent.QUIZ

    # Default to chat
    return Intent.CHAT


def route_based_on_intent(state: UnifiedChatState) -> str:
    """Route to appropriate agent based on intent.

    Args:
        state: Current chat state

    Returns:
        Next node name ("chat_agent" or "quiz_agent")

    Note:
        Returns "chat_agent" if intent is None (default).
    """
    intent = state.get("intent")
    if intent == Intent.QUIZ:
        return "quiz_agent"
    return "chat_agent"


# ============ Agent Nodes ============


async def intent_router_node(state: UnifiedChatState) -> UnifiedChatState:
    """Detect intent from the latest user message.

    Args:
        state: Current chat state

    Returns:
        Updated state with intent set
    """
    messages = state.get("messages", [])
    if not messages:
        return {"intent": Intent.CHAT}

    last_msg = messages[-1]
    if isinstance(last_msg, HumanMessage):
        intent = detect_intent(last_msg.content)
        return {"intent": intent, "workspace": {"type": intent.value}}

    return {"intent": Intent.CHAT}


async def chat_agent_node(
    state: UnifiedChatState, agent: CompiledStateGraph
) -> UnifiedChatState:
    """Chat agent: Simple conversational response.

    Args:
        state: Current chat state
        agent: Pre-built chat agent from get_agent()

    Returns:
        Updated state with LLM response added to messages

    Note:
        Uses existing get_agent() from eduagent.agents.chat.
        Just invokes the agent and returns the result.
    """
    messages = state.get("messages", [])
    if not messages:
        return state

    last_msg = messages[-1]
    if not isinstance(last_msg, HumanMessage):
        return state

    result = await agent.ainvoke({"messages": [last_msg]})
    return {"messages": result["messages"]}


async def quiz_agent_node(
    state: UnifiedChatState, session: AsyncSession
) -> UnifiedChatState:
    """Quiz agent: Generate questions from existing workflow.

    Args:
        state: Current chat state
        session: Database session for saving

    Returns:
        Updated state with quiz result in workspace

    Note:
        Uses existing quiz workflow from eduagent.quiz.graph.
        Parses request from message and calls run_quiz_generation_workflow().
    """
    messages = state.get("messages", [])
    if not messages:
        return state

    last_msg = messages[-1]
    if not isinstance(last_msg, HumanMessage):
        return state

    text = last_msg.content
    topic = text.replace("出题", "").replace("生成题目", "").strip() or "默认主题"
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

        return {
            "messages": [result_msg],
            "workspace": workspace,
        }
    except Exception as e:
        error_msg = AIMessage(content=f"出题失败：{str(e)}")
        return {
            "messages": [error_msg],
            "workspace": {"type": "error", "message": str(e)},
        }


# ============ Graph Builder ============


def build_unified_chat_graph(
    agent: CompiledStateGraph, session: AsyncSession | None = None
) -> CompiledStateGraph:
    """Build unified chat graph with intent routing.

    Args:
        agent: Pre-built chat agent from get_agent()
        session: Optional database session for quiz agent

    Returns:
        Compiled LangGraph workflow

    Graph Structure:
        START → intent_router → {chat_agent, quiz_agent} → END
    """
    workflow = StateGraph(UnifiedChatState)

    workflow.add_node("intent_router", intent_router_node)
    workflow.add_node(
        "chat_agent",
        lambda state: chat_agent_node(state, agent),
    )
    workflow.add_node(
        "quiz_agent",
        lambda state: quiz_agent_node(state, session) if session else state,
    )

    workflow.add_edge(START, "intent_router")
    workflow.add_conditional_edges(
        "intent_router",
        route_based_on_intent,
        {
            "chat_agent": "chat_agent",
            "quiz_agent": "quiz_agent",
        },
    )
    workflow.add_edge("chat_agent", END)
    workflow.add_edge("quiz_agent", END)

    return workflow.compile()
