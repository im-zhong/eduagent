from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from eduagent.quiz.scoring import QuizScoringResult, QuizScoringService


@dataclass
class FakeLLMResponse:
    content: str


class FakeLLM:
    def __init__(self, content: str) -> None:
        self.content = content

    def invoke(self, messages: list[Any]) -> FakeLLMResponse:
        assert messages
        return FakeLLMResponse(self.content)


EXPECTED_QUALITY = 0.8


def test_quiz_scoring_service_parses_response() -> None:
    llm = FakeLLM(
        '{"quality":0.8,"rationale":"Strong coverage","suggestions":["Add variety"]}'
    )
    service = QuizScoringService(llm=llm)
    result = service.score({"questions": [{"prompt": "Q1"}]})
    assert isinstance(result, QuizScoringResult)
    assert result.quality == EXPECTED_QUALITY
    assert "Strong" in result.rationale
    assert result.suggestions == ["Add variety"]


def test_quiz_scoring_service_handles_invalid_json() -> None:
    llm = FakeLLM("not-json")
    service = QuizScoringService(llm=llm)
    result = service.score({"questions": []})
    assert result.quality == 0.0
    assert result.suggestions
