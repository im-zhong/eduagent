from abc import abstractmethod

from .base import BaseTool
from .types import (
    FilterCriteria,
    SubmissionData,
    TextbookMetadata,
    ToolParameters,
    ToolResult,
)


class RAGTool(BaseTool):
    """
    Tool interface for RAG (Retrieval-Augmented Generation) operations
    Handles document processing, knowledge extraction, and knowledge retrieval
    """

    def __init__(self) -> None:
        super().__init__(
            tool_name="rag_knowledge_tool",
            description="Extract knowledge from documents and retrieve relevant educational content",
        )

    @abstractmethod
    def extract_knowledge(
        self, file_path: str, textbook_metadata: TextbookMetadata
    ) -> ToolResult:
        """
        Extract knowledge from a document and store in database

        Args:
            file_path: Path to the document file
            textbook_metadata: Metadata about the textbook

        Returns:
            Dictionary with extraction results
        """

    @abstractmethod
    def query_knowledge(
        self,
        user_query: str,
        textbook_id: str | None = None,
        filters: FilterCriteria | None = None,
    ) -> ToolResult:
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
    def get_knowledge_graph(self, textbook_id: str) -> ToolResult:
        """
        Retrieve knowledge graph data for a textbook

        Args:
            textbook_id: ID of the textbook

        Returns:
            Dictionary with knowledge graph data
        """

    def execute(
        self,
        operation: str,
        file_path: str | None = None,
        textbook_metadata: TextbookMetadata | None = None,
        user_query: str | None = None,
        submissions: list[SubmissionData] | None = None,  # noqa: ARG002
    ) -> ToolResult:
        """Execute RAG tool operation based on parameters"""
        if operation == "extract" and file_path and textbook_metadata:
            return self.extract_knowledge(file_path, textbook_metadata)
        if operation == "query" and user_query:
            return self.query_knowledge(user_query)
        if operation == "graph" and user_query:
            textbook_id = (
                user_query.split(":")[1].strip() if ":" in user_query else user_query
            )
            return self.get_knowledge_graph(textbook_id)
        return ToolResult(
            success=False, error=f"Unknown or invalid operation: {operation}"
        )

    def validate_parameters(self, parameters: ToolParameters) -> bool:
        """Validate RAG tool parameters"""
        operation = parameters.operation

        if operation == "extract":
            return parameters.question_text is not None
        if operation == "query":
            return parameters.question_text is not None
        if operation == "graph":
            return parameters.question_text is not None
        return False

    def get_tool_schema(self) -> ToolResult:
        """Return RAG tool schema"""
        return ToolResult(
            result_type="tool_schema", message=f"RAG tool schema for {self.tool_name}"
        )

    def get_tool_capabilities(self) -> ToolResult:
        """Return RAG tool capabilities"""
        return ToolResult(
            result_type="tool_capabilities",
            message="RAG tool capabilities: supported_file_formats (pdf, docx, txt, md), knowledge_extraction, semantic_search, knowledge_graph_generation, multi_modal_support, real_time_processing",
        )
