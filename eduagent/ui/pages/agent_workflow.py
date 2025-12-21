from __future__ import annotations

import streamlit as st

from eduagent.defs import defs
from eduagent.ui import common
from eduagent.ui.api_client import EduAgentAPIClient
from eduagent.ui.react_stream import drain_stream_queue


def render(client: EduAgentAPIClient) -> None:
    st.title("ReAct Agent Workflow (LangGraph)")
    st.caption(
        "Pick a completed ingestion job, enter a Chinese instruction, and watch the agent's reasoning,"
        " tool usage, todo list, and references streamed via SSE."
    )
    common.ensure_reference_style()
    stream_state = common.get_agent_stream_state()
    drain_stream_queue(stream_state)
    control_cols = st.columns([3, 1])
    with control_cols[1]:
        refresh_clicked = st.button("Refresh notebooks", key="agent_refresh")
    catalog_items = common.load_ingestion_catalog(client, refresh=refresh_clicked)
    selected_job = common.render_ingestion_selector(catalog_items)

    prompt = st.text_area(
        "Agent instruction (write in Chinese)",
        key="agent_prompt",
        height=180,
        placeholder=(
            "Example: Generate five multiple-choice questions covering the key knowledge from this notebook."
        ),
    )
    st.markdown("---")
    if st.button(
        "Start ReAct agent",
        type="primary",
        disabled=not (selected_job and prompt.strip()),
    ):
        if selected_job is None:
            st.error("Please pick a notebook first.")
        else:
            common.start_agent_stream(client, selected_job, prompt.strip())
            rerun = getattr(st, "experimental_rerun", None)
            if callable(rerun):
                rerun()

    common.render_agent_stream(stream_state)
