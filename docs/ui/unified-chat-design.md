# UI Architecture: Unified Chat–Driven Multi-Agent System

Overview

This document defines the Unified Chat UI architecture for the AI quiz-generation system.
All user interactions with agents happen through a single conversational interface, instead of multiple feature-specific pages.

This design is intentionally aligned with LangGraph stateful workflows and multi-agent patterns, enabling:
 • Incremental feature development
 • Multi-agent orchestration
 • Streaming observability
 • Long-term system evolution

⸻

Design Comparison

Separate Pages Approach (Legacy / Rejected)

Documents Page        Chat/QA Page         Quiz Generation Page

- Upload docs        - Ask questions       - Generate quizzes
- List docs         - Search docs         - View results

Pros
 • Simple per-page logic
 • Fast to prototype isolated features

Cons
 • Fragmented user experience
 • Context cannot be shared naturally
 • Duplicate chat logic across pages
 • Hard to evolve into multi-agent workflows

⸻

Unified Chat UI Approach (Adopted)

                 Unified Chat Interface (Single Page)

  ┌──────────────┬──────────────────────────┬──────────────────────────┐
  │ Modes /      │ Chat Window               │ Agent Workspace           │
  │ Active Agent │ (Conversation Stream)     │ (Execution Artifacts)     │
  │              │                           │                            │
  │ - Chat       │ - User / Assistant msgs   │ - Intent detection         │
  │ - Search     │ - Streaming tokens        │ - Retrieval results        │
  │ - Quiz       │ - Tool events (optional)  │ - Plans / Drafts           │
  │ - Paper      │                           │ - Validation reports       │
  │ - Review     │                           │ - Final outputs            │
  └──────────────┴──────────────────────────┴──────────────────────────┘

Core Idea

Chat is the control plane. Workspace is the execution plane.

The UI is not just a chatbot; it is a conversation-driven task orchestrator with a live, inspectable workspace.

⸻

Unified Interaction Flow

 1. User inputs a natural language request
 2. Intent is detected (rule-based + LLM fallback)
 3. Request is routed into a LangGraph workflow
 4. One or more agents execute (possibly as subgraphs)
 5. Intermediate artifacts stream into the workspace
 6. Final result is rendered inline in chat

⸻

Why Unified Chat?

Advantages
 • Single mental model: “Talk to the system”
 • Shared context across all tasks
 • Easy to add new agents (just register intent + graph)
 • Perfect fit for multi-agent coordination
 • Natural support for streaming + observability

Trade-offs
 • Higher initial complexity
 • Requires explicit state & protocol design

This document addresses those trade-offs directly.

⸻

Core Architectural Decisions (Explicit)

Decision 1: Intent Is Graph State, Not Just UI State

Intent must be part of LangGraph state, not only a UI variable.

class ChatState(TypedDict):
    messages: list[BaseMessage]
    intent: str | None
    active_agent: str | None
    workspace: dict
    run_status: str

Why
 • Enables multi-step routing
 • Supports agent handoffs
 • Allows agent-internal intent correction
 • Makes runs replayable and debuggable

The UI only reflects intent; it does not own it.

⸻

Decision 2: Agents Are Graph Nodes (or Subgraphs), Not Black Boxes

Short term

async def agent.process(user_input): ...

Long term (target architecture)

Agent = LangGraph Subgraph

Example (Quiz Agent):

retrieve → plan → generate → validate → optimize

Each node produces explicit artifacts for the workspace.

⸻

Decision 3: Workspace Is a First-Class Graph Artifact

Workspace is not ephemeral UI state.
It is a structured projection of Graph State.

class WorkspaceState(TypedDict):
    intent: str
    retrieval: list[RetrievalHit]
    plans: dict
    drafts: list[dict]
    evaluations: list[dict]
    final_output: dict | None

Benefits:
 • Streaming UI
 • Run persistence
 • Retry / resume
 • Diff & auditability
 • Future analytics

⸻

Decision 4: Intent Classification Is Multi-Layered

Layer Method Purpose
L0 Keyword / regex Fast, cheap, explainable
L1 Lightweight LLM Ambiguous cases
L2 Agent self-correction Context-aware fix

Routing may happen:
 • At graph entry (Router node)
 • Inside agents (handoff / refinement)

