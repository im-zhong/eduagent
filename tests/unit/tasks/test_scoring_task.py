from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from eduagent.quiz.enums import JobStatus
from eduagent.tasks import quiz as quiz_tasks


@dataclass
class FakeScore:
    quality: float
    rationale: str
    suggestions: list[str]


QUALITY_SCORE = 0.75


class FakeScoringService:
    def score(
        self, payload: dict[str, Any]
    ) -> FakeScore:  # pragma: no cover - simple stub
        assert "questions" in payload
        return FakeScore(QUALITY_SCORE, "Good coverage", ["Add variety"])


def test_score_quiz_quality(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, Any]] = []

    async def fake_update(
        job_id: str,
        status: JobStatus,
        *,
        result: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> None:
        calls.append(
            {"job_id": job_id, "status": status, "result": result, "error": error}
        )

    monkeypatch.setattr(quiz_tasks, "_update_job_status", fake_update)
    monkeypatch.setattr(quiz_tasks, "QuizScoringService", lambda: FakeScoringService())

    payload = {"questions": [{"prompt": "Q1"}]}
    result = quiz_tasks.score_quiz_quality("job-123", payload)
    assert result["quality"] == QUALITY_SCORE
    assert calls[-1]["result"]["suggestions"] == ["Add variety"]
