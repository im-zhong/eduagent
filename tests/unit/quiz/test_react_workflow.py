from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any, cast

from eduagent.documents.services import EmbeddingBackend
from eduagent.quiz.workflow import ReActQuizWorkflow, ReActWorkflowConfig
from eduagent.storage.milvus_store import MilvusVectorStore


class StubLLM:
    def __init__(self, responses: list[Any]) -> None:
        self._responses = responses

    def invoke(self, _messages: list[Any]) -> SimpleNamespace:
        if not self._responses:
            msg = "Unexpected LLM invocation"
            raise AssertionError(msg)
        payload = self._responses.pop(0)
        if isinstance(payload, SimpleNamespace):
            return payload
        return SimpleNamespace(content=_to_json(payload))


class StubEmbedder(EmbeddingBackend):
    def embed_query(self, text: str) -> list[float]:  # noqa: ARG002
        return [0.1, 0.2]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[0.1, 0.2] for _ in texts]


class StubVectorStore:
    def __init__(self) -> None:
        self.records: list[dict[str, Any]] = [
            {
                "text": "光合作用是植物制造养分的过程。",
                "metadata": {"ingestion_job_id": "job-1"},
            }
        ]

    def search(self, _embedding: list[float], limit: int) -> list[dict[str, Any]]:
        return self.records[:limit]


def _to_json(payload: Any) -> str:  # noqa: ANN401
    return json.dumps(payload, ensure_ascii=False)


def test_react_workflow_generates_questions() -> None:
    llm_responses: list[Any] = [
        {"thought": "先检索素材", "action": "retrieve"},
        {"status": "continue", "feedback": "需要题目"},
        {"thought": "生成题目", "action": "generate"},
        [
            {"prompt": "解释光合作用。", "answer": "植物利用光能合成有机物。"},
            {"prompt": "光合作用的产物是什么？", "answer": "葡萄糖与氧气。"},
        ],
        {"status": "finish", "feedback": "题目合格"},
    ]
    workflow = ReActQuizWorkflow(
        ReActWorkflowConfig(
            vector_store=cast(MilvusVectorStore, StubVectorStore()),
            embedder=StubEmbedder(),
            llm=StubLLM(llm_responses),
            retrieval_limit=2,
            max_iterations=5,
        )
    )
    result = workflow.run("设计两道练习题", ingestion_job_id="job-1")
    assert result["questions"]
    assert result["questions"][0]["prompt"].startswith("解释光合作用")
    assert result["evaluation"]["feedback"] == "题目合格"


def test_react_workflow_fallback_when_no_chunks() -> None:
    empty_store = StubVectorStore()
    empty_store.records = []
    llm_responses: list[Any] = [
        {"thought": "没有资料也要完成", "action": "generate"},
        [
            {"prompt": "自拟题目", "answer": "参考课本内容。"},
        ],
        {"status": "finish", "feedback": "完成"},
    ]
    workflow = ReActQuizWorkflow(
        ReActWorkflowConfig(
            vector_store=cast(MilvusVectorStore, empty_store),
            embedder=StubEmbedder(),
            llm=StubLLM(llm_responses),
        )
    )
    result = workflow.run("生成题目", ingestion_job_id="job-2")
    assert result["questions"][0]["prompt"] != ""
