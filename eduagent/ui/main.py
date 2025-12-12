"""
Operations console for EduAgent.
Provides pages for ingestion, workflow execution, and analytics using the new quiz APIs.
"""

from __future__ import annotations

import html
import json
import threading
from queue import Queue
from typing import TYPE_CHECKING, Any, TypedDict, cast
from uuid import uuid4

import streamlit as st

from eduagent.api.schemas import SubjectArea
from eduagent.defs import defs
from eduagent.ui.api_client import EduAgentAPIClient
from eduagent.ui.react_stream import (
    AgentStreamState,
    create_stream_state,
    drain_stream_queue,
)

if TYPE_CHECKING:
    from streamlit.delta_generator import DeltaGenerator
else:  # pragma: no cover
    DeltaGenerator = object

REFERENCE_PREVIEW_LIMIT = 200
INGESTION_CACHE_KEY = "agent_ingestion_cache"
AGENT_STREAM_STATE_KEY = "agent_stream_state"
RAG_STREAM_STATE_KEY = "rag_stream_state"
RAG_CHAT_HISTORY_KEY = "rag_chat_history"
AgentPlaceholderMap = dict[str, DeltaGenerator]


class _IngestionCache(TypedDict):
    items: list[dict[str, Any]]


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


def _load_ingestion_catalog(
    client: EduAgentAPIClient, *, refresh: bool = False
) -> list[dict[str, Any]]:
    existing = st.session_state.get(INGESTION_CACHE_KEY)
    cache: _IngestionCache
    if isinstance(existing, dict) and "items" in existing:
        cache = cast(_IngestionCache, existing)
    else:
        cache = {"items": []}
    if refresh or not cache["items"]:
        with st.spinner("Fetching completed ingestion notebooks..."):
            response = client.list_ingestion_jobs()
        if "error" in response:
            st.error(response["error"])
            items: list[dict[str, Any]] = []
        else:
            raw_items = cast(list[Any], response.get("items") or [])
            typed_items: list[dict[str, Any]] = [
                cast(dict[str, Any], obj) for obj in raw_items if isinstance(obj, dict)
            ]
            items = []
            for entry in typed_items:
                job_identifier = entry.get("job_id")
                if isinstance(job_identifier, str) and job_identifier:
                    items.append(entry)
        cache = {"items": items}
        st.session_state[INGESTION_CACHE_KEY] = cache
    return cache["items"]


def _filter_ingestion_items(
    items: list[dict[str, Any]], query: str | None
) -> list[dict[str, Any]]:
    if not query or not query.strip():
        return items
    needle = query.strip().lower()
    filtered: list[dict[str, Any]] = []
    for item in items:
        haystack = " ".join(
            str(value or "").lower()
            for value in (
                item.get("subject"),
                item.get("grade_level"),
                item.get("source_filename"),
                item.get("job_id"),
            )
        )
        if needle in haystack:
            filtered.append(item)
    return filtered


def _render_ingestion_selector(items: list[dict[str, Any]]) -> str | None:
    if not items:
        st.info(
            "No completed ingestion jobs available. Upload a notebook in Ingestion Lab first."
        )
        return None
    filter_value = st.text_input(
        "Filter notebooks (subject, grade, filename)",
        key="agent_ingestion_filter",
    )
    filtered = _filter_ingestion_items(items, filter_value)
    if not filtered:
        st.warning("No notebooks match the current filter.")
        return None
    job_map = {cast(str, item.get("job_id")): item for item in filtered}
    options = list(job_map.keys())
    selected_job = st.selectbox(
        "Available ingestion notebooks",
        options=options,
        format_func=lambda job: _format_ingestion_label(job, job_map[job]),
        key="agent_selected_ingestion",
    )
    selection = job_map.get(selected_job)
    if selection:
        st.caption(
            f"Source: {selection.get('source_filename') or 'unknown'} | Document job: {selection.get('document_job_id') or 'n/a'}"
        )
    return selected_job


