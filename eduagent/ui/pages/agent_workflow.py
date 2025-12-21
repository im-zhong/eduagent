from __future__ import annotations

import streamlit as st

from eduagent.defs import defs
from eduagent.ui import common
from eduagent.ui.api_client import EduAgentAPIClient
from eduagent.ui.react_stream import drain_stream_queue


def render(client: EduAgentAPIClient) -> None:
    st.title("ReAct 代理工作流（LangGraph）")
    st.caption(
        "选择一个已完成的解析任务，输入中文指令，实时查看代理的推理、工具使用、待办和参考资料。"
    )
    common.ensure_reference_style()
    stream_state = common.get_agent_stream_state()
    drain_stream_queue(stream_state)
    control_cols = st.columns([3, 1])
    with control_cols[1]:
        refresh_clicked = st.button("刷新笔记本", key="agent_refresh")
    catalog_items = common.load_ingestion_catalog(client, refresh=refresh_clicked)
    selected_job = common.render_ingestion_selector(catalog_items)

    prompt = st.text_area(
        "代理指令（中文）",
        key="agent_prompt",
        height=180,
        placeholder=("示例：生成 5 道涵盖该笔记本核心知识的选择题。"),
    )
    st.markdown("---")
    if st.button(
        "启动 ReAct 代理",
        type="primary",
        disabled=not (selected_job and prompt.strip()),
    ):
        if selected_job is None:
            st.error("请先选择一个笔记本。")
        else:
            common.start_agent_stream(client, selected_job, prompt.strip())
            rerun = getattr(st, "experimental_rerun", None)
            if callable(rerun):
                rerun()

    common.render_agent_stream(stream_state)
