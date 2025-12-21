from __future__ import annotations

import streamlit as st

from eduagent.api.schemas import SubjectArea
from eduagent.defs import defs
from eduagent.ui.api_client import EduAgentAPIClient


def render(client: EduAgentAPIClient) -> None:
    st.title("Ingestion Lab")
    st.subheader("Upload textbook or DOCX")
    file = st.file_uploader("Select file", type=["docx", "pdf"])
    grade = st.selectbox("Grade Level", defs.ui.GRADE_LEVELS)
    st.caption(
        "Subject tagging is inferred automatically by the ingestion workflow. "
        "Documents are initially stored with the 'general' subject label."
    )
    subject_value = SubjectArea.GENERAL.value
    if st.button("Start Ingestion") and file is not None:
        with st.spinner("Uploading to ingestion pipeline..."):
            result = client.upload_ingestion_document(
                file.name, file.getvalue(), subject_value, grade
            )
        if "error" in result:
            st.error(result["error"])
        else:
            st.success("Job created")
            st.json(result)

    st.markdown("---")
    st.subheader("Lookup Job Status")
    lookup_id = st.text_input("Quiz Job ID")
    if st.button("Fetch Job Detail") and lookup_id:
        with st.spinner("Fetching job info..."):
            detail = client.get_quiz_job(lookup_id)
        if "error" in detail:
            st.error(detail["error"])
        else:
            st.json(detail)
