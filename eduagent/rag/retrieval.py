import uuid
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from eduagent.db.models import AbilityTarget, CommonMistake, KnowledgePoint, Textbook
from eduagent.db.service import DatabaseService


class DocumentProcessor(ABC):
    """Abstract base class for document processing"""

    @abstractmethod
    def extract_text_and_images(self, file_path: Path) -> dict[str, Any]:
        """Extract text and images from document file"""

    @abstractmethod
    def segment_document(self, content: dict[str, Any]) -> list[dict[str, Any]]:
        """Segment document into logical sections (chapters, sections)"""


class KnowledgeExtractionStrategy(ABC):
    """Abstract strategy for knowledge extraction from documents"""

    @abstractmethod
    def extract_knowledge_points(
        self, document_sections: list[dict[str, Any]], textbook_id: uuid.UUID
    ) -> list[KnowledgePoint]:
        """Extract knowledge points from document sections"""

    @abstractmethod
    def extract_ability_targets(
        self, knowledge_point: KnowledgePoint, context: dict[str, Any]
    ) -> list[AbilityTarget]:
        """Extract ability targets for a knowledge point"""

    @abstractmethod
    def extract_common_mistakes(
        self, knowledge_point: KnowledgePoint, context: dict[str, Any]
    ) -> list[CommonMistake]:
        """Extract common mistakes for a knowledge point"""


