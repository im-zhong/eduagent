"""Docstring for chatbot.api."""

# 2025/12/14
# zhangzhong

## Authentication
# https://docs.streamlit.io/develop/concepts/connections/authentication
# https://docs.streamlit.io/develop/tutorials/authentication/google

# step 1:
# 为了用OCID，google cloud跟我要支付信息，wechat跟我要网站截图。。。
# https://open.weixin.qq.com/cgi-bin/appcreate?t=manage/createWeb&type=app&lang=zh_CN&token=9f69eada3ff04a80717b45f15db3c105eb2f5b24
# 微信的这个可以搞一下，刚好我有一个网站，用streamlit搞上玩一玩。

from __future__ import annotations


# try fastapi streaming response
# https://fastapi.tiangolo.com/advanced/custom-response/#streamingresponse

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
import asyncio
import json
from pydantic import BaseModel
from typing import Annotated
from eduagent.llm import get_chat_model
from eduagent.agents.chat import (
    get_agent,
    get_config,
    get_threads_for_user,
    get_all_history,
    init_new_agent_thread,
    ensure_user_threads_table,
    insert_user_thread,
)
from langchain.messages import HumanMessage
# from eduagent.agents.chat import MessagesState

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from contextlib import asynccontextmanager
import uuid
from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from fastapi import Request

llm = get_chat_model()


router = APIRouter(prefix="/chat", tags=["Knowledge Chat Agent"])


class AgentMessage(BaseModel):
    user_id: str
    thread_id: str
    message: str


async def agent_chat(agent, message: AgentMessage):
    # each time we call agent, we should get the snapshot of it, and resotre the messages
    # get the latest state

    # async with AsyncPostgresSaver.from_conn_string(DB_URI) as checkpointer:
    # with PostgresSaver.from_conn_string(DB_URI) as checkpointer:
    config = get_config(user_id=message.user_id, thread_id=message.thread_id)
    # checkpoint = agent.get_state(config=config)
    # 其实需要做的事情就是把memory里面的消息放到agent的state里面吧
    # state = MessagesState(**checkpoint.values)
    # 在最开始的时候 checkpoint里面是空的
    # ！！！ 我们不需要手动管理，checkpoint会自动做persistence！！！
    # print("checkpoint: ", checkpoint)
    # if not checkpoint.values:
    #     async for chunk in agent.astream(
    #         input={"messages": [HumanMessage(message)]},
    #         stream_mode="messages",
    #         # 每次调用agent都需要传入config！
    #         # 这样才能记录聊天历史
    #         config=config,
    #     ):
    #         yield f"data: {json.dumps({'token': chunk[0].content})}\n\n"
    # else:
    #     async for chunk in agent.astream(
    #         input={"messages": checkpoint.values["messages"] + [message]},
    #         stream_mode="messages",
    #         config=config,
    #     ):
    #         yield f"data: {json.dumps({'token': chunk[0].content})}\n\n"
    # 我擦！真的！！！牛逼呀，这样就更简单了，相比于没有checkpoint的写法，实际上就只多了一个config参数而已
    async for chunk in agent.astream(
        input={"messages": [HumanMessage(content=message.message)]},
        stream_mode="messages",
        config=config,
    ):
        yield f"data: {json.dumps({'token': chunk[0].content})}\n\n"


class UserMessage(BaseModel):
    messages: list


class NewChatRequest(BaseModel):
    user_id: str
    system_prompt: str | None = None


async def llm_chat(input: UserMessage):
    async for chunk in llm.astream(input=input.messages):
        yield f"data: {json.dumps({'token': chunk.content})}\n\n"


# TODO: 使用lifespan管理生命周期，使用dependency注入依赖
# ===========================
# TODO: App lifecycle & dependency refactor plan
# ===========================
#
# Goal:
# - Use FastAPI lifespan to OWN resource lifecycle (create / cleanup)
# - Use Depends to ACCESS resources (agent / db / checkpointer)
# - Avoid importing `app` inside routers
#
# ---------------------------
# 1. Lifespan (resource creation & cleanup)
# ---------------------------
# - Create long-lived resources inside lifespan ONLY
#   - AsyncPostgresSaver (checkpointer)
#   - DB connection (checkpointer.conn)
#   - LangGraph agent
#
# - Put references into app.state:
#   app.state.agent
#   app.state.conn
#   (optional) app.state.checkpointer
#
# - Use `async with` or `AsyncExitStack`
#   - Let context managers handle cleanup automatically
#   - Do NOT manually close resources after yield
#
# ---------------------------
# 2. app.state usage rule
# ---------------------------
# - app.state is a STORAGE ONLY (holds references)
# - app.state MUST NOT:
#   - create resources
#   - manage lifecycle
#   - contain business logic
#
# ---------------------------
# 3. Dependency layer (Depends)
# ---------------------------
# - Create small dependency functions:
#   def get_agent(request: Request)
#   def get_conn(request: Request)
#
# - Dependencies ONLY:
#   - read from request.app.state
#   - validate resource exists
#   - raise HTTP 500 if not initialized
#
# - Dependencies MUST NOT:
#   - create resources
#   - close resources
#
# ---------------------------
# 4. Router usage rule
# ---------------------------
# - Routers MUST NOT:
#   - import FastAPI app instance
#   - access app.state directly
#
# - Routers MUST:
#   - use Depends(get_agent / get_conn)
#   - treat agent / conn as injected services
#
# ---------------------------
# 5. Testing & future-proofing
# ---------------------------
# - With Depends:
#   - easy to override agent / conn in tests
#   - safe for multi-worker & reload
#
# - Future extensions:
#   - replace app.state with AppServices dataclass
#   - add redis / vector db / http client via AsyncExitStack
#
# ===========================
# End TODO
# ===========================


# in seperate router, we could not access the global fastapi app object
# so use the request.app 永远指向当前运行的 FastAPI 实例, Request 是 FastAPI 注入的
@router.post("/new-chat")
async def new_chat(req: NewChatRequest, request: Request):
    app = request.app
    thread_id = str(uuid.uuid4())
    await insert_user_thread(app.state.conn, req.user_id, thread_id)
    await init_new_agent_thread(
        agent=app.state.agent,
        user_id=req.user_id,
        thread_id=thread_id,
        system_prompt="let's start talk!",
    )
    return {"thread_id": thread_id}


@router.post("/agent-chat")
def do_agent_chat(input: AgentMessage, request: Request):
    # print("get user prompt", input.model_dump())
    app = request.app
    return StreamingResponse(
        agent_chat(app.state.agent, input),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@router.get("/all-chat-threads")
async def get_chat_history(user_id: str, request: Request) -> list[str]:
    app = request.app
    threads = await get_threads_for_user(conn=app.state.conn, user_id=user_id)
    return threads


@router.get("/thread-chat-messages")
async def get_thread_chat_messages(
    user_id: str, thread_id: str, request: Request
) -> list[dict]:
    app = request.app
    # return {role:"", content:""}
    messages = await get_all_history(
        agent=app.state.agent, user_id=user_id, thread_id=thread_id
    )
    print(messages)
    return messages


@router.get("/new-chat")
async def get_new_chat(user_id: str, request: Request) -> str:
    app = request.app
    thread_id = str(uuid.uuid4())
    await init_new_agent_thread(
        agent=app.state.agent, user_id=user_id, thread_id=thread_id
    )
    return thread_id