def _get_agent_stream_state() -> AgentStreamState:
    existing = st.session_state.get(AGENT_STREAM_STATE_KEY)
    if isinstance(existing, dict):
        return cast(AgentStreamState, existing)
    state: AgentStreamState = AgentStreamState(events=[], status="idle")
    st.session_state[AGENT_STREAM_STATE_KEY] = state
    return state


def _get_rag_stream_state() -> AgentStreamState:
    existing = st.session_state.get(RAG_STREAM_STATE_KEY)
    if isinstance(existing, dict):
        return cast(AgentStreamState, existing)
    state: AgentStreamState = AgentStreamState(events=[], status="idle")
    st.session_state[RAG_STREAM_STATE_KEY] = state
    return state


def _get_rag_chat_history() -> list[dict[str, Any]]:
    history = st.session_state.get(RAG_CHAT_HISTORY_KEY)
    if isinstance(history, list):
        return cast(list[dict[str, Any]], history)
    st.session_state[RAG_CHAT_HISTORY_KEY] = []
    return []


def _reset_rag_chat_session() -> None:
    st.session_state.pop(RAG_CHAT_HISTORY_KEY, None)
    st.session_state.pop(RAG_STREAM_STATE_KEY, None)


def _start_agent_stream(
    client: EduAgentAPIClient, ingestion_job_id: str, prompt: str
) -> None:
    run_id = uuid4().hex
    event_queue: Queue[dict[str, Any]] = Queue()
    state = create_stream_state(run_id, event_queue)
    state["ingestion_job_id"] = ingestion_job_id
    state["prompt"] = prompt
    st.session_state[AGENT_STREAM_STATE_KEY] = state

    def _worker() -> None:
        for event in client.stream_quiz_workflow(ingestion_job_id, prompt):
            event_queue.put(event)
            phase = str(event.get("phase") or "")
            if phase in {"final", "error"}:
                break

    thread = threading.Thread(
        target=_worker, name=f"react-stream-{run_id}", daemon=True
    )
    thread.start()


def _start_rag_chat_stream(
    client: EduAgentAPIClient,
    ingestion_job_ids: list[str],
    history: list[dict[str, Any]],
    question: str,
) -> None:
    run_id = uuid4().hex
    event_queue: Queue[dict[str, Any]] = Queue()
    state = create_stream_state(run_id, event_queue)
    state["ingestion_job_id"] = ",".join(ingestion_job_ids)
    state["prompt"] = question
    st.session_state[RAG_STREAM_STATE_KEY] = state

    def _worker() -> None:
        for event in client.stream_rag_chat(ingestion_job_ids, history, question):
            event_queue.put(event)
            phase = str(event.get("phase") or "")
            if phase in {"error", "final"}:
                break

    thread = threading.Thread(target=_worker, name=f"rag-stream-{run_id}", daemon=True)
    thread.start()


def _render_agent_stream(state: AgentStreamState) -> None:
    st.subheader("Live execution stream")
    status_placeholder = st.empty()
    state_cols = st.columns(3)
    plan_and_references = st.columns((1.3, 1.3, 1))
    placeholders: AgentPlaceholderMap = {
        "status": status_placeholder,
        "thought": state_cols[0].empty(),
        "action": state_cols[1].empty(),
        "observation": state_cols[2].empty(),
        "todo": plan_and_references[0].empty(),
        "references": plan_and_references[1].empty(),
        "tools": plan_and_references[2].empty(),
        "log": st.empty(),
        "final": st.empty(),
    }

    events = list(state.get("events") or [])
    status = state.get("status") or "idle"
    if status == "running":
        _schedule_agent_autorefresh()

    if not events:
        _render_idle_stream(status, placeholders["status"])
        return

    last_event = events[-1]
    phase = str(last_event.get("phase") or "")
    payload = cast(dict[str, Any], last_event.get("payload") or {})
    _render_status_section(
        placeholders,
        status,
        phase,
        payload,
        state.get("result"),
    )
    _render_agent_details(payload, placeholders)
    _render_agent_log(events, placeholders["log"])


