"""
Vector Store Module for EduAgent

Provides interfaces and implementations for vector storage and retrieval
operations that support the RAG system and other components requiring
vector similarity search capabilities.

This module follows a pluggable architecture allowing different backends
(pgvector, qdrant, etc.) while maintaining a consistent API.
"""

from .base import (
    Document,
    DocumentID,
    EmbeddingVector,
    Score,
    SearchQuery,
    SearchResult,
    VectorStore,
    VectorStoreConfig,
    VectorStoreConnectionError,
    VectorStoreError,
    VectorStoreFactory,
    VectorStoreIndexError,
    VectorStoreQueryError,
    VectorStoreStats,
    VectorStoreType,
)
from .factory import (
    DefaultVectorStoreFactory,
    create_vector_store,
    get_vector_store_factory,
    register_backend,
)

__all__ = [
    # Factory functions
    "DefaultVectorStoreFactory",
    # Core types and interfaces
    "Document",
    "DocumentID",
    "EmbeddingVector",
    "Score",
    "SearchQuery",
    "SearchResult",
    "VectorStore",
    "VectorStoreConfig",
    # Exception types
    "VectorStoreConnectionError",
    "VectorStoreError",
    "VectorStoreFactory",
    "VectorStoreIndexError",
    "VectorStoreQueryError",
    "VectorStoreStats",
    "VectorStoreType",
    "create_vector_store",
    "get_vector_store_factory",
    "register_backend",
]
