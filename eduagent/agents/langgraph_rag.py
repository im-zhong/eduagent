# from __future__ import annotations

# # pyright: reportMissingTypeArgument=false
# # pyright: reportUnknownMemberType=false
# # pyright: reportUnknownArgumentType=false
# # pyright: reportUnknownVariableType=false
# from collections.abc import Callable
# from dataclasses import dataclass
# from typing import Any, Literal, Protocol, cast

# from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
# from langgraph.graph import END, START, StateGraph
# from typing_extensions import TypedDict

# from eduagent.documents.services import EmbeddingBackend
# from eduagent.llm.factory import get_chat_model
# from eduagent.logger import get_logger
# from eduagent.settings import settings
# from eduagent.storage.milvus_store import milvus_store

# logger = get_logger(__name__, component="agents.rag")


# ## 这个生成的agent先不删了，不过写一个简单的能跑起来的agent先
# # 这个agent也根本就没用到啊


# class ConversationTurn(TypedDict):
#     role: Literal["user", "assistant"]
#     content: str


# class RagChatState(TypedDict, total=False):
#     question: str
#     ingestion_ids: list[str]
#     history: list[ConversationTurn]
#     context_chunks: list[dict[str, Any]]
#     references: list[dict[str, Any]]
#     answer: str


# class VectorStoreProtocol(Protocol):
#     def search(
#         self,
#         embedding: list[float],
#         *,
#         limit: int = 5,
#         expr: str | None = None,
#     ) -> list[dict[str, Any]]: ...


# class QueryEmbedderProtocol(Protocol):
#     def embed_query(self, text: str) -> list[float]: ...


# @dataclass
# class RagMemoryAgentConfig:
#     vector_store: VectorStoreProtocol | None = None
#     embedder: QueryEmbedderProtocol | None = None
#     llm: Any | None = None
#     retrieval_limit: int = 4
#     history_turns: int = 4


# @dataclass
# class RagChatResult:
#     answer: str
#     references: list[dict[str, Any]]
#     history: list[ConversationTurn]


# class RagGraphRunnable(Protocol):
#     def invoke(self, state: RagChatState) -> RagChatState: ...


# # 使用的是这个简单的agent，其他复杂的根本没用上
# class RagMemoryAgent:
#     """Simple LangGraph-based RAG agent with short-term memory for chat QA."""

#     SYSTEM_PROMPT = (
#         "你是一名课堂助教，会使用知识库片段回答学生的问题。"
#         "请用简体中文作答，并在需要时引用对应的参考编号。"
#         "如果检索不到答案，请坦率说明。"
#     )

#     def __init__(self, config: RagMemoryAgentConfig | None = None) -> None:
#         self.config = config or RagMemoryAgentConfig()
#         self.vector_store: VectorStoreProtocol = (
#             self.config.vector_store or milvus_store
#         )
#         self.embedder: QueryEmbedderProtocol = (
#             self.config.embedder or EmbeddingBackend()
#         )
#         self.llm = self.config.llm or get_chat_model()
#         self.graph: RagGraphRunnable = self._build_graph()
#         self._callback: Callable[[str, dict[str, Any]], None] | None = None

#     def _build_graph(self) -> RagGraphRunnable:
#         builder: StateGraph = StateGraph(RagChatState)
#         builder.add_node("ingest", self._ingest_step)
#         builder.add_node("retrieve", self._retrieve_step)
#         builder.add_node("respond", self._respond_step)
#         builder.add_edge(START, "ingest")
#         builder.add_edge("ingest", "retrieve")
#         builder.add_edge("retrieve", "respond")
#         builder.add_edge("respond", END)
#         return _RagCompiledGraph(builder.compile())

#     def _append_turn(
#         self, history: list[ConversationTurn], turn: ConversationTurn
#     ) -> list[ConversationTurn]:
#         updated = [*history, turn]
#         limit = max(self.config.history_turns * 2, 0)
#         if limit and len(updated) > limit:
#             updated = updated[-limit:]
#         return updated

#     def _ingest_step(self, state: RagChatState) -> RagChatState:
#         question = state.get("question", "").strip()
#         history = list(state.get("history") or [])
#         if question:
#             history = self._append_turn(
#                 history,
#                 {
#                     "role": "user",
#                     "content": question,
#                 },
#             )
#         state["history"] = history
#         self._emit(
#             "ingest",
#             history=history,
#             todo=["检索知识", "生成回答"],
#         )
#         return state

