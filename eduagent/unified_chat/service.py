"""Unified chat service module for streaming multi-agent responses.

This module provides async generators for streaming unified chat responses from
the LangGraph workflow, extracting the streaming logic from API endpoints.

Following best practices from docs/langgraph/:
- Streaming happens at graph level using graph.astream()
- Nodes use invoke() internally (not stream())
- Runtime dependencies (chat_agent, session) passed via config
- SSE-formatted events for UI consumption
- Combined streaming modes: ["updates", "messages"]
"""

from __future__ import annotations

import json
from typing import Any

from langchain.messages import AIMessage, HumanMessage
from langgraph.graph.state import CompiledStateGraph
from sqlalchemy.ext.asyncio import AsyncSession

from eduagent.agents.chat import get_config
from eduagent.unified_chat.graph import build_unified_chat_graph, UnifiedChatState


async def stream_unified_chat(
    unified_graph: CompiledStateGraph,
    user_id: str,
    thread_id: str,
    message: str,
    chat_agent: CompiledStateGraph,
    session: AsyncSession | None = None,
):
    """Stream unified chat response with intent routing.

    This async generator yields SSE-formatted events for streaming response
    to the client. Uses LangGraph's combined streaming modes to emit both
    message tokens and workspace updates.

    Args:
        unified_graph: Compiled unified chat graph
        user_id: User identifier for checkpoint persistence
        thread_id: Thread identifier for conversation continuity
        message: User's message content
        chat_agent: The chat agent to use for conversational queries
        session: Optional database session for quiz agent

    Yields:
        SSE-formatted events in the format: "data: {json}\n\n"
        where json contains:
        - {"token": "..."} for message tokens from AI responses
        - {"workspace": {...}} for workspace state updates

    Note:
        Runtime dependencies (chat_agent, session) passed via config.
        Uses combined streaming modes ["updates", "messages"].
        Streamed outputs are tuples of (mode, chunk).
        UI can render tokens in real-time and show workspace artifacts.
    """
    # Create config with runtime dependencies
    config = get_config(user_id=user_id, thread_id=thread_id)
    # Add runtime dependencies to config
    config["configurable"]["chat_agent"] = chat_agent
    if session:
        config["configurable"]["session"] = session

    # Create initial state
    initial_state: UnifiedChatState = {
        "messages": [HumanMessage(content=message)],
        "intent": None,
        "workspace": {},
    }

    try:
        # Stream with combined modes: updates (state changes) and messages (tokens)
        async for mode, chunk in unified_graph.astream(
            initial_state,
            stream_mode=["updates", "messages"],
            config=config,
        ):
            if mode == "updates":
                # chunk format: {node_name: state_update}
                for node_name, state_update in chunk.items():
                    # Extract workspace updates for UI rendering
                    workspace = state_update.get("workspace", {})
                    if workspace:
                        yield _format_sse({"workspace": workspace, "node": node_name})

            elif mode == "messages":
                # chunk is a list of Message objects
                messages = chunk if isinstance(chunk, list) else [chunk]
                for msg in messages:
                    if isinstance(msg, AIMessage) and msg.content:
                        # Token streaming for AI messages
                        yield _format_sse({"token": msg.content})

    except Exception as e:
        # Emit error event
        yield _format_sse({"error": str(e)})


def _format_sse(data: dict[str, Any]) -> str:
    """Format data as Server-Sent Event.

    Args:
        data: Dictionary to format as SSE

    Returns:
        SSE-formatted string: "data: {json}\n\n"
    """
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
