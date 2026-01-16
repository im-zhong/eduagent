"""Chat API endpoints for agent interactions.

This module provides REST API endpoints for chatting with the knowledge agent,
including thread management, message streaming, and history retrieval.
"""
from __future__ import annotations

import json
from uuid import uuid4

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from eduagent.agents.chat import (
    get_all_history,
    get_threads_for_user,
    init_new_agent_thread,
    insert_user_thread,
)
from eduagent.agents.chat_service import AgentMessage, agent_chat
from eduagent.llm import get_chat_model
from eduagent.unified_chat.prototype import unified_agent_chat


# Get current thread history if any
llm = get_chat_model()
router = APIRouter(prefix="/chat", tags=["Knowledge Chat Agent"])


class UserMessage(BaseModel):
    """Model for direct LLM chat messages."""

    messages: list


class NewChatRequest(BaseModel):
    """Model for creating a new chat thread."""

    user_id: str
    system_prompt: str | None = None


async def llm_chat(input: UserMessage):
    """Stream response directly from LLM (bypassing agent)."""
    async for chunk in llm.astream(input=input.messages):
        yield f"data: {json.dumps({'token': chunk.content})}\n\n"


# TODO: 使用lifespan管理生命周期，使用dependency注入依赖
# ===========================
# TODO: App lifecycle & dependency refactor plan
# ===========================
#
# Goal:
# - Use FastAPI lifespan to OWN resource lifecycle (create / cleanup)
# - Use Depends to ACCESS resources (agent / db / checkpointer)
# - Avoid importing `app` inside routers
#
# ---------------------------
# 1. Lifespan (resource creation & cleanup)
# ---------------------------
# - Create long-lived resources inside lifespan ONLY
#   - AsyncPostgresSaver (checkpointer)
#   - DB connection (checkpointer.conn)
#   - LangGraph agent
#
# - Put references into app.state:
#   app.state.agent
#   app.state.conn
#   (optional) app.state.checkpointer
#
# - Use `async with` or `AsyncExitStack`
#   - Let context managers handle cleanup automatically
#   - Do NOT manually close resources after yield
#
# ---------------------------
# 2. app.state usage rule
# ---------------------------
# - app.state is a STORAGE ONLY (holds references)
# - app.state MUST NOT:
#   - create resources
#   - manage lifecycle
#   - contain business logic
#
# ---------------------------
# 3. Dependency layer (Depends)
# ---------------------------
# - Create small dependency functions:
#   def get_agent(request: Request)
#   def get_conn(request: Request)
#
# - Dependencies ONLY:
#   - read from request.app.state
#   - validate resource exists
#   - raise HTTP 500 if not initialized
#
# - Dependencies MUST NOT:
#   - create resources
#   - close resources
#
# ---------------------------
# 4. Router usage rule
# ---------------------------
# - Routers MUST NOT:
#   - import FastAPI app instance
#   - access app.state directly
#
# - Routers MUST:
#   - use Depends(get_agent / get_conn)
#   - treat agent / conn as injected services
#
# ---------------------------
# 5. Testing & future-proofing
# ---------------------------
# - With Depends:
#   - easy to override agent / conn in tests
#   - safe for multi-worker & reload
#
# - Future extensions:
#   - replace app.state with AppServices dataclass
#   - add redis / vector db / http client via AsyncExitStack
#
# ===========================
# End TODO
# ===========================


# In separate router, we could not access the global fastapi app object
# So use the request.app which always points to the running FastAPI instance
# Request is injected by FastAPI


@router.post("/new-chat")
async def new_chat(req: NewChatRequest, request: Request) -> dict[str, str]:
    """Create a new chat thread.

    Creates a new thread ID, stores it in the database,
    and initializes it with an optional system prompt.
    """
    app = request.app
    thread_id = str(uuid4())
    await insert_user_thread(app.state.conn, req.user_id, thread_id)
    await init_new_agent_thread(
        agent=app.state.agent,
        user_id=req.user_id,
        thread_id=thread_id,
        system_prompt="let's start talk!",
    )
    return {"thread_id": thread_id}


@router.post("/agent-chat")
def do_agent_chat(input: AgentMessage, request: Request) -> StreamingResponse:
    """Send a message to the agent and stream the response.

    Streams the agent's response using Server-Sent Events (SSE) format.
    The agent maintains conversation history using the thread_id.
    """
    app = request.app
    return StreamingResponse(
        agent_chat(app.state.agent, input),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@router.get("/all-chat-threads")
async def get_chat_history(user_id: str, request: Request) -> list[str]:
    """Get all chat threads for a user.

    Returns a list of thread IDs for the given user, ordered by creation time.
    """
    app = request.app
    threads = await get_threads_for_user(conn=app.state.conn, user_id=user_id)
    return threads


@router.get("/thread-chat-messages")
async def get_thread_chat_messages(
    user_id: str, thread_id: str, request: Request
) -> list[dict]:
    """Get all messages in a specific thread.

    Returns the conversation history as a list of messages with
    role ("user", "assistant", "system") and content.
    """
    app = request.app
    messages = await get_all_history(
        agent=app.state.agent, user_id=user_id, thread_id=thread_id
    )
    print(messages)
    return messages


@router.get("/new-chat")
async def get_new_chat(user_id: str, request: Request) -> str:
    """Create a new chat thread (simpler version without system prompt)."""
    app = request.app
    thread_id = str(uuid4())
    await init_new_agent_thread(
        agent=app.state.agent, user_id=user_id, thread_id=thread_id
    )
    return thread_id


@router.post("/unified-chat")
def do_unified_agent_chat(input: AgentMessage, request: Request) -> StreamingResponse:
    """Unified chat endpoint with intent-based agent routing.

    Routes to different agents based on keyword detection:
    - "出题", "生成题目", "quiz", "question" → Quiz agent
    - Everything else → Chat agent

    Returns streaming response with tokens and workspace artifacts.

    Note:
        The session parameter is None for chat agent to work.
        Full implementation will include database session for quiz agent.
    """
    app = request.app
    unified_graph = getattr(app.state, "unified_chat_graph", None)

    return StreamingResponse(
        unified_agent_chat(unified_graph, input, None),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
