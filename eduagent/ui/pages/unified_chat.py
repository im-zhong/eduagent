"""Unified chat UI for multi-agent orchestration."""
from __future__ import annotations

import json
from typing import Any

import requests
import streamlit as st
from pydantic import BaseModel, Field

from eduagent.ui.api_client import EduAgentAPIClient


class Artifact(BaseModel):
    """Workspace artifact payload for the right panel."""

    type: str
    title: str
    payload: dict[str, Any] = Field(default_factory=dict)


class ChatMessage(BaseModel):
    """Chat message with optional intent and artifacts."""

    role: str
    content: str
    intent: str | None = None
    artifacts: list[Artifact] = Field(default_factory=list)


class UnifiedChatRequest(BaseModel):
    """Request payload for unified chat API."""

    message: str
    mode: str
    history: list[ChatMessage] = Field(default_factory=list)
    thread_id: str | None = None


class UnifiedChatResponse(BaseModel):
    """Response payload for unified chat API."""

    assistant_message: str | None = None
    intent: str | None = None
    workspace: dict[str, Any] = Field(default_factory=dict)
    artifacts: list[Artifact] = Field(default_factory=list)
    token: str | None = None


def _init_state() -> None:
    if "unified_chat_messages" not in st.session_state:
        st.session_state.unified_chat_messages = []
    if "unified_chat_workspace" not in st.session_state:
        st.session_state.unified_chat_workspace = []
    if "unified_chat_mode" not in st.session_state:
        st.session_state.unified_chat_mode = "auto"
    if "unified_chat_thread_id" not in st.session_state:
        st.session_state.unified_chat_thread_id = None


def _render_mode_panel() -> str:
    st.subheader("模式")
    options = {
        "自动路由": "auto",
        "聊天": "chat",
        "出题": "quiz",
    }
    selected = st.radio(
        "选择模式",
        options=list(options.keys()),
        index=list(options.values()).index(st.session_state.unified_chat_mode),
        label_visibility="collapsed",
    )
    mode = options[selected]
    st.session_state.unified_chat_mode = mode
    if st.button("重置会话", type="secondary"):
        st.session_state.unified_chat_messages = []
        st.session_state.unified_chat_workspace = []
        st.session_state.unified_chat_thread_id = None
        st.rerun()
    return mode


def _render_chat_panel(messages: list[ChatMessage]) -> None:
    st.subheader("对话")
    if not messages:
        st.caption("请输入问题开始对话。")
        return
    for message in messages:
        with st.chat_message(message.role):
            if message.intent and message.role == "assistant":
                st.caption(f"意图: {message.intent}")
            st.markdown(message.content)


def _render_workspace_panel(artifacts: list[Artifact]) -> None:
    st.subheader("工作区")
    if not artifacts:
        st.caption("暂无工作区输出。")
        return
    for artifact in artifacts:
        with st.expander(f"{artifact.title} ({artifact.type})"):
            st.json(artifact.payload)


def _to_messages(raw: list[ChatMessage]) -> list[ChatMessage]:
    return [ChatMessage.model_validate(msg) for msg in raw]


def _to_artifacts(raw: list[Artifact]) -> list[Artifact]:
    return [Artifact.model_validate(item) for item in raw]


def _to_workspace_artifacts(workspace: dict[str, Any]) -> list[Artifact]:
    if not workspace:
        return []
    artifact_type = workspace.get("type", "workspace")
    title = "工作区快照"
    if artifact_type == "quiz_result":
        title = "出题结果"
    return [Artifact(type=artifact_type, title=title, payload=workspace)]


def _headers() -> dict[str, str]:
    token = st.session_state.get("service_jwt")
    headers: dict[str, str] = {}
    if isinstance(token, str) and token.strip():
        headers["Authorization"] = f"Bearer {token.strip()}"
    return headers


def render(client: EduAgentAPIClient) -> None:
    """Render unified chat UI."""
    st.title("统一对话")
    _init_state()

    col_left, col_center, col_right = st.columns([1, 3, 2])
    with col_left:
        mode = _render_mode_panel()
    with col_center:
        _render_chat_panel(_to_messages(st.session_state.unified_chat_messages))
    with col_right:
        _render_workspace_panel(
            _to_artifacts(st.session_state.unified_chat_workspace)
        )

    prompt = st.chat_input("请输入问题或需求…")
    if not prompt:
        return

    user_message = ChatMessage(role="user", content=prompt)
    st.session_state.unified_chat_messages.append(user_message)

    with st.chat_message("user"):
        st.markdown(prompt)

    request_payload = UnifiedChatRequest(
        message=prompt,
        mode=mode,
        history=_to_messages(st.session_state.unified_chat_messages),
        thread_id=st.session_state.unified_chat_thread_id,
    )
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        workspace: dict[str, Any] = {}
        with requests.post(
            url=f"{client.base_url}/api/v1/chat/unified-chat",
            json=request_payload.model_dump(),
            headers=_headers(),
            stream=True,
            timeout=60,
        ) as response:
            for line in response.iter_lines(decode_unicode=True):
                if not line or not line.startswith("data: "):
                    continue
                payload = json.loads(line[6:])
                token = payload.get("token", "")
                if token:
                    full_response += token
                    message_placeholder.markdown(full_response + "▌")
                next_workspace = payload.get("workspace")
                if isinstance(next_workspace, dict) and next_workspace:
                    workspace = next_workspace

        message_placeholder.markdown(full_response or "未收到回复。")

    assistant_message = ChatMessage(
        role="assistant",
        content=full_response or "未收到回复。",
        intent=workspace.get("type"),
    )
    st.session_state.unified_chat_messages.append(assistant_message)
    st.session_state.unified_chat_workspace = _to_workspace_artifacts(workspace)
    st.rerun()
