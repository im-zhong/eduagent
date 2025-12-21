from __future__ import annotations

import streamlit as st

from eduagent.ui.api_client import EduAgentAPIClient


def render(client: EduAgentAPIClient) -> None:
    st.title("工作流运行")
    ingestion_job = st.text_input("摄取任务 ID")
    prompt = st.text_area("提示词", height=160)
    if st.button("运行工作流") and ingestion_job and prompt:
        with st.spinner("正在执行 LangGraph 工作流..."):
            result = client.run_quiz_workflow(ingestion_job, prompt)
        if "error" in result:
            st.error(result["error"])
        else:
            st.success("工作流已完成")
            st.json(result)