def _schedule_agent_autorefresh() -> None:
    autorefresh = getattr(st, "autorefresh", None)
    if callable(autorefresh):
        autorefresh(interval=1500, key="agent_stream_autorefresh")


def _render_idle_stream(status: str, placeholder: DeltaGenerator) -> None:
    if status == "running":
        placeholder.info("Agent is booting...")
    else:
        placeholder.info("Agent idle. Submit a prompt to start streaming.")


def _render_status_section(
    placeholders: AgentPlaceholderMap,
    status: str,
    phase: str,
    payload: dict[str, Any],
    final_result: dict[str, Any] | None,
) -> None:
    status_placeholder = placeholders["status"]
    if status == "error":
        status_placeholder.error(payload.get("message", "Agent execution failed"))
    elif status == "completed":
        status_placeholder.success("Agent finished. Final quiz payload is shown below.")
        final_payload = final_result or payload
        placeholders["final"].json(final_payload)
    else:
        status_placeholder.info(f"Phase: {phase}")


def _render_agent_details(
    payload: dict[str, Any],
    placeholders: AgentPlaceholderMap,
) -> None:
    placeholders["thought"].markdown(
        f"**Thought**: {payload.get('thought') or '[none]'}"
    )
    placeholders["action"].markdown(
        f"**Action**: {payload.get('action') or '[pending]'}"
    )
    placeholders["observation"].markdown(
        f"**Observation**: {payload.get('observation') or '[none yet]'}"
    )
    todo_items = [
        str(item)
        for item in cast(list[Any] | None, payload.get("todo")) or []
        if str(item).strip()
    ]
    if todo_items:
        todo_markdown = "\n".join(f"- {item}" for item in todo_items)
        placeholders["todo"].markdown(f"**Todo list**\n{todo_markdown}")
    else:
        placeholders["todo"].markdown("**Todo list**\n_none_")
    references = cast(list[dict[str, Any]], payload.get("references") or [])
    placeholders["references"].markdown(
        _reference_icons_html(references), unsafe_allow_html=True
    )
    tool_usage = cast(dict[str, Any], payload.get("tool_usage") or {})
    if tool_usage:
        usage_text = " / ".join(f"{key}:{value}" for key, value in tool_usage.items())
        placeholders["tools"].markdown(f"**Tool usage**: {usage_text}")
    else:
        placeholders["tools"].markdown("**Tool usage**: none")


def _render_agent_log(
    events: list[dict[str, Any]], log_placeholder: DeltaGenerator
) -> None:
    def _log_entry(event: dict[str, Any]) -> str:
        phase = str(event.get("phase") or "")
        payload = cast(dict[str, Any], event.get("payload") or {})
        excerpt = (
            payload.get("thought")
            or payload.get("observation")
            or payload.get("message")
            or ""
        )
        return f"[{phase}] {excerpt}"

    log_lines = [_log_entry(evt) for evt in events[-8:]]
    log_placeholder.markdown(
        "**Event log**\n" + "\n".join(f"- {line}" for line in log_lines)
    )


