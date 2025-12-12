from __future__ import annotations

from queue import Queue

from eduagent.ui.react_stream import create_stream_state, drain_stream_queue

EXPECTED_FINAL_EVENTS = 2


def test_drain_stream_queue_records_events() -> None:
    event_queue: Queue[dict[str, object]] = Queue()
    event_queue.put({"phase": "plan", "payload": {"thought": "collect notes"}})
    event_queue.put(
        {"phase": "final", "payload": {"questions": [{"prompt": "Q1"}], "answers": []}}
    )
    state = create_stream_state("run-1", event_queue)

    drain_stream_queue(state)

    events = state.get("events") or []
    assert len(events) == EXPECTED_FINAL_EVENTS
    assert state.get("status") == "completed"
    assert state.get("result") == {
        "questions": [{"prompt": "Q1"}],
        "answers": [],
    }


def test_drain_stream_queue_handles_error() -> None:
    event_queue: Queue[dict[str, object]] = Queue()
    event_queue.put({"phase": "error", "payload": {"message": "boom"}})
    state = create_stream_state("run-2", event_queue)

    drain_stream_queue(state)

    assert state.get("status") == "error"
    assert state.get("error") == "boom"
