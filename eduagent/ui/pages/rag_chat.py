from __future__ import annotations

import streamlit as st

from eduagent.ui import common
from eduagent.ui.api_client import EduAgentAPIClient
from eduagent.ui.react_stream import drain_stream_queue


def render(client: EduAgentAPIClient) -> None:
    st.title("LangGraph RAG Chat")
    st.caption(
        "选择一个或多个已完成的笔记本，使用中文提问，实时查看助教的检索与回答过程。"
    )
    common.ensure_reference_style()
    stream_state = common.get_rag_stream_state()
    drain_stream_queue(stream_state)
    control_cols = st.columns([3, 1, 1])
    with control_cols[1]:
        refresh_clicked = st.button("刷新笔记本", key="rag_refresh")
    with control_cols[2]:
        if st.button("清空对话", key="rag_reset"):
            common.reset_rag_chat_session()
            stream_state = common.get_rag_stream_state()
    catalog_items = common.load_ingestion_catalog(client, refresh=refresh_clicked)
    if catalog_items:
        job_map = {str(item["job_id"]): item for item in catalog_items}
        selected_jobs = st.multiselect(
            "选择知识库笔记",
            options=list(job_map.keys()),
            default=st.session_state.get("rag_selected_jobs") or [],
            format_func=lambda job: common.format_ingestion_label(job, job_map[job]),
        )
        st.session_state["rag_selected_jobs"] = selected_jobs
    else:
        selected_jobs = []
    st.markdown("---")
    history = common.get_rag_chat_history()
    for turn in history:
        role = "assistant" if turn.get("role") == "assistant" else "user"
        with st.chat_message(role):
            st.markdown(turn.get("content") or "")
    question = st.chat_input("请输入中文问题")
    if question:
        if not selected_jobs:
            st.warning("请至少选择一个已完成的笔记本。")
        else:
            prior_history = history.copy()
            updated_history = [*history, {"role": "user", "content": question}]
            st.session_state[common.RAG_CHAT_HISTORY_KEY] = updated_history
            common.start_rag_chat_stream(client, selected_jobs, prior_history, question)
            rerun = getattr(st, "experimental_rerun", None)
            if callable(rerun):
                rerun()
    st.markdown("---")
    common.render_rag_stream(stream_state)
