from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Protocol, cast

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import START, StateGraph
from typing_extensions import TypedDict

from eduagent.documents.services import EmbeddingBackend
from eduagent.llm.factory import get_chat_model
from eduagent.storage.milvus_store import MilvusVectorStore, milvus_store


class QuizGraphState(TypedDict, total=False):
    prompt: str
    context: list[str]
    questions: list[dict[str, Any]]
    answers: list[dict[str, Any]]
    evaluation: dict[str, Any]


@dataclass
class QuizWorkflowConfig:
    vector_store: MilvusVectorStore | None = None
    embedder: EmbeddingBackend | None = None
    llm: Any | None = None
    retrieval_limit: int = 5


MIN_ANSWER_LENGTH = 5


class GraphRunnable(Protocol):
    def invoke(self, state: QuizGraphState) -> QuizGraphState: ...


class QuizGenerationWorkflow:
    """LangGraph-based workflow that generates, answers, and evaluates quizzes."""

    def __init__(self, config: QuizWorkflowConfig | None = None) -> None:
        self.config = config or QuizWorkflowConfig()
        self.vector_store = self.config.vector_store or milvus_store
        self.embedder = self.config.embedder or EmbeddingBackend()
        self.llm = self.config.llm or get_chat_model()
        self.graph = self._build_graph()

    def _build_graph(self) -> GraphRunnable:
        builder: Any = StateGraph(QuizGraphState)
        builder.add_node("retrieve", self._retrieve_context)
        builder.add_node("generate", self._generate_questions)
        builder.add_node("answer", self._answer_questions)
        builder.add_node("evaluate", self._evaluate_questions)
        builder.add_edge(START, "retrieve")
        builder.add_edge("retrieve", "generate")
        builder.add_edge("generate", "answer")
        builder.add_edge("answer", "evaluate")
        compiled = builder.compile()
        return _CompiledGraph(compiled)

    def _retrieve_context(self, state: QuizGraphState) -> QuizGraphState:
        prompt = state.get("prompt", "")
        embedding = self.embedder.embed_query(prompt)
        hits = self.vector_store.search(embedding, limit=self.config.retrieval_limit)  # type: ignore[arg-type]
        context = [hit.get("text", "") for hit in hits if hit.get("text")]
        return {"prompt": prompt, "context": context}

    def _generate_questions(self, state: QuizGraphState) -> QuizGraphState:
        context = "\n".join(state.get("context") or [])
        messages = [
            SystemMessage(
                content="You are an educational quiz generator that outputs JSON."
            ),
            HumanMessage(
                content=(
                    "Using the following context, produce a JSON list of questions with 'prompt' and 'answer'.\n"
                    f"Context:\n{context}"
                )
            ),
        ]
        response = self.llm.invoke(messages)
        content = getattr(response, "content", "") if response else ""
        parsed_questions: Any = None
        questions: list[dict[str, Any]]
        if content:
            try:
                parsed_questions = json.loads(content)
            except json.JSONDecodeError:
                parsed_questions = None
        if isinstance(parsed_questions, list):
            typed_questions = [
                cast(dict[str, Any], item)
                for item in cast(list[Any], parsed_questions)
                if isinstance(item, dict)
            ]
            if typed_questions:
                questions = typed_questions
            else:
                questions = [
                    {
                        "prompt": f"What is a key fact about: {state.get('prompt', 'the topic')}?",
                        "answer": "Details provided in the context.",
                    }
                ]
        else:
            questions = [
                {
                    "prompt": f"What is a key fact about: {state.get('prompt', 'the topic')}?",
                    "answer": "Details provided in the context.",
                }
            ]
        return {"questions": questions}

    def _answer_questions(self, state: QuizGraphState) -> QuizGraphState:
        answers = [
            {
                "prompt": question.get("prompt", ""),
                "answer": question.get("answer", "N/A"),
                "is_correct": True,
            }
            for question in (state.get("questions") or [])
        ]
        return {"answers": answers}

    def _evaluate_questions(self, state: QuizGraphState) -> QuizGraphState:
        answers = state.get("answers") or []
        needs_revision = any(
            len(ans.get("answer", "")) < MIN_ANSWER_LENGTH for ans in answers
        )
        evaluation = {
            "total": len(answers),
            "approved": sum(
                1 for ans in answers if len(ans.get("answer", "")) >= MIN_ANSWER_LENGTH
            ),
            "needs_revision": needs_revision,
        }
        return {"evaluation": evaluation}

    def run(self, prompt: str) -> QuizGraphState:
        initial_state: QuizGraphState = {"prompt": prompt}
        return self.graph.invoke(initial_state)


class _CompiledGraph(GraphRunnable):
    def __init__(self, compiled: Any) -> None:  # noqa: ANN401
        self._compiled = compiled

    def invoke(self, state: QuizGraphState) -> QuizGraphState:
        result = self._compiled.invoke(state)
        if not isinstance(result, dict):
            error_msg = "Compiled graph returned invalid state"
            raise TypeError(error_msg)
        return cast(QuizGraphState, result)
