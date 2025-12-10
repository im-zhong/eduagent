from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from eduagent.documents.services import EmbeddingBackend
from eduagent.quiz.workflow import QuizGenerationWorkflow, QuizWorkflowConfig
from tests._paths import docs_file

CLASSES_PATH = docs_file("classes.txt")
CLASSES_SAMPLE_QUESTIONS = 2


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
        {
            "text": "Photosynthesis requires sunlight.",
            "metadata": {"ingestion_job_id": "job-1"},
        },
        {
            "text": "Chlorophyll captures light energy.",
            "metadata": {"ingestion_job_id": "job-1"},
        },
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

    result = workflow.run("biology photosynthesis", ingestion_job_id="job-1")

    assert "questions" in result
    assert len(result.get("questions") or []) == 1
    evaluation = result.get("evaluation") or {}
    assert evaluation.get("approved") == 1


def test_quiz_workflow_handles_invalid_llm_output() -> None:
    hits = [
        {
            "text": "The Ming dynasty built a vast navy.",
            "metadata": {"ingestion_job_id": "job-2"},
        }
    ]
    llm = FakeLLM("not-json")
    workflow = QuizGenerationWorkflow(
        QuizWorkflowConfig(
            vector_store=FakeVectorStore(hits),  # type: ignore[arg-type]
            embedder=TestEmbeddingBackend(),
            llm=llm,
        )
    )

    result = workflow.run("history ming", ingestion_job_id="job-2")

    assert len(result.get("questions") or []) == 1
    answers = result.get("answers") or []
    assert answers[0]["is_correct"] is True


def test_quiz_workflow_revision_loop() -> None:
    hits = [{"text": "Short context.", "metadata": {"ingestion_job_id": "job-3"}}]

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

    result = workflow.run("math topic", ingestion_job_id="job-3")

    evaluation = result.get("evaluation") or {}
    assert evaluation.get("needs_revision") is True


def _load_classes_paragraphs(limit: int = 2) -> list[str]:
    text = CLASSES_PATH.read_text(encoding="utf-8")
    paragraphs = [section.strip().replace("\n", " ") for section in text.split("\n\n")]
    minimum_length = 20
    filtered = [
        paragraph
        for paragraph in paragraphs
        if len(paragraph.strip()) >= minimum_length
    ]
    return filtered[:limit]


class _ClassesVectorStore:
    def __init__(self, contexts: list[str], job_id: str) -> None:
        self.contexts = contexts
        self.job_id = job_id

    def search(
        self,
        _embedding: list[float],
        limit: int = 5,
        _expr: str | None = None,
    ) -> list[dict[str, Any]]:
        return [
            {
                "id": f"{self.job_id}-{idx}",
                "score": 0.99 - idx * 0.01,
                "text": text,
                "metadata": {"ingestion_job_id": self.job_id},
            }
            for idx, text in enumerate(self.contexts[:limit])
        ]


class _ClassesLLM:
    def __init__(self, contexts: list[str]) -> None:
        self.contexts = contexts

    def invoke(self, _messages: list[Any]) -> FakeLLMResponse:
        ordered = sorted(
            self.contexts[:2],
            key=lambda text: "Python" not in text,
        )
        payload = [
            {
                "prompt": "What do Python classes bind together?",
                "answer": ordered[0].split("。")[0],
            },
            {
                "prompt": "Why are namespaces important?",
                "answer": ordered[1].split("。")[0],
            },
        ]
        return FakeLLMResponse(json.dumps(payload))


def test_quiz_workflow_uses_classes_sample() -> None:
    job_id = "classes-job"
    paragraphs = _load_classes_paragraphs()
    workflow = QuizGenerationWorkflow(
        QuizWorkflowConfig(
            vector_store=_ClassesVectorStore(paragraphs, job_id),  # type: ignore[arg-type]
            embedder=TestEmbeddingBackend(),
            llm=_ClassesLLM(paragraphs),
            retrieval_limit=2,
        )
    )

    result = workflow.run(
        "Explain the key ideas of Python classes", ingestion_job_id=job_id
    )
    questions = result.get("questions") or []
    assert len(questions) == CLASSES_SAMPLE_QUESTIONS
    assert "Python" in questions[0]["answer"]
    artifacts = result.get("evaluation") or {}
    assert artifacts.get("total") == len(questions)
