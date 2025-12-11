from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Protocol, cast

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import START, StateGraph
from typing_extensions import TypedDict

from eduagent.documents.repository import DocumentRepository
from eduagent.documents.services import EmbeddingBackend
from eduagent.llm.factory import get_chat_model
from eduagent.logger import get_logger
from eduagent.settings import settings
from eduagent.storage.milvus_store import MilvusVectorStore, milvus_store

INGESTION_METADATA_KEY = "ingestion_job_id"
workflow_logger = get_logger(__name__, component="quiz.workflow")


class ReActGraphRunnable(Protocol):
    def invoke(self, state: ReActAgentState) -> ReActAgentState: ...


class QuizWorkflowProtocol(Protocol):
    def run(
        self,
        prompt: str,
        ingestion_job_id: str | None = None,
        *,
        language: str = "zh",
    ) -> dict[str, Any]: ...


class ReActAgentState(TypedDict, total=False):
    task: str
    ingestion_job_id: str | None
    language: str
    plan: str
    thought: str
    action: str
    observation: str
    context_chunks: list[str]
    notes: str
    draft_questions: list[dict[str, Any]]
    critique: str
    goal_met: bool
    iterations: int
    final_output: dict[str, Any]
    tool_counts: dict[str, int]


@dataclass
class ReActWorkflowConfig:
    """Configuration for the ReAct-style workflow."""

    vector_store: MilvusVectorStore | None = None
    embedder: EmbeddingBackend | None = None
    llm: Any | None = None
    retrieval_limit: int = 5
    max_iterations: int = 3
    default_language: str = "zh"


