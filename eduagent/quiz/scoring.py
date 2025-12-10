from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Protocol, cast

from langchain_core.messages import HumanMessage, SystemMessage

from eduagent.llm.factory import get_chat_model


@dataclass
class QuizScoringResult:
    quality: float
    rationale: str
    suggestions: list[str]


class SupportsLLM(Protocol):
    def invoke(self, messages: list[object]) -> object: ...


class QuizScoringService:
    """Scores generated quizzes using an LLM based rubric."""

    def __init__(self, llm: SupportsLLM | None = None) -> None:
        self.llm = cast(SupportsLLM, llm or get_chat_model(temperature=0.2))

    def score(self, quiz_payload: dict[str, Any]) -> QuizScoringResult:
        questions_raw = cast(list[Any], quiz_payload.get("questions") or [])
        questions = [
            cast(dict[str, Any], question)
            for question in questions_raw
            if isinstance(question, dict)
        ]
        messages: list[object] = [
            SystemMessage(
                content=(
                    "You are an expert educator. Evaluate the provided quiz questions. "
                    "Return JSON with fields: quality (0-1), rationale, suggestions."
                )
            ),
            HumanMessage(
                content=json.dumps(
                    {
                        "questions": questions,
                        "rules": quiz_payload.get("rules", {}),
                    }
                )
            ),
        ]
        response = self.llm.invoke(messages)
        content = getattr(response, "content", "") if response else ""
        try:
            parsed = json.loads(content)
            quality = float(parsed.get("quality", 0.0))
            rationale = parsed.get("rationale", "")
            suggestions_raw = parsed.get("suggestions", [])
            if isinstance(suggestions_raw, Sequence) and not isinstance(
                suggestions_raw, (str, bytes)
            ):
                suggestions_seq = cast(Sequence[Any], suggestions_raw)
                suggestions = [str(item) for item in suggestions_seq]
            else:
                suggestions = [str(suggestions_raw)]
        except Exception:
            quality = 0.0
            rationale = "LLM failed to provide structured feedback."
            suggestions = ["Review quiz manually."]
        quality = max(0.0, min(1.0, quality))
        return QuizScoringResult(
            quality=quality,
            rationale=rationale,
            suggestions=suggestions,
        )