#     def _retrieve_step(self, state: RagChatState) -> RagChatState:
#         question = state.get("question")
#         if not question:
#             state["context_chunks"] = []
#             state["references"] = []
#             return state
#         query_vector = self.embedder.embed_query(question)
#         expr = self._metadata_expr(state.get("ingestion_ids"))
#         results = self.vector_store.search(
#             query_vector,
#             limit=self.config.retrieval_limit,
#             expr=expr,
#         )
#         logger.info("rag retrieve hits=%s expr=%s", len(results), expr or "<all>")
#         state["context_chunks"] = results
#         state["references"] = [
#             {
#                 "text": hit.get("text", ""),
#                 "metadata": hit.get("metadata") or {},
#                 "score": hit.get("score"),
#             }
#             for hit in results
#         ]
#         self._emit(
#             "retrieve",
#             references=state["references"],
#             todo=["生成回答"],
#         )
#         return state

#     def _respond_step(self, state: RagChatState) -> RagChatState:
#         history = list(state.get("history") or [])
#         question = state.get("question", "")
#         context_chunks = state.get("context_chunks") or []
#         context_text = self._format_context(context_chunks)
#         history_text = self._format_history(history[:-1])
#         system_message = SystemMessage(
#             content=(
#                 f"{self.SYSTEM_PROMPT}\n\n"
#                 f"会话纪要：\n{history_text or '（暂无历史记录）'}\n\n"
#                 f"检索片段：\n{context_text or '（未找到相关片段）'}\n"
#                 "如果引用知识库，请在回答末尾以 [参考#编号] 标注。"
#             )
#         )
#         lc_messages: list[Any] = [system_message]
#         for turn in history[:-1]:
#             if turn["role"] == "user":
#                 lc_messages.append(HumanMessage(content=turn["content"]))
#             else:
#                 lc_messages.append(AIMessage(content=turn["content"]))
#         lc_messages.append(
#             HumanMessage(content=history[-1]["content"] if history else question)
#         )
#         response = self.llm.invoke(lc_messages)
#         if isinstance(response, AIMessage):
#             answer_text = self._normalize_content(response.content)
#         else:
#             answer_text = self._normalize_content(response)
#         history = self._append_turn(
#             history,
#             {
#                 "role": "assistant",
#                 "content": answer_text,
#             },
#         )
#         state["history"] = history
#         state["answer"] = answer_text
#         self._emit(
#             "respond",
#             answer=answer_text,
#             references=state.get("references", []),
#             history=history,
#             todo=[],
#         )
#         return state

#     def _metadata_expr(self, ingestion_ids: list[str] | None) -> str | None:
#         if not ingestion_ids:
#             return None
#         quoted = ",".join(f'"{item}"' for item in ingestion_ids)
#         return f'metadata["ingestion_job_id"] in [{quoted}]'

#     def _format_context(self, chunks: list[dict[str, Any]]) -> str:
#         if not chunks:
#             return ""
#         rendered: list[str] = []
#         for idx, chunk in enumerate(chunks, start=1):
#             text = str(chunk.get("text") or "")
#             source = chunk.get("metadata", {}).get("source") or "unknown"
#             rendered.append(f"[{idx}] ({source}) {text}")
#         return "\n\n".join(rendered)

#     def _format_history(self, history: list[ConversationTurn]) -> str:
#         lines: list[str] = []
#         for turn in history:
#             speaker = "学生" if turn["role"] == "user" else "助教"
#             lines.append(f"{speaker}：{turn['content']}")
#         return "\n".join(lines)

#     def _normalize_content(self, content: object) -> str:
#         if isinstance(content, str):
#             return content
#         if isinstance(content, list):
#             return "".join(str(fragment) for fragment in content)
#         return str(content)

#     def run(
#         self,
#         question: str,
#         *,
#         ingestion_ids: list[str] | None = None,
#         history: list[ConversationTurn] | None = None,
#         callback: Callable[[str, dict[str, Any]], None] | None = None,
#     ) -> RagChatResult:
#         initial_state: RagChatState = {
#             "question": question,
#             "ingestion_ids": ingestion_ids or [],
#             "history": list(history or []),
#         }
#         previous_callback = self._callback
#         self._callback = callback
#         try:
#             final_state = self.graph.invoke(initial_state)
#         finally:
#             self._callback = previous_callback
#         return RagChatResult(
#             answer=final_state.get("answer", ""),
#             references=final_state.get("references", []),
#             history=final_state.get("history", []),
#         )

#     def _emit(self, phase: str, **payload: object) -> None:
#         if self._callback is None:
#             return
#         self._callback(phase, payload)


# def default_rag_memory_agent() -> RagMemoryAgent:
#     """Factory helper wired to global settings."""

#     return RagMemoryAgent(
#         RagMemoryAgentConfig(
#             retrieval_limit=settings.quiz_workflow.retrieval_limit,
#             history_turns=4,
#         )
#     )


# class _RagCompiledGraph(RagGraphRunnable):
#     def __init__(self, compiled_graph: object) -> None:
#         self._graph = cast(RagGraphRunnable, compiled_graph)

#     def invoke(self, state: RagChatState) -> RagChatState:
#         return self._graph.invoke(state)
