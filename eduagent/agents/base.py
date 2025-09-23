from abc import ABC, abstractmethod
from typing import Any


class BaseAgent(ABC):
    """
    Abstract base class for all educational AI agents
    Provides common interface for agent initialization, tool management, and execution
    """

    def __init__(self, agent_id: str, name: str, description: str) -> None:
        self.agent_id = agent_id
        self.name = name
        self.description = description
        self.tools: dict[str, Any] = {}
        self.available_actions: list[str] = []

    @abstractmethod
    def initialize_agent(self) -> None:
        """Initialize agent with required tools and configuration"""

    @abstractmethod
    def process_request(self, request: dict[str, Any]) -> dict[str, Any]:
        """
        Process user request and return agent response
        This is the main entry point for agent execution
        """

    @abstractmethod
    def get_available_actions(self) -> list[str]:
        """Return list of actions this agent can perform"""

    def add_tool(self, tool_name: str, tool_instance: object) -> None:
        """Add a tool to the agent's toolkit"""
        self.tools[tool_name] = tool_instance
        self.available_actions.append(f"use_{tool_name}")

    def remove_tool(self, tool_name: str) -> None:
        """Remove a tool from the agent's toolkit"""
        if tool_name in self.tools:
            del self.tools[tool_name]
            self.available_actions.remove(f"use_{tool_name}")

    def has_tool(self, tool_name: str) -> bool:
        """Check if agent has access to a specific tool"""
        return tool_name in self.tools

    @abstractmethod
    def validate_request(self, request: dict[str, Any]) -> bool:
        """Validate if the request can be processed by this agent"""

    @abstractmethod
    def get_agent_capabilities(self) -> dict[str, Any]:
        """Return agent capabilities and metadata"""
