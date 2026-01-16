"""ChatQwen: LangChain ChatOpenAI wrapper for local Qwen models.

This module provides a custom ChatOpenAI subclass that handles Qwen-specific
behaviors:
1. Automatically adds <|no_think|> to system prompts to disable think mode
2. Strips <think>...</think> blocks from model outputs
3. Preserves ChatOpenAI's structured output functionality

Usage:
    from eduagent.llm.qwen import ChatQwen

    llm = ChatQwen(
        model="Qwen3-235B-A22B",
        base_url="http://localhost:8001/v1",
        temperature=0.5,
    )

    # Works with structured output
    structured_llm = llm.with_structured_output(schema)
"""
from __future__ import annotations

import re
from typing import Any

from langchain_core.messages import BaseMessage, SystemMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_openai import ChatOpenAI


# Regex to match Qwen's <think>...</think> blocks (case-insensitive, multiline)
_THINK_BLOCK_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)

# System prompt prefix to disable Qwen's think mode
_NO_THINK_PREFIX = "<|no_think|>\n"


def _strip_think_blocks(text: str) -> str:
    """Remove <think>...</think> blocks from text.

    Args:
        text: The text to process.

    Returns:
        Text with think blocks removed, stripped of leading/trailing whitespace.
    """
    if not text:
        return ""
    return _THINK_BLOCK_RE.sub("", text).strip()


class ChatQwen(ChatOpenAI):
    """ChatOpenAI subclass for local Qwen models with think mode handling.

    This class automatically:
    1. Prepends <|no_think|> to all messages to disable think mode
    2. Strips <think>...</think> blocks from model outputs

    Example:
        llm = ChatQwen(
            model="Qwen3-235B-A22B",
            base_url="http://localhost:8001/v1",
            temperature=0.5,
            api_key="NOKEY",  # Qwen local deployments often don't require keys
        )

        # Use with structured output
        from pydantic import BaseModel

        class Extraction(BaseModel):
            name: str
            value: float

        structured_llm = llm.with_structured_output(Extraction)
        result = await structured_llm.ainvoke("Extract name and value from text")
    """

    def _inject_no_think_to_all_messages(
        self, messages: list[BaseMessage]
    ) -> list[BaseMessage]:
        """Inject <|no_think|> prefix to all messages.

        This ensures the no_think instruction is present throughout the conversation,
        preventing the model from entering think mode in multi-turn conversations.

        Args:
            messages: List of LangChain messages.

        Returns:
            Modified list with no_think prefix in all messages.
        """
        modified_messages = []
        for msg in messages:
            if hasattr(msg, "content") and isinstance(msg.content, str):
                # Only add prefix if not already present
                if not msg.content.startswith(_NO_THINK_PREFIX):
                    new_content = _NO_THINK_PREFIX + msg.content
                    # Create new message of the same type with modified content
                    modified_messages.append(msg.__class__(content=new_content))
                else:
                    modified_messages.append(msg)
            else:
                modified_messages.append(msg)
        return modified_messages

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Generate chat response with Qwen-specific handling.

        Overrides ChatOpenAI._generate to:
        1. Add no_think prefix to all messages
        2. Strip <think>...</think> blocks from outputs

        Args:
            messages: List of LangChain messages.
            stop: Optional stop sequences.
            run_manager: Optional run manager for callbacks.
            **kwargs: Additional arguments passed to parent.

        Returns:
            ChatResult with think blocks removed from outputs.
        """
        # Step 1: Inject no_think prefix to all messages
        messages = self._inject_no_think_to_all_messages(messages)

        # Step 2: Call parent implementation
        result = super()._generate(messages, stop, run_manager, **kwargs)

        # Step 3: Strip think blocks from all generations
        cleaned_generations = []
        for generation in result.generations:
            if isinstance(generation, ChatGeneration):
                # Clean the message content
                message = generation.message
                if hasattr(message, "content") and message.content:
                    original_content = message.content
                    cleaned_content = _strip_think_blocks(original_content)

                    # Only create new message if content actually changed
                    # This preserves all message attributes (additional_kwargs, etc.)
                    if cleaned_content != original_content:
                        # Create new message with same type, preserving all attributes
                        cleaned_generations.append(
                            ChatGeneration(
                                message=message.__class__(
                                    content=cleaned_content,
                                    additional_kwargs=getattr(message, "additional_kwargs", {}),
                                    response_metadata=getattr(message, "response_metadata", {}),
                                    id=getattr(message, "id", None),
                                )
                            )
                        )
                    else:
                        cleaned_generations.append(generation)
                else:
                    cleaned_generations.append(generation)
            else:
                cleaned_generations.append(generation)

        # Return result with cleaned generations
        return ChatResult(generations=cleaned_generations, llm_output=result.llm_output)

    async def _agenerate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Async generate chat response with Qwen-specific handling.

        Overrides ChatOpenAI._agenerate to:
        1. Add no_think prefix to all messages
        2. Strip think blocks from outputs

        Args:
            messages: List of LangChain messages.
            stop: Optional stop sequences.
            run_manager: Optional run manager for callbacks.
            **kwargs: Additional arguments passed to parent.

        Returns:
            ChatResult with think blocks removed from outputs.
        """
        # Step 1: Inject no_think prefix to all messages
        messages = self._inject_no_think_to_all_messages(messages)

        # Step 2: Call parent implementation
        result = await super()._agenerate(messages, stop, run_manager, **kwargs)

        # Step 3: Strip think blocks from all generations
        cleaned_generations = []
        for generation in result.generations:
            if isinstance(generation, ChatGeneration):
                # Clean the message content
                message = generation.message
                if hasattr(message, "content") and message.content:
                    original_content = message.content
                    cleaned_content = _strip_think_blocks(original_content)

                    # Only create new message if content actually changed
                    # This preserves all message attributes (additional_kwargs, etc.)
                    if cleaned_content != original_content:
                        # Create new message with same type, preserving all attributes
                        cleaned_generations.append(
                            ChatGeneration(
                                message=message.__class__(
                                    content=cleaned_content,
                                    additional_kwargs=getattr(message, "additional_kwargs", {}),
                                    response_metadata=getattr(message, "response_metadata", {}),
                                    id=getattr(message, "id", None),
                                )
                            )
                        )
                    else:
                        cleaned_generations.append(generation)
                else:
                    cleaned_generations.append(generation)
            else:
                cleaned_generations.append(generation)

        # Return result with cleaned generations
        return ChatResult(generations=cleaned_generations, llm_output=result.llm_output)