def _render_rag_stream(state: AgentStreamState) -> None:
    st.subheader("Agent 状态")
    placeholders: AgentPlaceholderMap = {
        "status": st.empty(),
        "todo": st.empty(),
        "references": st.empty(),
        "answer": st.empty(),
        "log": st.empty(),
    }
    events = list(state.get("events") or [])
    status = state.get("status") or "idle"
    if status == "running":
        _schedule_agent_autorefresh()
    if not events:
        placeholders["status"].info("等待提问")
        return
    latest = events[-1]
    phase = str(latest.get("phase") or "")
    payload = cast(dict[str, Any], latest.get("payload") or {})
    if status == "error":
        placeholders["status"].error(payload.get("message") or "RAG agent error")
    elif status == "completed":
        placeholders["status"].success("Agent 完成回答")
    else:
        placeholders["status"].info(f"阶段：{phase}")
    todo_items = [
        str(item)
        for item in cast(list[Any] | None, payload.get("todo")) or []
        if str(item).strip()
    ]
    if todo_items:
        placeholders["todo"].markdown(
            "**进行中的任务**\n" + "\n".join(f"- {item}" for item in todo_items)
        )
    else:
        placeholders["todo"].markdown("**进行中的任务**\n- (空)")
    references = cast(list[dict[str, Any]], payload.get("references") or [])
    placeholders["references"].markdown(
        _reference_icons_html(references), unsafe_allow_html=True
    )
    answer = payload.get("answer")
    if isinstance(answer, str) and answer.strip():
        placeholders["answer"].markdown(f"**回答草稿**\n\n{answer}")
    final_payload = state.get("result") or {}
    if final_payload:
        final_answer = final_payload.get("answer")
        if isinstance(final_answer, str):
            placeholders["answer"].markdown(f"**最终回答**\n\n{final_answer}")
        final_refs = cast(list[dict[str, Any]], final_payload.get("references") or [])
        placeholders["references"].markdown(
            _reference_icons_html(final_refs), unsafe_allow_html=True
        )
        final_history = final_payload.get("history")
        if isinstance(final_history, list):
            st.session_state[RAG_CHAT_HISTORY_KEY] = cast(
                list[dict[str, Any]], final_history
            )
    _render_agent_log(events, placeholders["log"])


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
    stream_state = _get_agent_stream_state()
    drain_stream_queue(stream_state)
    control_cols = st.columns([3, 1])
    with control_cols[1]:
        refresh_clicked = st.button("Refresh notebooks", key="agent_refresh")
    catalog_items = _load_ingestion_catalog(client, refresh=refresh_clicked)
    selected_job = _render_ingestion_selector(catalog_items)

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
            _start_agent_stream(client, selected_job, prompt.strip())
            rerun = getattr(st, "experimental_rerun", None)
            if callable(rerun):
                rerun()

    _render_agent_stream(stream_state)


def page_rag_chat(client: EduAgentAPIClient) -> None:
    st.title("LangGraph RAG Chat")
    st.caption(
        "选择一个或多个已完成的笔记本，使用中文提问，实时查看助教的检索与回答过程。"
    )
    _ensure_reference_style()
    stream_state = _get_rag_stream_state()
    drain_stream_queue(stream_state)
    control_cols = st.columns([3, 1, 1])
    with control_cols[1]:
        refresh_clicked = st.button("刷新笔记本", key="rag_refresh")
    with control_cols[2]:
        if st.button("清空对话", key="rag_reset"):
            _reset_rag_chat_session()
            stream_state = _get_rag_stream_state()
    catalog_items = _load_ingestion_catalog(client, refresh=refresh_clicked)
    if catalog_items:
        job_map = {cast(str, item["job_id"]): item for item in catalog_items}
        selected_jobs = st.multiselect(
            "选择知识库笔记",
            options=list(job_map.keys()),
            default=st.session_state.get("rag_selected_jobs") or [],
            format_func=lambda job: _format_ingestion_label(job, job_map[job]),
        )
        st.session_state["rag_selected_jobs"] = selected_jobs
    else:
        selected_jobs = []
    st.markdown("---")
    history = _get_rag_chat_history()
    for turn in history:
        role = "assistant" if turn.get("role") == "assistant" else "user"
        with st.chat_message(role):
            st.markdown(turn.get("content") or "")
    question = st.chat_input("请输入中文问题")
    if question:
        if not selected_jobs:
            st.warning("请至少选择一个已完成的笔记本。")
        else:
            prior_history = history.copy()
            updated_history = [*history, {"role": "user", "content": question}]
            st.session_state[RAG_CHAT_HISTORY_KEY] = updated_history
            _start_rag_chat_stream(client, selected_jobs, prior_history, question)
            rerun = getattr(st, "experimental_rerun", None)
            if callable(rerun):
                rerun()
    st.markdown("---")
    _render_rag_stream(stream_state)


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
    "RAG Chat": page_rag_chat,
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