class ReActQuizWorkflow:
    """ReAct-style workflow that plans, selects tools, and refines output in Chinese."""

    def __init__(self, config: ReActWorkflowConfig | None = None) -> None:
        self.config = config or self._config_from_settings()
        self.vector_store = self.config.vector_store or milvus_store
        self.embedder = self.config.embedder or EmbeddingBackend()
        self.llm = self.config.llm or get_chat_model()
        self.graph: ReActGraphRunnable = self._build_graph()

    def _config_from_settings(self) -> ReActWorkflowConfig:
        workflow_settings = settings.quiz_workflow
        return ReActWorkflowConfig(
            retrieval_limit=workflow_settings.retrieval_limit,
            max_iterations=workflow_settings.max_iterations,
            default_language=workflow_settings.default_language,
        )

    def _build_graph(self) -> ReActGraphRunnable:
        builder: Any = StateGraph(ReActAgentState)
        builder.add_node("plan", self._plan_step)
        builder.add_node("act", self._act_step)
        builder.add_node("evaluate", self._evaluate_step)
        builder.add_node("finalize", self._finalize_step)
        builder.add_edge(START, "plan")
        builder.add_edge("plan", "act")
        builder.add_edge("act", "evaluate")
        builder.add_conditional_edges(
            "evaluate",
            self._route_from_evaluation,
            {
                "continue": "plan",
                "finish": "finalize",
            },
        )
        return _ReActCompiledGraph(builder.compile())

    def _route_from_evaluation(self, state: ReActAgentState) -> str:
        if state.get("goal_met"):
            return "finish"
        if state.get("iterations", 0) >= self.config.max_iterations:
            return "finish"
        return "continue"

    def _log_step(
        self,
        state: ReActAgentState,
        phase: str,
        **details: object,
    ) -> None:
        job_id = state.get("ingestion_job_id")
        workflow_logger.info(
            f"react phase={phase} | job={job_id} | details={details}",
        )

    def _record_tool_usage(self, state: ReActAgentState, action: str) -> dict[str, int]:
        counts = dict(state.get("tool_counts") or {})
        counts[action] = counts.get(action, 0) + 1
        return counts

    def run(
        self,
        prompt: str,
        ingestion_job_id: str | None = None,
        *,
        language: str | None = None,
    ) -> dict[str, Any]:
        resolved_language = language or self.config.default_language
        initial_state: ReActAgentState = {
            "task": prompt,
            "ingestion_job_id": ingestion_job_id,
            "language": resolved_language,
            "context_chunks": [],
            "draft_questions": [],
            "iterations": 0,
            "tool_counts": {},
        }
        final_state = self.graph.invoke(initial_state)
        if "final_output" not in final_state:
            final_state = self._finalize_step(final_state)
        result = final_state.get("final_output")
        if isinstance(result, dict):
            return result
        return {
            "questions": final_state.get("draft_questions", []),
            "answers": final_state.get("draft_questions", []),
            "evaluation": {
                "feedback": str(final_state.get("critique", "")),
                "tool_usage": dict(final_state.get("tool_counts") or {}),
            },
            "ingestion_job_id": ingestion_job_id,
        }

    def _plan_step(self, state: ReActAgentState) -> ReActAgentState:
        messages = [
            SystemMessage(
                content="你是一名教育任务规划专家，需要使用思考-行动-观察的方式完成任务。"
            ),
            HumanMessage(
                content=(
                    "任务: {task}\n"
                    "已掌握内容: {context}\n"
                    "请用JSON回答，包含thought(思考)和action(动作，"
                    "可选 retrieve/summarize/generate/critique/finish)。"
                ).format(
                    task=state.get("task", ""),
                    context="；".join(state.get("context_chunks", [])) or "暂无",
                )
            ),
        ]
        response = self.llm.invoke(messages)
        payload = self._parse_json_response(response, default={})
        action = str(payload.get("action") or "retrieve")
        thought = str(payload.get("thought") or "")
        plan = str(payload.get("plan") or state.get("plan", ""))
        self._log_step(
            state,
            "plan",
            thought=thought,
            action=action,
            plan=plan,
        )
        return {"action": action, "thought": thought, "plan": plan}

    def _act_step(self, state: ReActAgentState) -> ReActAgentState:
        action = state.get("action", "retrieve")
        result: ReActAgentState
        if action == "retrieve":
            result = self._perform_retrieval(state)
        elif action == "summarize":
            result = self._summarize_context(state)
        elif action == "generate":
            result = self._generate_questions(state)
        elif action == "critique":
            result = self._critique_questions(state)
        else:
            result = cast(ReActAgentState, {"observation": "未执行动作"})
        counts = self._record_tool_usage(state, action)
        result["tool_counts"] = counts
        self._log_step(
            state,
            "act",
            action=action,
            observation=result.get("observation"),
            tool_usage=counts,
        )
        return result

    def _evaluate_step(self, state: ReActAgentState) -> ReActAgentState:
        iterations = state.get("iterations", 0) + 1
        messages = [
            SystemMessage(content="你是负责检查任务进度的审查官。"),
            HumanMessage(
                content=(
                    "当前计划: {plan}\n"
                    "最新观察: {observation}\n"
                    "草稿题目数量: {count}\n"
                    "请判断是否完成任务，返回JSON，包含status(continue/finish)"
                    "和feedback。"
                ).format(
                    plan=state.get("plan", ""),
                    observation=state.get("observation", ""),
                    count=len(state.get("draft_questions") or []),
                )
            ),
        ]
        response = self.llm.invoke(messages)
        payload = self._parse_json_response(
            response, default={"status": "continue", "feedback": ""}
        )
        goal_met = str(payload.get("status", "continue")) == "finish"
        critique = str(payload.get("feedback") or "")
        self._log_step(
            state,
            "evaluate",
            goal_met=goal_met,
            feedback=critique,
            iterations=iterations,
        )
        return {
            "goal_met": goal_met,
            "critique": critique,
            "iterations": iterations,
        }

    def _finalize_step(self, state: ReActAgentState) -> ReActAgentState:
        draft = state.get("draft_questions") or []
        if not draft:
            draft = [
                {
                    "prompt": "根据教材内容自拟一道题目。",
                    "answer": "根据笔记撰写答案。",
                }
            ]
        evaluation = {
            "feedback": str(state.get("critique", "")),
            "tool_usage": dict(state.get("tool_counts") or {}),
        }
        output = {
            "questions": draft,
            "answers": draft,
            "evaluation": evaluation,
            "ingestion_job_id": state.get("ingestion_job_id"),
        }
        self._log_step(
            state,
            "finalize",
            questions=len(draft),
            evaluation=evaluation,
        )
        return {
            **state,
            "final_output": output,
            "goal_met": True,
        }

    def _perform_retrieval(self, state: ReActAgentState) -> ReActAgentState:
        task = state.get("task", "")
        embedding = self.embedder.embed_query(task)
        hits = cast(
            list[dict[str, Any]],
            self.vector_store.search(
                embedding,
                limit=self.config.retrieval_limit,  # type: ignore[arg-type]
            ),
        )
        ingestion_job_id = state.get("ingestion_job_id")

        def matches_job(hit: dict[str, Any]) -> bool:
            metadata = cast(dict[str, Any] | None, hit.get("metadata"))
            if not isinstance(metadata, dict):
                return False
            if ingestion_job_id is None:
                return True
            return metadata.get(INGESTION_METADATA_KEY) == ingestion_job_id

        filtered = [hit for hit in hits if matches_job(hit)]
        chunks: list[str] = []
        for hit in filtered:
            text_value = hit.get("text")
            if isinstance(text_value, str):
                chunks.append(text_value)
        return {
            "context_chunks": chunks or state.get("context_chunks", []),
            "observation": f"检索到{len(chunks)}段内容",
        }

    def _summarize_context(self, state: ReActAgentState) -> ReActAgentState:
        context = "\n".join(state.get("context_chunks") or [])
        messages = [
            SystemMessage(content="你是擅长提炼要点的老师。"),
            HumanMessage(
                content=(
                    "请用中文概括以下内容的关键知识点，每条不超过40字：\n{context}"
                ).format(context=context or "暂无内容")
            ),
        ]
        response = self.llm.invoke(messages)
        summary = str(getattr(response, "content", ""))
        return {"notes": summary, "observation": summary}

    def _generate_questions(self, state: ReActAgentState) -> ReActAgentState:
        notes = state.get("notes") or "\n".join(state.get("context_chunks") or [])
        messages = [
            SystemMessage(content="你是一名中文出题专家，必须输出JSON格式。"),
            HumanMessage(
                content=(
                    "请根据以下笔记生成1-2道练习题，输出JSON数组，"
                    "每项包含prompt和answer字段。\n{notes}"
                ).format(notes=notes or "暂无资料")
            ),
        ]
        response = self.llm.invoke(messages)
        payload = self._parse_json_response(response, default=[])
        questions: list[dict[str, Any]] = []
        if isinstance(payload, list):
            payload_items = cast(list[Any], payload)
            typed_items: list[dict[str, Any]] = [
                cast(dict[str, Any], element)
                for element in payload_items
                if isinstance(element, dict)
            ]
            questions.extend(
                {
                    "prompt": str(question.get("prompt", "")),
                    "answer": str(question.get("answer", "")),
                }
                for question in typed_items
            )
        if not questions:
            questions = [
                {
                    "prompt": "描述教材中的一个核心概念。",
                    "answer": "根据课文内容回答。",
                }
            ]
        return {
            "draft_questions": questions,
            "observation": f"已生成{len(questions)}道题目",
        }

    def _critique_questions(self, state: ReActAgentState) -> ReActAgentState:
        questions = state.get("draft_questions") or []
        messages = [
            SystemMessage(content="你是审稿老师，需要指出题目问题。"),
            HumanMessage(
                content=(
                    f"题目列表: {json.dumps(questions, ensure_ascii=False)}\n"
                    "请用中文指出需要改进的地方，并给出建议。"
                )
            ),
        ]
        response = self.llm.invoke(messages)
        criticism = str(getattr(response, "content", ""))
        return {"critique": criticism, "observation": criticism}

    def _parse_json_response(self, response: Any, *, default: Any) -> Any:  # noqa: ANN401
        content = getattr(response, "content", "")
        if isinstance(content, str):
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                return default
        return default