class RetrievalStrategy(ABC):
    """Abstract strategy for knowledge retrieval from database"""

    @abstractmethod
    def retrieve_relevant_knowledge(
        self,
        user_query: str,
        textbook_id: uuid.UUID | None,
        knowledge_point_ids: list[uuid.UUID] | None,
        filters: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Retrieve relevant knowledge based on query and context"""

    @abstractmethod
    def calculate_relevance_scores(
        self, query: str, knowledge_items: list[Any]
    ) -> dict[str, float]:
        """Calculate relevance scores for knowledge items"""

    @abstractmethod
    def rank_results(
        self, results: dict[str, Any], ranking_criteria: dict[str, Any]
    ) -> dict[str, Any]:
        """Rank retrieval results based on criteria"""


class RAGSystem:
    """
    RAG system for educational content extraction and retrieval
    Uses strategy pattern for flexible knowledge extraction and retrieval
    """

    def __init__(
        self,
        document_processor: DocumentProcessor,
        extraction_strategy: KnowledgeExtractionStrategy,
        retrieval_strategy: RetrievalStrategy,
        db_service: DatabaseService,
    ) -> None:
        self.document_processor = document_processor
        self.extraction_strategy = extraction_strategy
        self.retrieval_strategy = retrieval_strategy
        self.db_service = db_service
        self.available_strategies: dict[str, Any] = {}

    def set_extraction_strategy(self, strategy: KnowledgeExtractionStrategy) -> None:
        """Set the knowledge extraction strategy"""
        self.extraction_strategy = strategy

    def set_retrieval_strategy(self, strategy: RetrievalStrategy) -> None:
        """Set the knowledge retrieval strategy"""
        self.retrieval_strategy = strategy

    def register_strategy(self, strategy_name: str, strategy: object) -> None:
        """Register a strategy for dynamic switching"""
        self.available_strategies[strategy_name] = strategy

    def extract_document_to_database(
        self, file_path: Path, textbook_metadata: dict[str, Any]
    ) -> Textbook:
        """
        Extract document content and store knowledge in database
        Returns the created Textbook object
        """
        # Step 1: Process document
        content = self.document_processor.extract_text_and_images(file_path)
        sections = self.document_processor.segment_document(content)

        # Step 2: Create textbook record
        textbook = Textbook(
            title=textbook_metadata.get("title", "Unknown"),
            author=textbook_metadata.get("author", ""),
            publisher=textbook_metadata.get("publisher", ""),
            subject=textbook_metadata.get("subject"),
            grade_level=textbook_metadata.get("grade_level", ""),
            file_path=str(file_path),
            file_type=file_path.suffix,
            extraction_status="processing",
        )
        textbook = self.db_service.create(textbook)
        assert isinstance(textbook, Textbook), (
            "Created textbook must be of type Textbook"
        )

        # Step 3: Extract knowledge points using strategy
        knowledge_points = self.extraction_strategy.extract_knowledge_points(
            sections, textbook.id
        )

        # Step 4: Store knowledge points and related data
        for kp in knowledge_points:
            stored_kp = self.db_service.create(kp)
            assert isinstance(stored_kp, KnowledgePoint), (
                "Created knowledge point must be of type KnowledgePoint"
            )

            # Extract ability targets using strategy
            ability_targets = self.extraction_strategy.extract_ability_targets(
                stored_kp, {"textbook_id": textbook.id}
            )
            for at in ability_targets:
                self.db_service.create(at)

            # Extract common mistakes using strategy
            common_mistakes = self.extraction_strategy.extract_common_mistakes(
                stored_kp, {"textbook_id": textbook.id}
            )
            for cm in common_mistakes:
                self.db_service.create(cm)

        # Step 5: Update textbook status
        self.db_service.update_textbook_extraction_status(textbook.id, "completed")

        return textbook

    def retrieve_knowledge_for_query(
        self,
        user_query: str,
        textbook_id: uuid.UUID | None = None,
        knowledge_point_ids: list[uuid.UUID] | None = None,
        filters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Retrieve relevant knowledge from database for a user query
        """
        # Retrieve relevant knowledge using retrieval strategy
        knowledge_context = self.retrieval_strategy.retrieve_relevant_knowledge(
            user_query, textbook_id, knowledge_point_ids, filters
        )

        return {
            "query": user_query,
            "knowledge_context": knowledge_context,
            "retrieved_at": datetime.now(UTC),
        }

    def get_available_strategies(self) -> dict[str, Any]:
        """Get information about available strategies"""
        return {
            "extraction_strategy": type(self.extraction_strategy).__name__,
            "retrieval_strategy": type(self.retrieval_strategy).__name__,
            "available_strategies": list(self.available_strategies.keys()),
        }


class RAGTool:
    """
    Tool interface for RAG system that can be used by LangChain agents
    Supports multiple retrieval strategies
    """

    def __init__(self, rag_system: RAGSystem) -> None:
        self.rag_system = rag_system
        self.name = "rag_knowledge_tool"
        self.description = "Extract knowledge from documents and retrieve relevant educational content using multiple strategies"

    def switch_extraction_strategy(self, strategy_name: str) -> bool:
        """Switch to a different extraction strategy"""
        if strategy_name in self.rag_system.available_strategies:
            strategy = self.rag_system.available_strategies[strategy_name]
            if isinstance(strategy, KnowledgeExtractionStrategy):
                self.rag_system.set_extraction_strategy(strategy)
                return True
        return False

    def switch_retrieval_strategy(self, strategy_name: str) -> bool:
        """Switch to a different retrieval strategy"""
        if strategy_name in self.rag_system.available_strategies:
            strategy = self.rag_system.available_strategies[strategy_name]
            if isinstance(strategy, RetrievalStrategy):
                self.rag_system.set_retrieval_strategy(strategy)
                return True
        return False

    def get_current_strategies(self) -> dict[str, Any]:
        """Get information about current strategies"""
        return self.rag_system.get_available_strategies()

    def extract_knowledge(
        self, file_path: str, textbook_metadata: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Tool method: Extract knowledge from a document and store in database
        """
        textbook = self.rag_system.extract_document_to_database(
            Path(file_path), textbook_metadata
        )
        return {
            "textbook_id": str(textbook.id),
            "status": "completed",
            "extracted_knowledge_points": len(textbook.knowledge_points),
        }

    def query_knowledge(
        self,
        user_query: str,
        textbook_id: str | None = None,
        filters: dict[str, Any] | None = None,
        retrieval_strategy: str | None = None,
    ) -> dict[str, Any]:
        """
        Tool method: Query the knowledge base for relevant information
        Optionally specify retrieval strategy
        """
        uuid_textbook_id = uuid.UUID(textbook_id) if textbook_id else None

        # Switch strategy if specified
        if retrieval_strategy:
            self.switch_retrieval_strategy(retrieval_strategy)

        result = self.rag_system.retrieve_knowledge_for_query(
            user_query, uuid_textbook_id, None, filters
        )

        return {
            "query": result["query"],
            "knowledge_context": result["knowledge_context"],
            "retrieved_at": result["retrieved_at"].isoformat(),
            "strategy_used": type(self.rag_system.retrieval_strategy).__name__,
        }

    def get_knowledge_graph(self, textbook_id: str) -> dict[str, Any]:
        """
        Tool method: Retrieve knowledge graph data for a textbook
        """
        uuid_textbook_id = uuid.UUID(textbook_id)
        return self.rag_system.db_service.get_knowledge_graph_data(uuid_textbook_id)

    def list_available_strategies(self) -> dict[str, Any]:
        """List all available extraction and retrieval strategies"""
        return {
            "extraction_strategies": ["glm", "rule_based", "hybrid"],
            "retrieval_strategies": ["semantic", "keyword", "hybrid", "educational"],
            "current_strategies": self.get_current_strategies(),
        }
