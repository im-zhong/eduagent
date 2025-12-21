from __future__ import annotations

import streamlit as st

from eduagent.ui.api_client import EduAgentAPIClient


def render(client: EduAgentAPIClient) -> None:
    st.title("EduAgent Operations Console")
    st.write(
        "Manage ingestion jobs, run the LangGraph workflow, and coordinate quiz "
        "generation/evaluation using the secured API."
    )
    if st.button("Check API Health"):
        with st.spinner("Contacting API..."):
            result = client.health_check()
            if "error" in result:
                st.error(result["error"])
            else:
                st.success("API is healthy")
                st.json(result)

    st.subheader("Workflow")
    st.markdown(
        "1. Upload document via **Ingestion Lab**\n"
        "2. Optionally run **Workflow Runner** for synchronous results\n"
        "3. Use **Async Pipeline** to orchestrate Celery jobs\n"
        "4. Validate quality in **Scoring Studio**\n"
        "5. Monitor overall metrics through **Analytics Monitor**"
    )
