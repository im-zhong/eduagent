from __future__ import annotations

import html
import json
import threading
from queue import Queue
from typing import TYPE_CHECKING, Any, TypedDict, cast
from uuid import uuid4

import streamlit as st

from eduagent.ui.api_client import EduAgentAPIClient
from eduagent.ui.react_stream import AgentStreamState, create_stream_state

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


def json_text_area(label: str, key: str) -> list[dict[str, Any]]:
    raw = st.text_area(label, key=key, height=180)
    if not raw.strip():
        return []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        st.error(f"JSON 解析错误: {exc}")
        return []
    if isinstance(data, list):
        filtered: list[dict[str, Any]] = [
            cast(dict[str, Any], item)
            for item in cast(list[Any], data)
            if isinstance(item, dict)
        ]
        if not filtered:
            st.warning("JSON 列表不包含对象。")
        return filtered
    st.warning("需要 JSON 列表，已忽略输入。")
    return []


def format_ingestion_label(job_id: str, detail: dict[str, Any]) -> str:
    subject = detail.get("subject") or "未知学科"
    grade = detail.get("grade_level") or "-"
    return f"{job_id} | {subject} | {grade}"


def ensure_reference_style() -> None:
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


def reference_icons_html(references: list[dict[str, Any]]) -> str:
    if not references:
        return "<span style='color:#6b7280;'>暂无参考资料</span>"
    icons: list[str] = []
    for idx, ref in enumerate(references, start=1):
        raw_text = str(ref.get("text") or "").strip()
        snippet = raw_text[:REFERENCE_PREVIEW_LIMIT]
        if len(raw_text) > REFERENCE_PREVIEW_LIMIT:
            snippet += "..."
        tooltip = html.escape(snippet.replace("\n", " ").strip() or "空白", quote=True)
        chunk_label = ref.get("metadata", {}).get("chunk_index")
        label = html.escape(str(chunk_label if chunk_label is not None else idx))
        icons.append(
            f"<span class='ref-icon' data-tooltip='{tooltip}'>&#128206;{label}</span>"
        )
    return "".join(icons)


def load_ingestion_catalog(
    client: EduAgentAPIClient, *, refresh: bool = False
) -> list[dict[str, Any]]:
    existing = st.session_state.get(INGESTION_CACHE_KEY)
    cache: dict[str, Any]
    if isinstance(existing, dict) and "items" in existing:
        cache = cast(dict[str, Any], existing)
    else:
        cache = {"items": []}
    if refresh or not cache["items"]:
        with st.spinner("正在获取已完成的笔记本..."):
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
    return cast(list[dict[str, Any]], cache["items"])