Decision 5: State Persistence with AsyncPostgresSaver

All ChatState and WorkspaceState must be persisted using LangGraph's AsyncPostgresSaver.

```python
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
import asyncpg

# Initialize async PostgreSQL checkpointer
async def get_checkpointer() -> AsyncPostgresSaver:
    conn = await asyncpg.connect("postgresql://user:pass@localhost:5432/eduagent")
    return AsyncPostgresSaver(conn)

# Compile graph with persistence
app = workflow.compile(
    checkpointer=await get_checkpointer()
)

# Run with thread_id for persistence
config = {"configurable": {"thread_id": "user_session_123"}}
result = await app.ainvoke(initial_state, config)
```

Why
 • Enables run replay and debugging
 • Supports long-running conversations
 • Allows pause/resume workflows
 • Provides audit trail for compliance
 • Enables analytics on user interaction patterns

Thread Management:
 • thread_id identifies a conversation session
 • Each user session maps to one thread_id
 • Threads are created automatically on first invoke
 • Thread history can be retrieved and inspected

State Schema Constraints:
 • All state must be JSON-serializable (for PostgreSQL storage)
 • Use Pydantic models for complex nested structures
 • Avoid storing large binary data (store references instead)

Decision 6: Error Handling with Conditional Routing

LangGraph follows a philosophy: errors should be state-driven, not exception-driven.

Core Principles:

1. Errors in nodes do NOT automatically fail the entire graph
2. State is preserved after errors via checkpoints
3. Use state to communicate error information between nodes
4. Conditional edges route execution based on error conditions

Error State Pattern:

class ChatState(TypedDict):
    messages: list[BaseMessage]
    intent: str | None
    active_agent: str | None
    workspace: dict
    run_status: str  # "running" | "completed" | "failed" | "retrying"
    error: dict | None  # {"node": "generate", "message": "...", "retry_count": 0}

Error Handling Patterns:

1. Retry Pattern (Node-level)
async def generate_node(state: ChatState) -> ChatState:
    max_retries = 3
    for attempt in range(max_retries):
        try:
            result = await llm.ainvoke(...)
            state.workspace["drafts"].append(result)
            return state
        except RateLimitError as e:
            if attempt == max_retries - 1:
                raise
            await asyncio.sleep(2 ** attempt)  # exponential backoff

2. Error State + Conditional Routing (Graph-level)

# Route based on error condition

def route_on_error(state: ChatState) -> str:
    if state.error and state.error.get("retry_count", 0) < 3:
        return "retry_node"
    elif state.error:
        return "error_handler_node"
    return "next_node"

workflow.add_conditional_edges(
    "generate",
    route_on_error,
    {
        "retry_node": "generate",  # Retry the same node
        "error_handler_node": "error_handler",
        "next_node": "validate"
    }
)

# Error handler node provides graceful fallback

async def error_handler_node(state: ChatState) -> ChatState:
    state.run_status = "failed"
    state.workspace["errors"].append({
        "node": state.error["node"],
        "message": state.error["message"],
        "fallback": "Partial results available"
    })
    return state

1. Fallback Node Pattern

async def generate_with_fallback(state: ChatState) -> ChatState:
    try:
        # Try primary generation (expensive model)
        result = await primary_llm.ainvoke(...)
        state.workspace["final_output"] = result
    except Exception as e:
        # Fallback to simpler model
        result = await fallback_llm.ainvoke(...)
        state.workspace["final_output"] = result
        state.workspace["warnings"].append("Used fallback model due to error")
    return state

1. Graceful Degradation Pattern

async def retrieval_node(state: ChatState) -> ChatState:
    try:
        hits = await vector_store.search(...)
        state.workspace["retrieval"] = hits
    except Exception as e:
        # Don't fail - continue with empty retrieval
        state.workspace["retrieval"] = []
        state.workspace["warnings"].append("Retrieval failed, proceeding without context")
    return state

Workspace Error Display:

When state.run_status is "failed" or state.error exists:

if state.error:
    st.error(f"Error in {state.error['node']}: {state.error['message']}")
    if state.workspace.get("warnings"):
        for warning in state.workspace["warnings"]:
            st.warning(warning)

