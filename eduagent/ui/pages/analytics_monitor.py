from __future__ import annotations

import streamlit as st

from eduagent.defs import defs
from eduagent.ui.api_client import EduAgentAPIClient


def render(client: EduAgentAPIClient) -> None:
    st.title("Analytics Monitor")
    tab1, tab2, tab3 = st.tabs(
        ["Student Performance", "Class Analytics", "Mistakes"]
    )
    with tab1:
        student_id = st.text_input("Student ID")
        time_period = st.selectbox("Time Period", defs.ui.TIME_PERIODS)
        if st.button("Fetch Student Analytics") and student_id:
            result = client.get_performance_analytics(student_id, time_period)
            st.json(result)
    with tab2:
        class_id = st.text_input("Class ID")
        time_period = st.selectbox(
            "Class Time Period",
            defs.ui.TIME_PERIODS,
            key="class_period",
        )
        if st.button("Fetch Class Analytics") and class_id:
            result = client.get_class_analytics(class_id, time_period)
            st.json(result)
    with tab3:
        student = st.text_input("Student (mistake analysis)")
        subject = st.selectbox("Subject", defs.ui.SUBJECTS)
        if st.button("Analyze Mistakes") and student:
            result = client.analyze_mistakes(student, subject)
            st.json(result)
