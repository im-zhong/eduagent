# 2025/12/14
# zhangzhong
from eduagent.agents.chat import get_agent
from eduagent.llm import get_chat_model
from langchain.messages import HumanMessage, AIMessageChunk
import pytest
from langgraph.checkpoint.memory import InMemorySaver

pytestmark = pytest.mark.anyio


async def test_agent() -> None:
    agent = get_agent(model=get_chat_model(), checkpointer=InMemorySaver())

    # https://docs.langchain.com/oss/python/langgraph/streaming
    # async for chunk in agent.astream(
    #     input={"messages": [HumanMessage("please introduce lagnchain")]}
    # ):
    #     print(chunk, flush=True)

    # messages 可以流式输出llm的response
    async for chunk in agent.astream(
        input={"messages": [HumanMessage("hi")]},
        stream_mode="messages",
        config={"configurable": {"user_id": "1", "thread_id": 2}},
    ):
        # chunk 本身就是一个tuple, len = 2, chunk[0]: AIMessageChunk, chunk[1]: dict
        print(chunk, sep="|", flush=True)
