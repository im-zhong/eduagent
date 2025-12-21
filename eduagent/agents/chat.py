# 2025/12/14
# zhangzhong
# https://docs.langchain.com/oss/python/langgraph/quickstart

from operator import add
from typing import Annotated, Any

from langchain.messages import AIMessage, AnyMessage, HumanMessage, SystemMessage
from langchain_core.language_models import BaseChatModel
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver

# https://docs.langchain.com/oss/python/langgraph/persistence
# - The state of a thread at a particular point in time is called a checkpoint.
# - config: Config associated with this checkpoint.
# - metadata: Metadata associated with this checkpoint.
# - values: Values of the state channels at this point in time.
# - next A tuple of the node names to execute next in the graph.
# - tasks: A tuple of PregelTask objects that contain information about next tasks to be executed. If the step was previously attempted, it will include error information. If a graph was interrupted dynamically from within a node, tasks will contain additional data associated with interrupts.
# https://github.com/langchain-ai/langgraph/tree/main/libs/checkpoint-postgres
# https://docs.langchain.com/oss/python/langgraph/add-memory#example-using-postgres-checkpointer
# 我必须要按照这个例子里面的方式来写吗？用with？
# from langgraph.checkpoint.postgres import PostgresSaver
# from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from typing_extensions import TypedDict

from eduagent.llm import get_chat_model


# 在 LangGraph 里：
# 	•	State 是在一次 graph 执行过程中持续存在的
# 	•	执行结束（到 END）后，state 就“死了”
# 	•	下一次 graph.invoke(...) → 重新创建 state
# TODO: 使用langgraph checkpointer来做跨graph调用的memory
#  只有使用 checkpointer + thread_id，state 才会跨 invoke 持久化
# TODO: 你现在每次都硬塞一个 SystemMessage：， 会导致 系统提示重复注入（如果你以后做多轮）。
class MessagesState(TypedDict):
    # reducer: The Annotated type with operator.add ensures that new messages are appended to the existing list rather than replacing it.
    messages: Annotated[list[AnyMessage], add]
    llm_calls: int


# 看起来我们必须先启动一个pg了
# 看起来async pg saver的内部实现并没有使用sqlalchemy，直接用的psycopg
DB_URI = "postgresql://postgres:postgres@localhost:5442/postgres?sslmode=disable"


def get_agent(
    model: BaseChatModel,
    checkpointer: BaseCheckpointSaver,
) -> CompiledStateGraph[MessagesState, None, MessagesState, MessagesState]:
    # 这里应该有两个东西
    # State: State in LangGraph persists throughout the agent’s execution
    # Context: 暂时还没有学到

    # TODO:
    # 每次连接都会创建各异连接池pool，每个连接池默认十个连接，所以一个全局的async pg saver的连接是合适的
    # 不过为了编码方便，我们这里还是每次重新会话都重新创建连接
    # 好像是我们必须在这里也创建async的checkpointer，
    # 并且好像在agent chat里面不需要创建checkpointer 因为根本就用不到，所以这个async saver 必须是全局的
    # async with AsyncPostgresSaver.from_conn_string(DB_URI) as checkpointer:
    #     # When using Postgres checkpointers for the first time, make sure to call .setup() method on them to create required tables
    #     checkpointer.setup()

    # how to guide里面是把这个llmcall也放到with context里面了，我认为是没有必要的
    def llm_call(state: dict) -> dict[str, Any]:
        """LLM decides whether to call a tool or not"""

        return {
            "messages": [
                model.invoke(
                    # 使用上checkpoint saver这里就不对了 应该只有在state第一次初始化的时候，加上，不然的话
                    # 每次调用llm call这个函数就都会在消息记录里面加上这一条
                    # [SystemMessage(content="You are a helpful chatbot.")]
                    #
                    state["messages"]
                )
            ],
            "llm_calls": state.get("llm_calls", 0) + 1,
        }

    # Build workflow
    agent_builder = StateGraph(state_schema=MessagesState)

    # Add nodes, 支持clouser
    agent_builder.add_node("llm_call", llm_call)

    # Add edges to connect nodes
    agent_builder.add_edge(START, "llm_call")
    agent_builder.add_edge("llm_call", END)

    # Compile the agent
    # checkpointer = InMemorySaver()
    agent = agent_builder.compile(checkpointer=checkpointer)
    return agent


