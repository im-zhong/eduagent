from __future__ import annotations

import pytest
from langchain_core.messages import HumanMessage
from pydantic import BaseModel

from eduagent.llm import get_chat_model

pytestmark = pytest.mark.anyio


class User(BaseModel):
    name: str
    age: int


async def test_chat_model_with_structured_output() -> None:
    chat = get_chat_model()
    # https://reference.langchain.com/python/integrations/langchain_aws/?h=with_struc#langchain_aws.ChatBedrockConverse.with_structured_output
    # https://reference.langchain.com/python/integrations/langchain_deepseek/#langchain_deepseek.ChatDeepSeek.with_structured_output
    # deepseek的method支持function_calling, json_method, json_schema
    # schema: The schema defining the structured output format. Supports:
    #   Pydantic models: BaseModel subclasses with field validation
    #   Dataclasses: Python dataclasses with type annotations
    #   TypedDict: Typed dictionary classes
    #   JSON Schema: Dictionary with JSON schema specification
    # method:
    # - json_method or json_schema
    #   Some model providers support structured output natively through their APIs (e.g. OpenAI, Grok, Gemini).
    #   This is the most reliable method when available.
    # - function_calling:
    #   For models that don’t support native structured output, LangChain uses tool calling to achieve the same result.
    #   This works with all models that support tool calling, which is most modern models.
    # include_raw:
    #   If False, return only parsed output. If an error occurs during model output parsing it will be raised.
    #   If True, return a dict with raw (BaseMessage), parsed (or None on parse failure), and parsing_error (exception or None).
    #   If an error occurs during output parsing it will be caught and returned as well.
    #   The final output is always a dict with keys 'raw', 'parsed', and 'parsing_error'.
    structured = chat.with_structured_output(
        schema=User,
        # method="function_calling",
        include_raw=False,
    )

    result = await structured.ainvoke(
        input=[HumanMessage(content="hi, I am Ada, and I am 5 age")]
    )

    # 感觉不太适合stream
    # async for chunk in structured.astream(
    #     input=[HumanMessage(content="hi, I am Ada, and I am 5 age")]
    # ):
    #     print(chunk)

    assert isinstance(result, User)
    assert result.name == "Ada"
    assert result.age == 5

    structured = chat.with_structured_output(
        schema=User,
        # qwen 支持 json mode，可以通过测试
        # 智谱ai只支持function calling，不能通过测试，会出现幻觉
        # deepseek需要在prompt中明确提及json，但是也可以通过测试, json_schema不行
        method="json_mode",
        include_raw=True,
    )
    result = await structured.ainvoke(
        input=[HumanMessage(content="extract info into json: hi, what a nice day!,")]
        # input=[HumanMessage(content="hi, what a nice day!,")]
    )
    # zhipu和deepseek在没有提供schema里的信息的时候，会出现幻觉，强行解析
    # zhipu: user=john, age=25
    # deepseek: user=User, age=0
    print(result)
    raw = result["raw"]
    parsed = result["parsed"]
    parsing_error = result["parsing_error"]
    assert parsed is None
    assert parsing_error is not None


def test_chat_model_stream() -> None:
    model = get_chat_model()

    for chunk in model.stream(input=[HumanMessage("please introduce langchain")]):
        print(chunk)
