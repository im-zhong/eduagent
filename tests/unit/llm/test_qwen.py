"""Unit tests for ChatQwen model.

Tests the ChatQwen wrapper for local Qwen models, including:
- Normal chat functionality
- Structured output with Pydantic models

Note: These tests use the real Qwen model endpoint.
"""

from __future__ import annotations

import pytest
from pydantic import BaseModel, Field

from eduagent.llm.factory import get_qwen_local_model_with_no_think
from eduagent.llm.qwen import ChatQwen, _strip_think_blocks


# ================================
# _strip_think_blocks() Utility Tests
# ================================


class TestStripThinkBlocks:
    """Test the _strip_think_blocks utility function."""

    def test_strip_think_blocks_basic(self) -> None:
        """Test stripping basic think block."""
        text = "Before\n\nAfter"
        result = _strip_think_blocks(text)
        assert "Before" in result
        assert "After" in result
        assert "Some reasoning here" not in result

    def test_strip_think_blocks_case_insensitive(self) -> None:
        """Test that think block matching is case-insensitive."""
        text = "Before\n<THINK>Reasoning</THINK>\nAfter"
        result = _strip_think_blocks(text)
        assert "Before" in result
        assert "After" in result
        assert "Reasoning" not in result

    def test_strip_think_blocks_empty_input(self) -> None:
        """Test stripping from empty string."""
        assert _strip_think_blocks("") == ""

    # def test_strip_think_blocks_multiple_blocks(self) -> None:
    #     """Test stripping multiple think blocks."""
    #     text = "Start\n</think>First\n\nMiddle\n\nSecond\n\nEnd"
    #     result = _strip_think_blocks(text)
    #     assert "Start" in result
    #     assert "Middle" in result
    #     assert "End" in result
    #     assert "First" not in result
    #     assert "Second" not in result


# ================================
# ChatQwen Model Tests
# ================================


class TestChatQwenModel:
    """Test ChatQwen model functionality."""

    def test_chat_qwen_initialization(self) -> None:
        """Test ChatQwen can be initialized with required parameters."""
        llm = ChatQwen(
            model="Qwen3-235B-A22B",
            base_url="http://222.30.145.85:8001/v1",
            api_key="NOKEY",
            temperature=0.5,
        )
        assert llm.model_name == "Qwen3-235B-A22B"
        assert llm.temperature == 0.5


# ================================
# Integration Tests (with real model)
# ================================


class TestChatQwenIntegration:
    """Integration tests with real Qwen model endpoint."""

    @pytest.mark.asyncio
    async def test_simple_chat(self) -> None:
        """Test simple chat interaction with Qwen model."""
        llm = get_qwen_local_model_with_no_think()

        # Simple question that should not trigger think mode
        response = await llm.ainvoke("What is 2 + 2? Answer with just the number.")

        # Verify we got a response
        assert response.content is not None
        assert len(response.content) > 0

        # Verify think block was removed (if model outputted one)
        # The model should not have think blocks in the output
        assert "<think>" not in response.content
        assert "</think>" not in response.content

        # The answer should contain 4
        assert "4" in response.content

    @pytest.mark.asyncio
    async def test_structured_output(self) -> None:
        """Test structured output with Pydantic model."""
        llm = get_qwen_local_model_with_no_think()

        # Define a simple schema for extraction
        class PersonInfo(BaseModel):
            """Extracted person information."""

            name: str = Field(description="The person's name")
            age: int = Field(description="The person's age")
            city: str = Field(description="The city where the person lives")

        # Create structured output model
        structured_llm = llm.with_structured_output(PersonInfo)

        # Test text for extraction
        test_text = "John is a 25-year-old software engineer living in Beijing."

        # Invoke with structured output
        result = await structured_llm.ainvoke(test_text)

        # Verify we got a PersonInfo object
        assert isinstance(result, PersonInfo)
        assert isinstance(result.name, str)
        assert isinstance(result.age, int)
        assert isinstance(result.city, str)

        # Verify the extracted values are reasonable
        assert "John" in result.name
        assert result.age == 25
        assert "Beijing" in result.city
