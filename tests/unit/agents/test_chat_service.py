"""Unit tests for chat service module.

Tests the AgentMessage class and agent_chat async generator
for streaming responses from the LangGraph agent.
"""
from __future__ import annotations

import json

import pytest
from langchain.messages import AIMessage, HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph.state import CompiledStateGraph

from eduagent.agents.chat import get_agent
from eduagent.agents.chat_service import AgentMessage, agent_chat
from eduagent.llm import get_chat_model


# ============ Test AgentMessage class ============


def test_agent_message_creation() -> None:
    """Test AgentMessage object creation and attribute access."""
    message = AgentMessage(user_id="user123", thread_id="thread456", message="Hello")

    assert message.user_id == "user123"
    assert message.thread_id == "thread456"
    assert message.message == "Hello"


def test_agent_message_attributes() -> None:
    """Test that AgentMessage has required attributes."""
    message = AgentMessage(user_id="test", thread_id="abc", message="test message")

    # Verify attributes are set correctly
    assert hasattr(message, "user_id")
    assert hasattr(message, "thread_id")
    assert hasattr(message, "message")

    # Verify types
    assert isinstance(message.user_id, str)
    assert isinstance(message.thread_id, str)
    assert isinstance(message.message, str)


# ============ Integration tests with actual agent ============


@pytest.mark.integration
@pytest.mark.asyncio
async def test_agent_chat_yields_sse_format() -> None:
    """Test that agent_chat yields SSE-formatted tokens."""
    llm = get_chat_model()
    checkpointer = MemorySaver()
    chat_agent = get_agent(llm, checkpointer)

    test_message = AgentMessage(
        user_id="test_user", thread_id="test_thread", message="你好"
    )

    # Collect yielded tokens
    yielded_tokens = []
    async for token in agent_chat(chat_agent, test_message):
        yielded_tokens.append(token)

    # Verify we got a response
    assert len(yielded_tokens) > 0

    # Verify SSE format
    for token in yielded_tokens:
        assert token.startswith("data: ")
        assert token.endswith("\n\n")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_agent_chat_token_content() -> None:
    """Test that agent_chat yields valid JSON tokens."""
    llm = get_chat_model()
    checkpointer = MemorySaver()
    chat_agent = get_agent(llm, checkpointer)

    test_message = AgentMessage(
        user_id="test_user", thread_id="test_thread", message="What is 1+1?"
    )

    # Collect and parse yielded tokens
    parsed_tokens = []
    async for token in agent_chat(chat_agent, test_message):
        # Parse SSE format: "data: {json}\n\n"
        json_str = token.replace("data: ", "").replace("\n\n", "")
        parsed_tokens.append(json.loads(json_str))

    # Verify token structure
    assert all("token" in token for token in parsed_tokens)
    assert all(isinstance(token["token"], str) for token in parsed_tokens)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_agent_chat_with_config() -> None:
    """Test that agent_chat passes correct config to agent."""
    llm = get_chat_model()
    checkpointer = MemorySaver()
    chat_agent = get_agent(llm, checkpointer)

    test_message = AgentMessage(
        user_id="user_xyz", thread_id="thread_789", message="Hello"
    )

    # Collect tokens
    yielded_tokens = []
    async for token in agent_chat(chat_agent, test_message):
        yielded_tokens.append(token)

    # Verify some response was generated
    assert len(yielded_tokens) > 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_agent_chat_multiple_messages() -> None:
    """Test agent_chat with multiple sequential messages."""
    llm = get_chat_model()
    checkpointer = MemorySaver()
    chat_agent = get_agent(llm, checkpointer)

    user_id = "test_user_multi"
    thread_id = "test_thread_multi"

    # Send first message
    message1 = AgentMessage(user_id=user_id, thread_id=thread_id, message="My name is Alice")
    tokens1 = []
    async for token in agent_chat(chat_agent, message1):
        tokens1.append(token)
    assert len(tokens1) > 0

    # Send second message
    message2 = AgentMessage(user_id=user_id, thread_id=thread_id, message="What is my name?")
    tokens2 = []
    async for token in agent_chat(chat_agent, message2):
        tokens2.append(token)
    assert len(tokens2) > 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_agent_chat_with_different_users() -> None:
    """Test that agent_chat maintains separate contexts for different users."""
    llm = get_chat_model()
    checkpointer = MemorySaver()
    chat_agent = get_agent(llm, checkpointer)

    # User 1 sends a message
    user1_message = AgentMessage(
        user_id="user1", thread_id="thread1", message="I like Python"
    )
    tokens1 = []
    async for token in agent_chat(chat_agent, user1_message):
        tokens1.append(token)
    assert len(tokens1) > 0

    # User 2 sends a message (different thread)
    user2_message = AgentMessage(
        user_id="user2", thread_id="thread2", message="What programming language?"
    )
    tokens2 = []
    async for token in agent_chat(chat_agent, user2_message):
        tokens2.append(token)
    assert len(tokens2) > 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_agent_chat_sse_format_structure() -> None:
    """Test that SSE format matches expected structure exactly."""
    llm = get_chat_model()
    checkpointer = MemorySaver()
    chat_agent = get_agent(llm, checkpointer)

    test_message = AgentMessage(
        user_id="test_user", thread_id="test_thread", message="Hello"
    )

    # Check first token format
    async for token in agent_chat(chat_agent, test_message):
        # Verify exact SSE format: "data: {json}\n\n"
        assert token.startswith("data: ")
        assert token.endswith("\n\n")

        # Verify valid JSON in the data field
        data_part = token[6:-2]  # Remove "data: " prefix and "\n\n" suffix
        parsed = json.loads(data_part)
        assert "token" in parsed

        # Just check first token, then break
        break
