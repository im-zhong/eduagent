"""Chat service module for streaming agent responses.

This module provides async generators for streaming chat responses from
the LangGraph agent, extracting the streaming logic from API endpoints.
"""
from __future__ import annotations

import json

from langchain.messages import HumanMessage
from langgraph.graph.state import CompiledStateGraph

from eduagent.agents.chat import get_config


class AgentMessage:
    """Model for agent chat message input.

    Attributes:
        user_id: User identifier for the conversation
        thread_id: Thread identifier for conversation continuity
        message: The user's message content
    """

    user_id: str
    thread_id: str
    message: str

    def __init__(self, user_id: str, thread_id: str, message: str) -> None:
        self.user_id = user_id
        self.thread_id = thread_id
        self.message = message


async def agent_chat(agent: CompiledStateGraph, message: AgentMessage):
    """Stream chat response from the agent.

    This async generator yields SSE-formatted tokens for streaming response
    to the client. It uses the agent's checkpoint system to maintain
    conversation history across multiple requests.

    Args:
        agent: Compiled LangGraph agent with checkpointer
        message: AgentMessage containing user_id, thread_id, and message content

    Yields:
        SSE-formatted tokens in the format: "data: {json}\n\n"
        where json contains {"token": "content"}

    Note:
        Uses stream_mode="messages" to get full message objects.
        The config with user_id and thread_id ensures checkpoint
        persistence across requests for conversation continuity.
    """
    # Get config for checkpoint persistence with thread_id and user_id
    config = get_config(user_id=message.user_id, thread_id=message.thread_id)

    # Stream messages from the agent using messages stream mode
    async for chunk in agent.astream(
        input={"messages": [HumanMessage(content=message.message)]},
        stream_mode="messages",
        config=config,
    ):
        # chunk is a list with one message when stream_mode="messages"
        yield f"data: {json.dumps({'token': chunk[0].content})}\n\n"