def get_config(thread_id: str, user_id: str) -> RunnableConfig:
    return {"configurable": {"thread_id": thread_id, "user_id": user_id}}


def to_openai_messages(raw_messages):
    role_map = {
        HumanMessage: "user",
        AIMessage: "assistant",
        SystemMessage: "system",
    }
    result = []
    for m in raw_messages:
        for cls, role in role_map.items():
            if isinstance(m, cls):
                result.append({"role": role, "content": m.content})
                break
    return result


async def get_all_history(agent: CompiledStateGraph, user_id: str, thread_id: str):
    config = {"configurable": {"user_id": user_id, "thread_id": thread_id}}
    # get the latest state
    snapshot = await agent.aget_state(config=config)

    # list[BaseMessage]
    raw_messages = snapshot.values["messages"]
    # print(raw_messages)
    # messages = [msg["input"] for msg in raw_messages]
    messages = to_openai_messages(raw_messages)

    return messages

    # I want to get all the history state
    # 这个函数都是拿到某个thread 的所有对话历史的，不是拿到所有的对话！
    # snapshots = agent.get_state_history(config=config)

    # 对于我们的agent，想要在某个history上进行聊天，只需要
    # 1. 在agent.invoke里面加上checkpoint_id这个参数
    # 2. 每次都找到某个
    # 不对不对！只需要拿到thread id就行了呀！！！
    # 如果config里面只提供了 thread id，那么就总是从最新的checkpoint开始replay
    # 这和我们的预期行为是一样的


async def get_threads_for_user(conn, user_id: str) -> list[str]:
    query = """
        SELECT thread_id
        FROM user_threads
        WHERE user_id = %s
        ORDER BY created_at DESC
    """
    async with conn.cursor() as cur:
        await cur.execute(query, (user_id,))
        rows = await cur.fetchall()
    return [r["thread_id"] for r in rows]


async def ensure_user_threads_table(conn) -> None:
    """Create user_threads table if it doesn't exist."""
    async with conn.cursor() as cur:
        await cur.execute(
            """
            CREATE TABLE IF NOT EXISTS user_threads (
                user_id TEXT NOT NULL,
                thread_id TEXT PRIMARY KEY,
                created_at TIMESTAMP DEFAULT now()
            );
            """
        )
        await cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_user_threads_user
            ON user_threads(user_id);
            """
        )


async def insert_user_thread(conn, user_id: str, thread_id: str) -> None:
    """Record a new chat thread for a user."""
    sql = """
        INSERT INTO user_threads (user_id, thread_id)
        VALUES (%s, %s)
        ON CONFLICT (thread_id) DO NOTHING
    """
    async with conn.cursor() as cur:
        await cur.execute(sql, (user_id, thread_id))


async def init_new_agent_thread(
    agent: CompiledStateGraph,
    user_id: str,
    thread_id: str,
    system_prompt: str | None = None,
) -> None:
    """Seed a new thread with an initial system message."""
    config = get_config(thread_id=thread_id, user_id=user_id)
    base_messages: list[AnyMessage] = []
    if system_prompt:
        base_messages.append(SystemMessage(content=system_prompt))

    # https://docs.langchain.com/oss/python/langgraph/persistence#update-state
    # Persist the initial state so subsequent invokes pick it up from the checkpointer.
    await agent.aupdate_state(
        config=config,
        values={"messages": base_messages, "llm_calls": 0},
    )
