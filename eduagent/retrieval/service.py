"""Retrieval service for RAG-based context retrieval.

This service provides a high-level interface for retrieving relevant document chunks
using BGE-M3 embeddings and Milvus vector search.

Architecture:
    Query → BGE Embedding Service → Dense/Sparse Vectors → Milvus Search → Retrieved Chunks
"""
from __future__ import annotations

from pymilvus import Collection

from eduagent.retrieval.milvus_client import (
    HybridWeights,
    MilvusClient,
    MilvusConfig,
    SearchHit,
)
from eduagent.settings import settings
from eduagent.tools.bge_client import (
    BGEClient,
    BGEClientConfig,
    DenseEmbeddingsResponse,
    HybridEmbeddingsResponse,
    SparseEmbedding,
)


class RetrievalService:
    """High-level retrieval service combining BGE embeddings and Milvus search."""

    def __init__(
        self,
        bge_client: BGEClient,
        milvus_client: MilvusClient,
    ) -> None:
        self.bge_client = bge_client
        self.milvus_client = milvus_client
        self._collection: Collection | None = None

    @property
    def collection(self) -> Collection:
        """Get or create Milvus collection."""
        if self._collection is None:
            self.milvus_client.connect()
            self._collection = self.milvus_client.ensure_collection()
        return self._collection

    async def retrieve_relevant_chunks(
        self,
        query: str,
        doc_id: int | None = None,
        top_k: int = 5,
        use_hybrid: bool = True,
    ) -> list[SearchHit]:
        """Retrieve relevant document chunks for a given query.

        Args:
            query: The search query text
            doc_id: Optional document ID to filter results
            top_k: Number of chunks to retrieve (default: 5)
            use_hybrid: Use hybrid dense+sparse search (default: True)

        Returns:
            List of SearchHit objects with chunk_id, doc_id, text, and score

        Note:
            Uses BGE-M3 for embedding (dense+sparse if use_hybrid=True).
            Searches Milvus for nearest neighbors.
            If doc_id is provided, filters results to that document only.
        """
        # Step 1: Get query embeddings from BGE service
        if use_hybrid:
            bge_response: HybridEmbeddingsResponse = await self.bge_client.embed_hybrid(
                EmbeddingRequest(texts=[query])
            )
            dense_vector = bge_response.dense_embeddings[0]
            sparse_dict = _sparse_to_dict(bge_response.sparse_embeddings[0])
        else:
            dense_response: DenseEmbeddingsResponse = await self.bge_client.embed(
                EmbeddingRequest(texts=[query])
            )
            dense_vector = dense_response.embeddings[0]
            sparse_dict = {}

        # Step 2: Search Milvus
        if use_hybrid:
            hits = self.milvus_client.hybrid_search(
                self.collection,
                dense_vector=dense_vector,
                sparse_vector=sparse_dict,
                limit=top_k,
            )
        else:
            hits = self.milvus_client.dense_search(
                self.collection,
                dense_vector=dense_vector,
                limit=top_k,
            )

        # Step 3: Filter by doc_id if specified
        if doc_id is not None:
            hits = [hit for hit in hits if hit.doc_id == doc_id]

        return hits


def _sparse_to_dict(sparse: SparseEmbedding) -> dict[int, float]:
    """Convert sparse embedding format to dictionary.

    BGE returns sparse as: SparseEmbedding(indices=[], values=[])
    Milvus expects: dict[int, float]

    Args:
        sparse: BGE sparse embedding

    Returns:
        Dictionary mapping indices to values
    """
    return dict(zip(sparse.indices, sparse.values))


def get_retrieval_service() -> RetrievalService:
    """Factory function to create a RetrievalService with configured clients."""
    bge_client = BGEClient(
        config=BGEClientConfig(
            base_url=settings.bge.base_url,
            timeout_seconds=settings.bge.timeout_seconds,
        )
    )

    milvus_client = MilvusClient(
        config=MilvusConfig(
            host=settings.milvus.host,
            port=settings.milvus.port,
            database=settings.milvus.database,
            collection=settings.milvus.collection,
            dim=settings.milvus.dim,
        )
    )

    return RetrievalService(bge_client=bge_client, milvus_client=milvus_client)


# Re-export for convenience
from eduagent.tools.bge_client import EmbeddingRequest
