from __future__ import annotations

import json

import requests
import streamlit as st

from eduagent.api.endpoints.chat import AgentMessage
from eduagent.ui.api_client import EduAgentAPIClient
from eduagent.ui import common


def _load_user_id() -> str:
    secrets = getattr(st, "secrets", None) or {}
    user = secrets.get("agent_chat_user_id")
    if not isinstance(user, str) or not user.strip():
        st.error("缺少 agent_chat_user_id，请在 secrets.toml 中配置该用户。")
        st.stop()
    return user.strip()


def render(client: EduAgentAPIClient | None = None) -> None:
    st.title("对话演示")
    user_id = _load_user_id()
    st.caption(f"使用预设用户：{user_id}")

    if "current_thread_id" not in st.session_state:
        st.session_state.current_thread_id = None

    def _ordered_messages(msgs: list[dict]) -> list[dict]:
        # Show oldest at the top
        return list(reversed(msgs))

    base_url = (client.base_url if client else "http://api.eduagent:8000").rstrip("/")
    token = getattr(st.session_state, "service_jwt", None)

    def _headers() -> dict[str, str]:
        headers: dict[str, str] = {}
        if isinstance(token, str) and token.strip():
            headers["Authorization"] = f"Bearer {token.strip()}"
        return headers

    def fetch_threads() -> list[str]:
        resp = requests.get(
            f"{base_url}/api/v1/chat/all-chat-threads",
            params={"user_id": user_id},
            headers=_headers(),
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()

    def fetch_thread_chat_messages(thread_id: str) -> list[dict]:
        resp = requests.get(
            f"{base_url}/api/v1/chat/thread-chat-messages",
            params={"user_id": user_id, "thread_id": thread_id},
            headers=_headers(),
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()

    def new_chat() -> str:
        resp = requests.post(
            f"{base_url}/api/v1/chat/new-chat",
            json={"user_id": user_id},
            headers=_headers(),
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["thread_id"]

    selected_kb: str | None = None
    if client:
        refresh_kb = st.button("刷新知识库列表", key="agent_chat_kb_refresh")
        catalog_items = common.load_ingestion_catalog(client, refresh=refresh_kb)
        if catalog_items:
            job_map = {str(item["job_id"]): item for item in catalog_items}
            options = list(job_map.keys())
            selected_kb = st.selectbox(
                "选择知识库",
                options=options,
                format_func=lambda job: common.format_ingestion_label(
                    job, job_map[job]
                ),
                key="agent_chat_kb",
            )
            st.session_state["agent_chat_selected_kb"] = selected_kb
        else:
            st.info("暂无已完成的知识库，请先上传并完成摄取。")
    else:
        st.info("未检测到 API 客户端，无法加载知识库列表。")

    st.sidebar.header("历史对话")
    try:
        thread_ids = fetch_threads()
    except requests.RequestException as exc:
        st.sidebar.error(f"加载历史失败: {exc}")
        thread_ids = []

    if st.sidebar.button("➕ 新建对话", use_container_width=True):
        st.session_state.current_thread_id = new_chat()
        st.rerun()

    if not thread_ids:
        st.sidebar.caption("暂无对话，已自动创建新会话。")
        st.session_state.current_thread_id = new_chat()
    else:
        if st.session_state.current_thread_id not in thread_ids:
            st.session_state.current_thread_id = thread_ids[0]

        selected = st.sidebar.radio(
            "对话列表",
            options=thread_ids,
            index=thread_ids.index(st.session_state.current_thread_id),
            label_visibility="collapsed",
        )
        st.session_state.current_thread_id = selected
        st.session_state.messages = _ordered_messages(
            fetch_thread_chat_messages(st.session_state.current_thread_id)
        )

    if st.session_state.current_thread_id is None or "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "Let's start chatting! 👇"}
        ]

    for message in _ordered_messages(st.session_state.messages):
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    with st.form("agent_chat_form"):
        prompt = st.text_area("请输入问题", key="agent_chat_prompt", height=100)
        send = st.form_submit_button("发送")

    if send and prompt.strip():
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = ""
            agent_message = AgentMessage(
                message=prompt,
                user_id=user_id,
                thread_id=st.session_state.current_thread_id,
            )

            with requests.post(
                url=f"{base_url}/api/v1/chat/agent-chat",
                json=agent_message.model_dump(),
                headers=_headers(),
                stream=True,
                timeout=30,
            ) as r:
                for line in r.iter_lines(decode_unicode=True):
                    if not line or not line.startswith("data: "):
                        continue
                    payload = json.loads(line[5:])
                    token = payload["token"]
                    full_response += token
                    message_placeholder.markdown(full_response + "▌")

            message_placeholder.markdown(full_response)
        st.session_state.messages.append(
            {"role": "assistant", "content": full_response}
        )
