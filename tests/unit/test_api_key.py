import zhipuai
from zhipuai.types.chat.chat_completion import Completion

from eduagent.settings import settings


def test_api_key() -> None:
    """
    Verify API Key is set and can create a successful request.
    """
    # Ensure key exists
    assert settings.llm.api_key, "API Key is not set!"
    # print("API Key found:", settings.llm.api_key)

    # Initialize client
    client = zhipuai.ZhipuAI(api_key=settings.llm.api_key)

    # Make a simple chat call
    response = client.chat.completions.create(
        model="glm-4-air",  # or glm-4, glm-4-plus, etc.
        messages=[{"role": "user", "content": "Hello"}],
    )
    assert isinstance(response, Completion)

    # Check response is well formed
    assert response is not None
    assert hasattr(response, "choices")
    assert isinstance(response.choices, list)
    assert len(response.choices) > 0
    assert response.choices[0].message.content  # non-empty reply
