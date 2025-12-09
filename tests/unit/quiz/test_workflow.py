from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from eduagent.documents.services import EmbeddingBackend
from eduagent.quiz.workflow import QuizGenerationWorkflow, QuizWorkflowConfig


class FakeVectorStore:
    def __init__(self, hits: list[dict[str, Any]]) -> None:
        self.hits = hits

    def search(
        self,
        _embedding: list[float],
        limit: int = 5,
        _expr: str | None = None,
    ) -> list[dict[str, Any]]:
        return self.hits[:limit]


@dataclass
class FakeLLMResponse:
    content: str


class FakeLLM:
    def __init__(self, response: str) -> None:
        self.response = response

    def invoke(self, _messages: list[Any]) -> FakeLLMResponse:
        return FakeLLMResponse(content=self.response)


class TestEmbeddingBackend(EmbeddingBackend):
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[float(idx)] * 3 for idx, _ in enumerate(texts, start=1)]

    def embed_query(self, text: str) -> list[float]:
        _ = text
        return [1.0, 1.0, 1.0]


def test_quiz_workflow_generates_questions() -> None:
    hits = [
        {"text": "Photosynthesis requires sunlight."},
        {"text": "Chlorophyll captures light energy."},
    ]
    llm = FakeLLM(
        '[{"prompt":"Explain photosynthesis","answer":"Plants convert light."}]'
    )
    workflow = QuizGenerationWorkflow(
        QuizWorkflowConfig(
            vector_store=FakeVectorStore(hits),  # type: ignore[arg-type]
            embedder=TestEmbeddingBackend(),
            llm=llm,
        )
    )

    result = workflow.run("biology photosynthesis")

    assert "questions" in result
    assert len(result.get("questions") or []) == 1
    evaluation = result.get("evaluation") or {}
    assert evaluation.get("approved") == 1


def test_quiz_workflow_handles_invalid_llm_output() -> None:
    hits = [{"text": "The Ming dynasty built a vast navy."}]
    llm = FakeLLM("not-json")
    workflow = QuizGenerationWorkflow(
        QuizWorkflowConfig(
            vector_store=FakeVectorStore(hits),  # type: ignore[arg-type]
            embedder=TestEmbeddingBackend(),
            llm=llm,
        )
    )

    result = workflow.run("history ming")

    assert len(result.get("questions") or []) == 1
    answers = result.get("answers") or []
    assert answers[0]["is_correct"] is True


def test_quiz_workflow_revision_loop() -> None:
    hits = [{"text": "Short context."}]

    class ShortAnswerLLM(FakeLLM):
        def invoke(self, _messages: list[Any]) -> FakeLLMResponse:
            return FakeLLMResponse('[{"prompt":"Short","answer":"tiny"}]')

    workflow = QuizGenerationWorkflow(
        QuizWorkflowConfig(
            vector_store=FakeVectorStore(hits),  # type: ignore[arg-type]
            embedder=TestEmbeddingBackend(),
            llm=ShortAnswerLLM(""),
        )
    )

    result = workflow.run("math topic")

    evaluation = result.get("evaluation") or {}
    assert evaluation.get("needs_revision") is True