def filter_ingestion_items(
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


def render_ingestion_selector(items: list[dict[str, Any]]) -> str | None:
    if not items:
        st.info("暂无已完成的解析任务，请先在“数据解析”上传笔记本。")
        return None
    filter_value = st.text_input(
        "筛选笔记本（学科、年级、文件名）",
        key="agent_ingestion_filter",
    )
    filtered = filter_ingestion_items(items, filter_value)
    if not filtered:
        st.warning("没有符合筛选条件的笔记本。")
        return None
    job_map = {cast(str, item.get("job_id")): item for item in filtered}
    options = list(job_map.keys())
    selected_job = st.selectbox(
        "可用笔记本",
        options=options,
        format_func=lambda job: format_ingestion_label(job, job_map[job]),
        key="agent_selected_ingestion",
    )
    selection = job_map.get(selected_job)
    if selection:
        st.caption(
            f"来源: {selection.get('source_filename') or '未知'} | 文档任务: {selection.get('document_job_id') or 'n/a'}"
        )
    return selected_job


def get_agent_stream_state() -> AgentStreamState:
    existing = st.session_state.get(AGENT_STREAM_STATE_KEY)
    if isinstance(existing, dict):
        return cast(AgentStreamState, existing)
    state: AgentStreamState = AgentStreamState(events=[], status="idle")
    st.session_state[AGENT_STREAM_STATE_KEY] = state
    return state


def get_rag_stream_state() -> AgentStreamState:
    existing = st.session_state.get(RAG_STREAM_STATE_KEY)
    if isinstance(existing, dict):
        return cast(AgentStreamState, existing)
    state: AgentStreamState = AgentStreamState(events=[], status="idle")
    st.session_state[RAG_STREAM_STATE_KEY] = state
    return state


def get_rag_chat_history() -> list[dict[str, Any]]:
    history = st.session_state.get(RAG_CHAT_HISTORY_KEY)
    if isinstance(history, list):
        return cast(list[dict[str, Any]], history)
    st.session_state[RAG_CHAT_HISTORY_KEY] = []
    return []


def reset_rag_chat_session() -> None:
    st.session_state.pop(RAG_CHAT_HISTORY_KEY, None)
    st.session_state.pop(RAG_STREAM_STATE_KEY, None)


def start_agent_stream(
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


def start_rag_chat_stream(
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


def render_agent_stream(state: AgentStreamState) -> None:
    st.subheader("实时执行流")
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
        placeholder.info("代理正在启动...")
    else:
        placeholder.info("代理空闲，提交指令以开始流式执行。")


def _render_status_section(
    placeholders: AgentPlaceholderMap,
    status: str,
    phase: str,
    payload: dict[str, Any],
    final_result: dict[str, Any] | None,
) -> None:
    status_placeholder = placeholders["status"]
    if status == "error":
        status_placeholder.error(payload.get("message", "代理执行失败"))
    elif status == "completed":
        status_placeholder.success("代理已完成，最终测验载荷如下。")
        final_payload = final_result or payload
        placeholders["final"].json(final_payload)
    else:
        status_placeholder.info(f"阶段：{phase}")


def _render_agent_details(
    payload: dict[str, Any],
    placeholders: AgentPlaceholderMap,
) -> None:
    placeholders["thought"].markdown(f"**思考**: {payload.get('thought') or '[暂无]'}")
    placeholders["action"].markdown(f"**动作**: {payload.get('action') or '[待执行]'}")
    placeholders["observation"].markdown(
        f"**观察**: {payload.get('observation') or '[尚无]'}"
    )
    todo_items = [
        str(item)
        for item in cast(list[Any] | None, payload.get("todo")) or []
        if str(item).strip()
    ]
    if todo_items:
        todo_markdown = "\n".join(f"- {item}" for item in todo_items)
        placeholders["todo"].markdown(f"**待办列表**\n{todo_markdown}")
    else:
        placeholders["todo"].markdown("**待办列表**\n_暂无_")
    references = cast(list[dict[str, Any]], payload.get("references") or [])
    placeholders["references"].markdown(
        reference_icons_html(references), unsafe_allow_html=True
    )
    tool_usage = cast(dict[str, Any], payload.get("tool_usage") or {})
    if tool_usage:
        usage_text = " / ".join(f"{key}:{value}" for key, value in tool_usage.items())
        placeholders["tools"].markdown(f"**工具使用**: {usage_text}")
    else:
        placeholders["tools"].markdown("**工具使用**: 无")


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
        "**事件日志**\n" + "\n".join(f"- {line}" for line in log_lines)
    )


def render_rag_stream(state: AgentStreamState) -> None:
    st.subheader("代理状态")
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
        placeholders["status"].error(payload.get("message") or "RAG 代理错误")
    elif status == "completed":
        placeholders["status"].success("代理完成回答")
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
        reference_icons_html(references), unsafe_allow_html=True
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
            reference_icons_html(final_refs), unsafe_allow_html=True
        )
        final_history = final_payload.get("history")
        if isinstance(final_history, list):
            st.session_state[RAG_CHAT_HISTORY_KEY] = cast(
                list[dict[str, Any]], final_history
            )
