from abc import ABC, abstractmethod
from typing import Any


class BaseTool(ABC):
    """
    Abstract base class for all tools used by educational AI agents
    Provides common interface for tool initialization and execution
    """

    def __init__(self, tool_name: str, description: str, version: str = "1.0.0"):
        self.tool_name = tool_name
        self.description = description
        self.version = version
        self.parameters: dict[str, Any] = {}
        self.required_parameters: list[str] = []

    @abstractmethod
    def execute(self, **kwargs) -> dict[str, Any]:
        """
        Execute the tool with provided parameters

        Args:
            **kwargs: Tool-specific parameters

        Returns:
            Dictionary with tool execution results
        """

    @abstractmethod
    def validate_parameters(self, parameters: dict[str, Any]) -> bool:
        """
        Validate if provided parameters are sufficient and correct

        Args:
            parameters: Parameters to validate

        Returns:
            True if parameters are valid, False otherwise
        """

    @abstractmethod
    def get_tool_schema(self) -> dict[str, Any]:
        """
        Return tool schema including parameters and requirements

        Returns:
            Dictionary with tool schema information
        """

    def add_parameter(self, name: str, description: str, required: bool = False, default: Any = None) -> None:
        """
        Add a parameter definition to the tool

        Args:
            name: Parameter name
            description: Parameter description
            required: Whether parameter is required
            default: Default value if not provided
        """
        self.parameters[name] = {
            "description": description,
            "required": required,
            "default": default
        }
        if required:
            self.required_parameters.append(name)

    def remove_parameter(self, name: str) -> None:
        """Remove a parameter definition"""
        if name in self.parameters:
            del self.parameters[name]
            if name in self.required_parameters:
                self.required_parameters.remove(name)

    def get_parameter_info(self, name: str) -> dict[str, Any] | None:
        """Get information about a specific parameter"""
        return self.parameters.get(name)

    @abstractmethod
    def get_tool_capabilities(self) -> dict[str, Any]:
        """
        Return tool capabilities and limitations

        Returns:
            Dictionary with tool capabilities
        """
