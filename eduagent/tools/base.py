from abc import ABC, abstractmethod

from .types import SubmissionData, TextbookMetadata, ToolParameters, ToolResult


class BaseTool(ABC):
    """
    Abstract base class for all tools used by educational AI agents
    Provides common interface for tool initialization and execution
    """

    def __init__(
        self, tool_name: str, description: str, version: str = "1.0.0"
    ) -> None:
        self.tool_name = tool_name
        self.description = description
        self.version = version

    @abstractmethod
    def execute(
        self,
        operation: str,
        file_path: str | None = None,
        textbook_metadata: TextbookMetadata | None = None,
        user_query: str | None = None,
        submissions: list[SubmissionData] | None = None,
    ) -> ToolResult:
        """
        Execute the tool with provided parameters

        Args:
            **kwargs: Tool-specific parameters

        Returns:
            Dictionary with tool execution results
        """

    @abstractmethod
    def validate_parameters(self, parameters: ToolParameters) -> bool:
        """
        Validate if provided parameters are sufficient and correct

        Args:
            parameters: Parameters to validate

        Returns:
            True if parameters are valid, False otherwise
        """

    @abstractmethod
    def get_tool_schema(self) -> ToolResult:
        """
        Return tool schema including parameters and requirements

        Returns:
            Dictionary with tool schema information
        """

    @abstractmethod
    def get_tool_capabilities(
        self,
    ) -> ToolResult:
        """
        Return tool capabilities and limitations

        Returns:
            Dictionary with tool capabilities
        """
