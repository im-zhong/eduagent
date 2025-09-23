from abc import abstractmethod
from typing import Any

from .base import BaseTool


class RAGTool(BaseTool):
    """
    Tool interface for RAG (Retrieval-Augmented Generation) operations
    Handles document processing, knowledge extraction, and knowledge retrieval
    """

    def __init__(self) -> None:
        super().__init__(
            tool_name="rag_knowledge_tool",
            description="Extract knowledge from documents and retrieve relevant educational content"
        )
        # Define tool parameters
        self.add_parameter("file_path", "Path to document file", required=True)
        self.add_parameter("textbook_metadata", "Metadata for the textbook", required=True)
        self.add_parameter("user_query", "User query for knowledge retrieval")
        self.add_parameter("textbook_id", "ID of specific textbook to query")
        self.add_parameter("filters", "Additional filters for retrieval")

    @abstractmethod
    def extract_knowledge(self, file_path: str, textbook_metadata: dict[str, Any]) -> dict[str, Any]:
        """
        Extract knowledge from a document and store in database

        Args:
            file_path: Path to the document file
            textbook_metadata: Metadata about the textbook

        Returns:
            Dictionary with extraction results
        """

    @abstractmethod
    def query_knowledge(self,
                       user_query: str,
                       textbook_id: str | None = None,
                       filters: dict[str, Any] | None = None) -> dict[str, Any]:
        """
        Query the knowledge base for relevant information

        Args:
            user_query: User's query string
            textbook_id: Optional textbook ID to limit search
            filters: Additional query filters

        Returns:
            Dictionary with query results
        """

    @abstractmethod
    def get_knowledge_graph(self, textbook_id: str) -> dict[str, Any]:
        """
        Retrieve knowledge graph data for a textbook

        Args:
            textbook_id: ID of the textbook

        Returns:
            Dictionary with knowledge graph data
        """

    def execute(self, **kwargs: Any) -> dict[str, Any]:
        """Execute RAG tool operation based on parameters"""
        operation = kwargs.get("operation", "query")

        if operation == "extract":
            return self.extract_knowledge(
                kwargs["file_path"],
                kwargs["textbook_metadata"]
            )
        if operation == "query":
            return self.query_knowledge(
                kwargs["user_query"],
                kwargs.get("textbook_id"),
                kwargs.get("filters")
            )
        if operation == "graph":
            return self.get_knowledge_graph(kwargs["textbook_id"])
        return {"error": f"Unknown operation: {operation}"}

    def validate_parameters(self, parameters: dict[str, Any]) -> bool:
        """Validate RAG tool parameters"""
        operation = parameters.get("operation", "query")

        if operation == "extract":
            return "file_path" in parameters and "textbook_metadata" in parameters
        if operation == "query":
            return "user_query" in parameters
        if operation == "graph":
            return "textbook_id" in parameters
        return False

    def get_tool_schema(self) -> dict[str, Any]:
        """Return RAG tool schema"""
        return {
            "name": self.tool_name,
            "description": self.description,
            "version": self.version,
            "operations": ["extract", "query", "graph"],
            "parameters": self.parameters
        }

    def get_tool_capabilities(self) -> dict[str, Any]:
        """Return RAG tool capabilities"""
        return {
            "supported_file_formats": ["pdf", "docx", "txt", "md"],
            "knowledge_extraction": True,
            "semantic_search": True,
            "knowledge_graph_generation": True,
            "multi_modal_support": True,
            "real_time_processing": False
        }
