from __future__ import annotations

import json

import streamlit as st

from eduagent.ui import common
from eduagent.ui.api_client import EduAgentAPIClient


def render(client: EduAgentAPIClient) -> None:
    st.title("Async Quiz Pipeline")
    st.subheader("Generation Job")
    ingestion_job = st.text_input("Ingestion Job ID", key="async_ingestion")
    col1, col2 = st.columns(2)
    subject = col1.text_input("Subject Override", "")
    query = col2.text_input("Additional Query/Context", "")
    rules_default = {
        "total_questions": 5,
        "include_explanations": True,
        "allow_distractors": True,
    }
    rules_text = st.text_area(
        "Quiz Rules (JSON)",
        value=json.dumps(rules_default, indent=2),
        height=160,
    )
    if st.button("Queue Generation Job") and ingestion_job:
        try:
            quiz_rules = json.loads(rules_text)
        except json.JSONDecodeError as exc:
            st.error(f"Invalid JSON: {exc}")
        else:
            with st.spinner("Submitting generation job..."):
                result = client.request_quiz_generation(
                    ingestion_job,
                    subject or None,
                    query or None,
                    quiz_rules,
                )
            st.json(result)

    st.markdown("---")
    st.subheader("Evaluation Job")
    quiz_job_id = st.text_input("Quiz Job ID", key="eval_quiz_job")
    answers = common.json_text_area(
        "Answer Sheet (JSON list of {question_id, answer})", "eval_answers"
    )
    if st.button("Queue Evaluation") and quiz_job_id and answers:
        with st.spinner("Submitting evaluation job..."):
            response = client.request_quiz_evaluation(quiz_job_id, answers)
        st.json(response)

    st.markdown("---")
    st.subheader("Job Monitor")
    monitor_id = st.text_input("Job ID to monitor")
    if st.button("Refresh Status") and monitor_id:
        detail = client.get_quiz_job(monitor_id)
        st.json(detail)