class _ReActCompiledGraph(ReActGraphRunnable):
    def __init__(self, compiled: Any) -> None:  # noqa: ANN401
        self._compiled = compiled

    def invoke(self, state: ReActAgentState) -> ReActAgentState:
        result = self._compiled.invoke(state)
        if not isinstance(result, dict):
            error_msg = "Compiled graph returned invalid state"
            raise TypeError(error_msg)
        return cast(ReActAgentState, result)


@dataclass
class QuizWorkflowRunner:
    repository: DocumentRepository
    workflow: QuizWorkflowProtocol | None = None

    def __post_init__(self) -> None:
        if self.workflow is None:
            self.workflow = ReActQuizWorkflow()

    async def run(
        self,
        ingestion_job_id: str,
        prompt: str,
        *,
        document_job_id: str | None = None,
    ) -> dict[str, Any]:
        doc_job_id = document_job_id or ingestion_job_id
        ingestion_job = await self.repository.get_job(doc_job_id)
        if ingestion_job is None:
            error_msg = "Ingestion job not found"
            raise ValueError(error_msg)
        workflow: QuizWorkflowProtocol = self.workflow or ReActQuizWorkflow()
        self.workflow = workflow
        metadata = ingestion_job.job_metadata or {}
        language = (
            cast(str | None, metadata.get("language"))
            or settings.quiz_workflow.default_language
        )
        workflow_result = dict(
            workflow.run(prompt, ingestion_job_id=doc_job_id, language=language) or {}
        )
        artifact = await self.repository.add_artifact(
            doc_job_id,
            artifact_type="quiz_workflow",
            payload=workflow_result,
            pipeline_job_id=ingestion_job_id,
        )
        if artifact is None:
            error_msg = "Failed to persist quiz artifact"
            raise RuntimeError(error_msg)
        workflow_result.pop("ingestion_job_id", None)
        return {
            "artifact_id": artifact.id,
            "ingestion_job_id": ingestion_job_id,
            **workflow_result,
        }
