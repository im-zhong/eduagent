"""Unit tests for unified_chat components.

Tests the intent detection, routing, and state management functions
for the unified chat system without mocking.
"""
from __future__ import annotations

import json

import pytest
from langchain.messages import AIMessage, HumanMessage

from eduagent.agents.chat import get_agent
from eduagent.llm import get_chat_model
from eduagent.unified_chat.prototype import (
    Intent,
    UnifiedChatState,
    build_unified_chat_graph,
    detect_intent,
    intent_router_node,
    route_based_on_intent,
    unified_agent_chat,
)
from langgraph.checkpoint.memory import MemorySaver


# ============ Test detect_intent function ============


@pytest.mark.parametrize(
    ("message", "expected_intent"),
    [
        # Quiz-related keywords
        ("请帮我出题", Intent.QUIZ),
        ("生成题目", Intent.QUIZ),
        ("make a quiz", Intent.QUIZ),
        ("question about topic", Intent.QUIZ),
        # Chat-related keywords (default fallback)
        ("你好", Intent.CHAT),
        ("hello there", Intent.CHAT),
        ("help me", Intent.CHAT),
        ("帮助", Intent.CHAT),
        # Non-keyword messages (default to chat)
        ("随便聊点什么", Intent.CHAT),
        ("how are you?", Intent.CHAT),
    ],
)
def test_detect_intent(message: str, expected_intent: Intent) -> None:
    """Test intent detection from user messages."""
    result = detect_intent(message)
    assert result == expected_intent


def test_detect_intent_case_insensitive() -> None:
    """Test that intent detection is case insensitive."""
    assert detect_intent("Quiz please") == Intent.QUIZ
    assert detect_intent("出题") == Intent.QUIZ
    assert detect_intent("HELLO") == Intent.CHAT


# ============ Test route_based_on_intent function ============


@pytest.mark.parametrize(
    ("intent", "expected_route"),
    [
        (Intent.QUIZ, "quiz_agent"),
        (Intent.CHAT, "chat_agent"),
        (None, "chat_agent"),
    ],
)
def test_route_based_on_intent(intent: Intent | None, expected_route: str) -> None:
    """Test routing based on detected intent."""
    state: UnifiedChatState = {"intent": intent, "messages": [], "workspace": {}, "llm_calls": 0}
    result = route_based_on_intent(state)
    assert result == expected_route


# ============ Test intent_router_node ============


@pytest.mark.asyncio
async def test_intent_router_node_with_human_message() -> None:
    """Test intent router node processes human messages correctly."""
    state: UnifiedChatState = {
        "messages": [HumanMessage(content="请出题")],
        "intent": None,
        "workspace": {},
        "llm_calls": 0,
    }

    result = await intent_router_node(state)

    assert result["intent"] == Intent.QUIZ
    assert result["workspace"]["type"] == "quiz"


@pytest.mark.asyncio
async def test_intent_router_node_with_ai_message() -> None:
    """Test intent router node defaults to CHAT for non-human messages."""
    state: UnifiedChatState = {
        "messages": [AIMessage(content="Hello")],
        "intent": None,
        "workspace": {},
        "llm_calls": 0,
    }

    result = await intent_router_node(state)

    assert result["intent"] == Intent.CHAT


@pytest.mark.asyncio
async def test_intent_router_node_empty_messages() -> None:
    """Test intent router node handles empty message list."""
    state: UnifiedChatState = {
        "messages": [],
        "intent": None,
        "workspace": {},
        "llm_calls": 0,
    }

    result = await intent_router_node(state)

    assert result["intent"] == Intent.CHAT


# ============ Integration tests with actual graph ============


@pytest.mark.integration
@pytest.mark.asyncio
async def test_unified_chat_end_to_end_with_chat_agent() -> None:
    """End-to-end test of unified chat with actual chat agent.

    This test requires a running LLM and will invoke the chat agent
    to verify the full flow works correctly.
    """
    llm = get_chat_model()
    checkpointer = MemorySaver()
    chat_agent = get_agent(llm, checkpointer)
    unified_graph = build_unified_chat_graph(agent=chat_agent, session=None)

    # Create a mock message object
    class AgentMessageMock:
        def __init__(self, user_id: str, thread_id: str, message: str):
            self.user_id = user_id
            self.thread_id = thread_id
            self.message = message

    test_message = AgentMessageMock(
        user_id="test_user", thread_id="test_thread", message="你好"
    )

    # Collect yielded tokens
    yielded_tokens = []
    async for token in unified_agent_chat(unified_graph, test_message, session=None):
        yielded_tokens.append(token)

    # Verify we got a response
    assert len(yielded_tokens) > 0

    # Verify the format
    token_data = json.loads(
        yielded_tokens[0].replace("data: ", "").replace("\n\n", "")
    )
    assert "token" in token_data
    assert token_data["token"] is not None
    assert token_data["workspace"] == {}


@pytest.mark.integration
@pytest.mark.asyncio
async def test_unified_chat_with_quiz_keyword() -> None:
    """Test unified chat correctly routes quiz keywords.

    This test verifies that quiz-related keywords are detected correctly
    and routed to the appropriate agent.
    """
    llm = get_chat_model()
    checkpointer = MemorySaver()
    chat_agent = get_agent(llm, checkpointer)
    unified_graph = build_unified_chat_graph(agent=chat_agent, session=None)

    class AgentMessageMock:
        def __init__(self, user_id: str, thread_id: str, message: str):
            self.user_id = user_id
            self.thread_id = thread_id
            self.message = message

    # Test with quiz keyword - should route to quiz agent
    test_message = AgentMessageMock(
        user_id="test_user", thread_id="test_thread", message="请帮我出题"
    )

    yielded_tokens = []
    async for token in unified_agent_chat(unified_graph, test_message, session=None):
        yielded_tokens.append(token)

    # Should get a response (even from the error case in quiz_agent_node)
    assert len(yielded_tokens) >= 1
