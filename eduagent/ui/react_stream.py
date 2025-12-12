from __future__ import annotations

from queue import Empty, Queue
from typing import Any, TypedDict, cast

AgentEvent = dict[str, Any]


class AgentStreamState(TypedDict, total=False):
    run_id: str
    queue: Queue[AgentEvent]
    events: list[AgentEvent]
    status: str
    result: dict[str, Any] | None
    error: str | None
    ingestion_job_id: str
    prompt: str


def create_stream_state(
    run_id: str, event_queue: Queue[AgentEvent]
) -> AgentStreamState:
    return AgentStreamState(
        run_id=run_id,
        queue=event_queue,
        events=[],
        status="running",
        result=None,
        error=None,
    )


def drain_stream_queue(state: AgentStreamState) -> None:
    event_queue = state.get("queue")
    if not isinstance(event_queue, Queue):
        return
    while True:
        try:
            event = event_queue.get_nowait()
        except Empty:
            break
        apply_event(state, event)


def apply_event(state: AgentStreamState, event: AgentEvent) -> None:
    events = state.setdefault("events", [])
    events.append(event)
    phase = str(event.get("phase") or "")
    payload = cast(dict[str, Any], event.get("payload") or {})
    if phase == "error":
        state["status"] = "error"
        state["error"] = payload.get("message")
    elif phase == "final":
        state["status"] = "completed"
        state["result"] = payload
    else:
        state["status"] = "running"
