"""
Vector Store Interface for EduAgent RAG System

Provides abstract interfaces for vector storage and retrieval operations
that can be implemented by different backends (pgvector, qdrant, etc.).
"""

from abc import ABC, abstractmethod
from typing import Any, TypeVar
from uuid import UUID

from pydantic import BaseModel

# Type definitions
EmbeddingVector = list[float]  # LLM embedding type
DocumentID = UUID | str  # Document identifier type
Score = float  # Similarity score type


class Document(BaseModel):
    """Represents a document stored in the vector store"""

    id: DocumentID
    content: str
    metadata: dict[str, Any] = {}
    embedding: EmbeddingVector | None = None


class SearchResult(BaseModel):
    """Represents a vector search result"""

    document: Document
    score: Score
    distance: float | None = None


class SearchQuery(BaseModel):
    """Represents a vector search query"""

    embedding: EmbeddingVector
    limit: int = 10
    filter_metadata: dict[str, Any] = {}
    score_threshold: float | None = None


class VectorStoreStats(BaseModel):
    """Statistics about the vector store"""

    total_documents: int
    total_vectors: int
    dimension: int | None = None
    backend_info: dict[str, Any] = {}


class VectorStoreConfig(BaseModel):
    """Configuration for vector store implementations"""

    backend: str  # "pgvector", "qdrant", etc.
    connection_string: str | None = None
    collection_name: str = "eduagent_vectors"
    dimension: int | None = None
    index_type: str = "hnsw"  # or "flat", "ivf", etc.
    distance_metric: str = "cosine"  # or "euclidean", "dot"


class VectorStoreError(Exception):
    """Base exception for vector store operations"""


class VectorStoreConnectionError(VectorStoreError):
    """Raised when unable to connect to vector store backend"""


class VectorStoreIndexError(VectorStoreError):
    """Raised when index operations fail"""


class VectorStoreQueryError(VectorStoreError):
    """Raised when query operations fail"""


class VectorStore(ABC):
    """
    Abstract interface for vector storage and retrieval operations.

    This interface defines the contract that all vector store implementations
    must follow, allowing for different backends (pgvector, qdrant, etc.)
    while maintaining a consistent API for the RAG system.
    """

    @abstractmethod
    def __init__(self, config: VectorStoreConfig) -> None:
        """
        Initialize the vector store with configuration.

        Args:
            config: Configuration for the vector store backend
        """

    @abstractmethod
    async def connect(self) -> None:
        """
        Establish connection to the vector store backend.

        Raises:
            VectorStoreConnectionError: If connection fails
        """

    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection to the vector store backend."""

    @abstractmethod
    async def create_index(self, dimension: int) -> None:
        """
        Create vector index for similarity search.

        Args:
            dimension: Dimension of the embedding vectors

        Raises:
            VectorStoreIndexError: If index creation fails
        """

    @abstractmethod
    async def add_documents(self, documents: list[Document]) -> list[DocumentID]:
        """
        Add documents with their embeddings to the vector store.

        Args:
            documents: List of documents to add

        Returns:
            List of document IDs that were added

        Raises:
            VectorStoreError: If document addition fails
        """

    @abstractmethod
    async def add_document(self, document: Document) -> DocumentID:
        """
        Add a single document with its embedding to the vector store.

        Args:
            document: Document to add

        Returns:
            Document ID that was added

        Raises:
            VectorStoreError: If document addition fails
        """

    @abstractmethod
    async def update_document(
        self, document_id: DocumentID, document: Document
    ) -> None:
        """
        Update an existing document in the vector store.

        Args:
            document_id: ID of the document to update
            document: Updated document data

        Raises:
            VectorStoreError: If document update fails
        """

    @abstractmethod
    async def delete_document(self, document_id: DocumentID) -> bool:
        """
        Delete a document from the vector store.

        Args:
            document_id: ID of the document to delete

        Returns:
            True if document was deleted, False if not found

        Raises:
            VectorStoreError: If document deletion fails
        """

    @abstractmethod
    async def search(self, query: SearchQuery) -> list[SearchResult]:
        """
        Search for similar documents using vector similarity.

        Args:
            query: Search query with embedding and parameters

        Returns:
            List of search results sorted by similarity score

        Raises:
            VectorStoreQueryError: If search operation fails
        """

    @abstractmethod
    async def get_document(self, document_id: DocumentID) -> Document | None:
        """
        Retrieve a document by its ID.

        Args:
            document_id: ID of the document to retrieve

        Returns:
            Document if found, None otherwise

        Raises:
            VectorStoreError: If document retrieval fails
        """

    @abstractmethod
    async def get_documents_by_metadata(
        self, metadata_filter: dict[str, Any], limit: int = 100
    ) -> list[Document]:
        """
        Retrieve documents matching metadata criteria.

        Args:
            metadata_filter: Key-value pairs to match in document metadata
            limit: Maximum number of documents to return

        Returns:
            List of matching documents

        Raises:
            VectorStoreError: If metadata query fails
        """

    @abstractmethod
    async def get_stats(self) -> VectorStoreStats:
        """
        Get statistics about the vector store.

        Returns:
            Statistics about the vector store

        Raises:
            VectorStoreError: If stats retrieval fails
        """

    @abstractmethod
    async def clear_collection(self) -> None:
        """
        Clear all documents from the vector store collection.

        Raises:
            VectorStoreError: If clear operation fails
        """

    @abstractmethod
    async def drop_index(self) -> None:
        """
        Drop the vector index.

        Raises:
            VectorStoreIndexError: If index drop fails
        """

    @abstractmethod
    def is_connected(self) -> bool:
        """
        Check if the vector store is connected.

        Returns:
            True if connected, False otherwise
        """


class VectorStoreFactory(ABC):
    """Abstract factory for creating vector store instances."""

    @abstractmethod
    def create_vector_store(self, config: VectorStoreConfig) -> VectorStore:
        """
        Create a vector store instance with the given configuration.

        Args:
            config: Configuration for the vector store

        Returns:
            Configured vector store instance
        """


# Type alias for convenience
VectorStoreType = TypeVar("VectorStoreType", bound=VectorStore)