Error Handling Best Practices:
 • Always include error info in state (don't just raise)
 • Use conditional edges for routing based on error state
 • Provide fallback mechanisms for non-critical failures
 • Log errors for debugging while keeping UI user-friendly
 • Preserve partial results when possible (graceful degradation)

⸻

UX Additions (Routing Control + Artifact Protocol)

Add a Manual Override for Routing

Auto-routing should be the default, but the user must be able to force an agent.
This is best expressed as a "Modes / Active Agent" selector in the left panel.
When selected, the router uses the override instead of intent inference.

Why
 • Reduces user frustration on ambiguous prompts
 • Makes behavior predictable when testing
 • Supports "power user" workflows

Minimal Artifact Schema (Workspace Payload)

Agents should return structured artifacts, not just text.
This keeps the workspace UI consistent across agents and enables reuse.

class Artifact(TypedDict):
    type: str               # "retrieval" | "draft" | "plan" | "evaluation" | "final"
    title: str
    payload: dict
    created_at: str

Artifacts are appended to state.workspace and rendered by type.

Intent Visibility in Chat Stream

Each agent response should include a small "intent badge" in the chat UI:
e.g., [intent: quiz_generation], [intent: document_search].

Why
 • Improves transparency and trust
 • Helps debugging routing issues
 • Reinforces multi-agent mental model

⸻

Agent Workspace (Right Panel)

The workspace visualizes what the system is doing, not just what it says.

with st.expander("Agent Workspace", expanded=False):
    st.subheader("Agent Execution")

    if state.intent:
        st.caption(f"Intent: {state.intent}")

    if state.workspace.get("retrieval"):
        st.markdown("### Retrieval")
        for hit in state.workspace["retrieval"]:
            st.write(hit.preview)

    if state.workspace.get("plans"):
        st.markdown("### Plan")
        st.json(state.workspace["plans"])

    if state.workspace.get("evaluations"):
        st.markdown("### Validation")
        for ev in state.workspace["evaluations"]:
            st.write(ev.summary)

Workspace updates are driven by graph streaming events, not polling.

⸻

Chat Interface (Left Panel)

Chat is the interaction surface, not the execution engine.

for msg in st.session_state["messages"]:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

user_input = st.chat_input("请输入您的问题或需求...")

On submit:
 • Append user message
 • Invoke graph (streaming)
 • Render assistant messages + workspace updates

⸻

Agent Types

Agent Description
Chat / QA General explanations, system questions
Document Search Hybrid + graph retrieval
Quiz Generation Single-question agent (RAG + planning)
Paper Generation Multi-agent orchestrator
Review Validation / rewrite / difficulty control

⸻

Top-Level LangGraph Architecture

UnifiedChatGraph
│
├─ IntentRouter
│
├─ ChatAgent
├─ SearchAgent
├─ QuizAgent (subgraph)
│     ├─ retrieve
│     ├─ plan
│     ├─ generate
│     ├─ validate
│     └─ optimize
│
└─ PaperAgent (orchestrator–worker)

All agents:
 • Share ChatState
 • Write into workspace
 • Stream events to UI

⸻

Multi-Agent Patterns Used

Pattern Usage
Router Intent detection
Handoffs Mode switching
Skills Tool / data access
Orchestrator–Worker Paper generation
Evaluator–Optimizer Quality control

⸻

Migration Path

Milestone 5
 • Single QuizAgent
 • Unified chat UI (basic routing)
 • Workspace shows retrieval + result

Milestone 6
 • Replace agent.process with LangGraph subgraphs
 • Enable streaming workspace updates

Milestone 10
 • Full multi-agent orchestration
 • Persistent runs, replay, evaluation loops

⸻

Final Rationale

Unified Chat UI is not a UI choice.
It is a system architecture choice.

It enables:
 • Multi-agent evolution
 • Transparent execution
 • Human-in-the-loop control
 • Research-grade experimentation
 • Production-grade UX

⸻

Implementation Priority

 1. Define ChatState + WorkspaceState
 2. Implement UnifiedChatGraph (minimal)
 3. Stream graph events into UI
 4. Incrementally add agents as subgraphs

⸻

This document is the single source of truth
for UI + Agent coordination in the system.
