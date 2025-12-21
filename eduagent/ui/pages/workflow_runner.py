from __future__ import annotations

import streamlit as st

from eduagent.ui.api_client import EduAgentAPIClient


def render(client: EduAgentAPIClient) -> None:
    st.title("Workflow Runner")
    ingestion_job = st.text_input("Ingestion Job ID")
    prompt = st.text_area("Prompt", height=160)
    if st.button("Run Workflow") and ingestion_job and prompt:
        with st.spinner("Executing LangGraph workflow..."):
            result = client.run_quiz_workflow(ingestion_job, prompt)
        if "error" in result:
            st.error(result["error"])
        else:
            st.success("Workflow completed")
            st.json(result)
