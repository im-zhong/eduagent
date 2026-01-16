"""Simple unified chat UI.

A minimal chat interface that uses the /api/v1/chat/unified-chat endpoint.
Features:
- Chat message display
- Streaming responses
- Simple session management (thread_id)
"""

from __future__ import annotations

import json
from uuid import uuid4

import requests
import streamlit as st

from eduagent.ui.api_client import EduAgentAPIClient


def _init_state() -> None:
    """Initialize session state variables."""
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []
    if "chat_thread_id" not in st.session_state:
        st.session_state.chat_thread_id = ""
    if "chat_user_id" not in st.session_state:
        st.session_state.chat_user_id = "default_user"


def _get_headers() -> dict[str, str]:
    """Get authorization headers."""
    token = st.session_state.get("service_jwt")
    headers: dict[str, str] = {}
    if isinstance(token, str) and token.strip():
        headers["Authorization"] = f"Bearer {token.strip()}"
    return headers


def _create_new_thread(client: EduAgentAPIClient) -> str:
    """Create a new chat thread via API.

    Returns:
        The new thread_id
    """
    user_id = st.session_state.chat_user_id
    url = f"{client.base_url}/api/v1/chat/new-chat"
    params = {"user_id": user_id}

    response = requests.get(
        url,
        params=params,
        headers=_get_headers(),
        timeout=10,
    )
    response.raise_for_status()
    return response.text


def _render_messages() -> None:
    """Render chat messages."""
    for message in st.session_state.chat_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])


def _send_message(client: EduAgentAPIClient, prompt: str) -> str:
    """Send message to API and stream response.

    Args:
        client: API client
        prompt: User message

    Returns:
        The assistant's response text
    """
    # Create thread if needed
    if not st.session_state.chat_thread_id:
        st.session_state.chat_thread_id = _create_new_thread(client)

    request_payload = {
        "user_id": st.session_state.chat_user_id,
        "thread_id": st.session_state.chat_thread_id,
        "message": prompt,
    }

    full_response = ""
    with requests.post(
        url=f"{client.base_url}/api/v1/chat/unified-chat",
        json=request_payload,
        headers=_get_headers(),
        stream=True,
        timeout=120,
    ) as response:
        response.raise_for_status()
        for line in response.iter_lines(decode_unicode=True):
            if not line or not line.startswith("data: "):
                continue
            payload = json.loads(line[6:])
            token = payload.get("token", "")
            if token:
                full_response += token
            # Handle workspace updates if needed
            workspace = payload.get("workspace")
            if workspace:
                # Could display workspace info here
                pass

    return full_response


def render(client: EduAgentAPIClient) -> None:
    """Render simple unified chat UI.

    Args:
        client: EduAgent API client
    """
    st.title("💬 智能对话")
    _init_state()

    # Sidebar: New chat button
    with st.sidebar:
        st.header("设置")
        if st.button("➕ 新对话", use_container_width=True):
            st.session_state.chat_thread_id = ""
            st.session_state.chat_messages = []
            st.rerun()

        st.caption(f"用户ID: {st.session_state.chat_user_id}")
        if st.session_state.chat_thread_id:
            st.caption(f"会话ID: {st.session_state.chat_thread_id[:8]}...")
        else:
            st.caption("会话: (新会话)")

    # Main chat interface
    _render_messages()

    # Chat input
    if prompt := st.chat_input("请输入问题…"):
        # Add user message
        st.session_state.chat_messages.append({"role": "user", "content": prompt})

        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)

        # Get assistant response with streaming
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = ""

            try:
                # Create thread if needed and send message
                if not st.session_state.chat_thread_id:
                    with st.spinner("创建会话…"):
                        st.session_state.chat_thread_id = _create_new_thread(client)

                request_payload = {
                    "user_id": st.session_state.chat_user_id,
                    "thread_id": st.session_state.chat_thread_id,
                    "message": prompt,
                }

                with requests.post(
                    url=f"{client.base_url}/api/v1/chat/unified-chat",
                    json=request_payload,
                    headers=_get_headers(),
                    stream=True,
                    timeout=120,
                ) as response:
                    response.raise_for_status()
                    for line in response.iter_lines(decode_unicode=True):
                        if not line or not line.startswith("data: "):
                            continue
                        payload = json.loads(line[6:])
                        token = payload.get("token", "")
                        if token:
                            full_response += token
                            message_placeholder.markdown(full_response + "▌")

            except requests.exceptions.RequestException as e:
                full_response = f"请求失败: {e}"
                message_placeholder.error(full_response)

            # Final render
            message_placeholder.markdown(full_response)

        # Add assistant message to history
        st.session_state.chat_messages.append({"role": "assistant", "content": full_response})
        st.rerun()
