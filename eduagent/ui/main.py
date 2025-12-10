"""
Operations console for EduAgent.
Provides pages for ingestion, workflow execution, and analytics using the new quiz APIs.
"""

from __future__ import annotations

import json
from typing import Any, cast

import streamlit as st

from eduagent.api.schemas import SubjectArea
from eduagent.defs import defs
from eduagent.ui.api_client import EduAgentAPIClient

DEFAULT_API_URL = "http://api.eduagent:8000"


def _load_api_client() -> EduAgentAPIClient:
    if "api_client" not in st.session_state:
        st.session_state.api_client = EduAgentAPIClient(DEFAULT_API_URL)
    return st.session_state.api_client


def _configure_sidebar(client: EduAgentAPIClient) -> None:
    st.sidebar.header("API Configuration")
    stored_url = st.session_state.get("api_base_url") or client.base_url
    base_url = st.sidebar.text_input(
        "Service Base URL",
        value=stored_url,
    )
    token = st.sidebar.text_area(
        "Service JWT",
        value=st.session_state.get("service_jwt", ""),
        height=140,
        help="Paste the signed service token from Next.js.",
    )
    if st.sidebar.button("Apply Settings"):
        effective_base = base_url or DEFAULT_API_URL
        st.session_state.api_base_url = effective_base
        st.session_state.service_jwt = token
        client.configure(effective_base, token or None)
        st.sidebar.success("Configuration updated.")


def _json_text_area(label: str, key: str) -> list[dict[str, Any]]:
    raw = st.text_area(label, key=key, height=180)
    if not raw.strip():
        return []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        st.error(f"JSON parse error: {exc}")
        return []
    if isinstance(data, list):
        filtered: list[dict[str, Any]] = [
            cast(dict[str, Any], item)
            for item in cast(list[Any], data)
            if isinstance(item, dict)
        ]
        if not filtered:
            st.warning("JSON list does not contain any objects.")
        return filtered
    st.warning("Expecting a JSON list. Ignoring input.")
    return []


def page_overview(client: EduAgentAPIClient) -> None:
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


def page_ingestion_lab(client: EduAgentAPIClient) -> None:
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


def page_workflow_runner(client: EduAgentAPIClient) -> None:
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


def page_async_pipeline(client: EduAgentAPIClient) -> None:
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
    answers = _json_text_area(
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


def page_scoring_studio(client: EduAgentAPIClient) -> None:
    st.title("Scoring Studio")
    quiz_job_id = st.text_input("Quiz Job ID for Scoring")
    questions = _json_text_area("Questions JSON", "score_questions")
    rules_text = st.text_area(
        "Optional Rules JSON",
        height=120,
        placeholder='{"allow_distractors": true}',
    )
    rules: dict[str, Any] | None = None
    if rules_text.strip():
        try:
            parsed = json.loads(rules_text)
            if isinstance(parsed, dict):
                rules = cast(dict[str, Any], parsed)
            else:
                st.warning("Rules JSON should be an object/dict")
        except json.JSONDecodeError as exc:
            st.warning(f"Rules JSON invalid: {exc}")
    if st.button("Score Quiz") and quiz_job_id and questions:
        with st.spinner("Requesting scoring job..."):
            response = client.request_quiz_scoring(quiz_job_id, questions, rules)
        st.json(response)


def page_analytics(client: EduAgentAPIClient) -> None:
    st.title("Analytics Monitor")
    tab1, tab2, tab3 = st.tabs(["Student Performance", "Class Analytics", "Mistakes"])
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


PAGE_HANDLERS = {
    "Overview": page_overview,
    "Ingestion Lab": page_ingestion_lab,
    "Workflow Runner": page_workflow_runner,
    "Async Pipeline": page_async_pipeline,
    "Scoring Studio": page_scoring_studio,
    "Analytics Monitor": page_analytics,
}


def main() -> None:
    st.set_page_config(
        page_title="EduAgent Operations Console",
        page_icon=defs.ui.PAGE_ICON,
        layout="wide",
    )
    st.sidebar.title("EduAgent Console")
    client = _load_api_client()
    _configure_sidebar(client)
    st.sidebar.markdown("---")
    page_name = st.sidebar.radio("Pages", defs.ui.TEACHER_NAV_OPTIONS)
    handler = PAGE_HANDLERS.get(page_name, page_overview)
    handler(client)


if __name__ == "__main__":
    main()
