"""
Operations console for EduAgent.
Provides pages for ingestion, workflow execution, and analytics using the new quiz APIs.
"""

from __future__ import annotations

import html
import json
from typing import Any, cast

import streamlit as st

from eduagent.api.schemas import SubjectArea
from eduagent.defs import defs
from eduagent.quiz.enums import JobStatus, JobType
from eduagent.ui.api_client import EduAgentAPIClient

REFERENCE_PREVIEW_LIMIT = 200

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


def _get_tracked_ingestions() -> dict[str, dict[str, Any]]:
    key = "agent_ingestions"
    if key not in st.session_state:
        st.session_state[key] = {}
    return cast(dict[str, dict[str, Any]], st.session_state[key])


def _format_ingestion_label(job_id: str, detail: dict[str, Any]) -> str:
    subject = detail.get("subject") or "unknown"
    grade = detail.get("grade_level") or "-"
    return f"{job_id} | {subject} | {grade}"


def _ensure_reference_style() -> None:
    key = "_reference_style_loaded"
    if st.session_state.get(key):
        return
    st.markdown(
        """
        <style>
        .ref-icon {
            cursor: pointer;
            display: inline-block;
            margin-right: 0.3rem;
            font-size: 1.2rem;
            position: relative;
        }
        .ref-icon::after {
            content: attr(data-tooltip);
            position: absolute;
            bottom: 130%;
            left: 0;
            background: #111827;
            color: white;
            padding: 0.35rem 0.6rem;
            border-radius: 0.35rem;
            opacity: 0;
            pointer-events: none;
            transition: opacity 0.15s ease-in-out;
            width: 280px;
            max-width: 50vw;
            white-space: pre-wrap;
            font-size: 0.75rem;
            z-index: 10;
        }
        .ref-icon:hover::after {
            opacity: 0.92;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.session_state[key] = True


def _reference_icons_html(references: list[dict[str, Any]]) -> str:
    if not references:
        return "<span style='color:#6b7280;'>No references yet</span>"
    icons: list[str] = []
    for idx, ref in enumerate(references, start=1):
        raw_text = str(ref.get("text") or "").strip()
        snippet = raw_text[:REFERENCE_PREVIEW_LIMIT]
        if len(raw_text) > REFERENCE_PREVIEW_LIMIT:
            snippet += "..."
        tooltip = html.escape(snippet.replace("\n", " ").strip() or "empty", quote=True)
        chunk_label = ref.get("metadata", {}).get("chunk_index")
        label = html.escape(str(chunk_label if chunk_label is not None else idx))
        icons.append(
            f"<span class='ref-icon' data-tooltip='{tooltip}'>&#128206;{label}</span>"
        )
    return "".join(icons)


def _rerun_app() -> None:
    rerun = getattr(st, "rerun", None)
    if callable(rerun):
        rerun()
        return
    legacy_rerun = getattr(st, "experimental_rerun", None)
    if callable(legacy_rerun):
        legacy_rerun()


def _render_ingestion_form(
    client: EduAgentAPIClient, catalog: dict[str, dict[str, Any]]
) -> None:
    with st.form("agent_ingestion_form"):
        ingestion_input = st.text_input(
            "Add a completed ingestion job ID",
            key="agent_ingestion_input",
            placeholder="Example: 7ac26000-6b8a-4a37-b3e1-08b9380d4e74",
        )
        submitted = st.form_submit_button("Add notebook")
        if not submitted:
            return
        if not ingestion_input.strip():
            st.warning("Enter the job id before submitting.")
            return
        job_id = ingestion_input.strip()
        with st.spinner("Fetching job metadata..."):
            detail = client.get_quiz_job(job_id)
        if "error" in detail:
            st.error(detail["error"])
            return
        if str(detail.get("job_type")) != JobType.INGESTION.value:
            st.error("The job is not an ingestion record.")
            return
        if str(detail.get("status")) != JobStatus.COMPLETED.value:
            st.warning("Job has not completed yet.")
            return
        catalog[job_id] = {
            "subject": detail.get("subject"),
            "grade_level": detail.get("grade_level"),
            "result": detail.get("result", {}),
        }
        st.success("Notebook added to the list.")


def _render_ingestion_selector(catalog: dict[str, dict[str, Any]]) -> str | None:
    if not catalog:
        st.info("No notebooks stored yet. Add a completed ingestion job first.")
        return None
    job_ids = list(catalog.keys())
    selected_job = st.selectbox(
        "Tracked notebooks",
        options=job_ids,
        format_func=lambda job: _format_ingestion_label(job, catalog[job]),
        key="agent_selected_ingestion",
    )
    if st.button("Remove selected notebook") and selected_job in catalog:
        catalog.pop(selected_job, None)
        st.success("Removed.")
        _rerun_app()
    return selected_job


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


def page_agent_workflow(client: EduAgentAPIClient) -> None:
    st.title("ReAct Agent Workflow (LangGraph)")
    st.caption(
        "Pick a completed ingestion job, enter a Chinese instruction, and watch the agent's reasoning,"
        " tool usage, todo list, and references streamed via SSE."
    )
    _ensure_reference_style()
    catalog = _get_tracked_ingestions()
    _render_ingestion_form(client, catalog)
    selected_job = _render_ingestion_selector(catalog)

    prompt = st.text_area(
        "Agent instruction (write in Chinese)",
        key="agent_prompt",
        height=180,
        placeholder=(
            "Example: Generate five multiple-choice questions covering the key knowledge from this notebook."
        ),
    )
    st.markdown("---")
    run_container = st.container()
    if st.button(
        "Start ReAct agent",
        type="primary",
        disabled=not (selected_job and prompt.strip()),
    ):
        if selected_job is None:
            st.error("Please pick a notebook first.")
        else:
            with run_container:
                _execute_agent_stream(client, selected_job, prompt.strip())


def _execute_agent_stream(
    client: EduAgentAPIClient, ingestion_job_id: str, prompt: str
) -> None:
    st.subheader("Live execution stream")
    status_placeholder = st.empty()
    state_cols = st.columns(3)
    thought_placeholder = state_cols[0].empty()
    action_placeholder = state_cols[1].empty()
    observation_placeholder = state_cols[2].empty()
    plan_and_references = st.columns((1.3, 1.3, 1))
    todo_placeholder = plan_and_references[0].empty()
    reference_placeholder = plan_and_references[1].empty()
    tool_placeholder = plan_and_references[2].empty()
    log_placeholder = st.empty()
    final_placeholder = st.empty()

    status_placeholder.info("Agent is booting...")
    log_lines: list[str] = []
    for event in client.stream_quiz_workflow(ingestion_job_id, prompt):
        phase = str(event.get("phase") or "")
        payload = cast(dict[str, Any], event.get("payload") or {})
        if phase == "error":
            status_placeholder.error(payload.get("message", "Agent execution failed"))
            break
        if phase == "final":
            status_placeholder.success(
                "Agent finished. Final quiz payload is shown below."
            )
            final_placeholder.json(payload)
            break
        status_placeholder.info(f"Phase: {phase}")
        thought_placeholder.markdown(
            f"**Thought**: {payload.get('thought') or '[none]'}"
        )
        action_placeholder.markdown(
            f"**Action**: {payload.get('action') or '[pending]'}"
        )
        observation_placeholder.markdown(
            f"**Observation**: {payload.get('observation') or '[none yet]'}"
        )
        todo_items = [
            str(item)
            for item in cast(list[Any] | None, payload.get("todo")) or []
            if str(item).strip()
        ]
        if todo_items:
            todo_markdown = "\n".join(f"- {item}" for item in todo_items)
            todo_placeholder.markdown(f"**Todo list**\n{todo_markdown}")
        else:
            todo_placeholder.markdown("**Todo list**\n_none_")
        references = cast(list[dict[str, Any]], payload.get("references") or [])
        reference_placeholder.markdown(
            _reference_icons_html(references), unsafe_allow_html=True
        )
        tool_usage = cast(dict[str, Any], payload.get("tool_usage") or {})
        if tool_usage:
            usage_text = " / ".join(
                f"{key}:{value}" for key, value in tool_usage.items()
            )
            tool_placeholder.markdown(f"**Tool usage**: {usage_text}")
        else:
            tool_placeholder.markdown("**Tool usage**: none")
        excerpt = (
            payload.get("thought")
            or payload.get("observation")
            or payload.get("message")
            or ""
        )
        log_lines.append(f"[{phase}] {excerpt}")
        log_placeholder.markdown(
            "**Event log**\n" + "\n".join(f"- {line}" for line in log_lines[-8:])
        )


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
    "Agent Workflow": page_agent_workflow,
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
