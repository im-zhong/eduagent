from __future__ import annotations

from langchain_core.messages import AIMessage

from eduagent.agents import (
    ConversationTurn,
    RagMemoryAgent,
    RagMemoryAgentConfig,
)


class StubVectorStore:
    def __init__(self) -> None:
        self.requests: list[dict[str, object]] = []

    def search(
        self,
        embedding: list[float],
        *,
        limit: int = 5,
        expr: str | None = None,
    ) -> list[dict[str, object]]:
        self.requests.append({"embedding": embedding, "limit": limit, "expr": expr})
        return [
            {
                "id": "chunk-1",
                "text": "牛顿第一定律描述了惯性。",
                "metadata": {"source": "physics.docx", "page": 3},
                "score": 0.92,
            }
        ]


class StubEmbedder:
    def __init__(self) -> None:
        self.queries: list[str] = []

    def embed_query(self, text: str) -> list[float]:
        self.queries.append(text)
        return [0.1, 0.2, 0.3]


class StubLLM:
    def __init__(self) -> None:
        self.calls: list[list[object]] = []

    def invoke(self, messages: list[object]) -> AIMessage:
        self.calls.append(messages)
        return AIMessage(content="最终答案：物体保持匀速直线运动。")


def test_memory_agent_returns_answer_and_references() -> None:
    vector = StubVectorStore()
    embedder = StubEmbedder()
    llm = StubLLM()
    agent = RagMemoryAgent(
        RagMemoryAgentConfig(
            vector_store=vector,
            embedder=embedder,
            llm=llm,
            retrieval_limit=2,
            history_turns=2,
        )
    )
    previous_history: list[ConversationTurn] = [
        {"role": "user", "content": "你好"},
        {"role": "assistant", "content": "请问我能帮你什么？"},
    ]
    result = agent.run(
        "解释一下牛顿第一定律",
        history=previous_history,
        ingestion_ids=["job-1"],
    )
    assert "最终答案" in result.answer
    assert result.references
    assert result.references[0]["metadata"]["source"] == "physics.docx"
    assert embedder.queries == ["解释一下牛顿第一定律"]
    expected_limit = 2
    assert vector.requests[0]["limit"] == expected_limit
    assert len(result.history) <= agent.config.history_turns * 2
    assert result.history[-1]["role"] == "assistant"


def test_history_is_trimmed_to_configured_window() -> None:
    vector = StubVectorStore()
    embedder = StubEmbedder()
    llm = StubLLM()
    agent = RagMemoryAgent(
        RagMemoryAgentConfig(
            vector_store=vector,
            embedder=embedder,
            llm=llm,
            retrieval_limit=1,
            history_turns=1,
        )
    )
    long_history: list[ConversationTurn] = []
    for idx in range(6):
        long_history.append({"role": "user", "content": f"问题{idx}"})
        long_history.append({"role": "assistant", "content": f"回答{idx}"})
    result = agent.run("最新问题", history=long_history)
    assert len(result.history) <= agent.config.history_turns * 2
    assert result.history[-1]["role"] == "assistant"
