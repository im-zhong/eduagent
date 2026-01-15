"""Retrieval API endpoints for indexing and search."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from eduagent.documents.repository import list_document_chunks
from eduagent.logger import get_logger
from eduagent.retrieval.milvus_client import MilvusClient, MilvusConfig
from eduagent.retrieval.models import (
    IndexChunksResponse,
    SearchChunksRequest,
    SearchChunksResponse,
)
from eduagent.settings import settings
from eduagent.storage.engine import get_async_session
from eduagent.tools.bge_client import (
    BGEClient,
    BGEClientConfig,
    EmbeddingRequest,
    RerankRequest,
)

logger = get_logger(__name__, component="api.retrieval")

router = APIRouter()


def _bge_client() -> BGEClient:
    """Build a BGE client with current settings."""
    return BGEClient(
        BGEClientConfig(
            base_url=settings.bge.base_url,
            timeout_seconds=settings.bge.timeout_seconds,
        )
    )


def _milvus_client() -> MilvusClient:
    """Build and connect a Milvus client for retrieval."""
    config = MilvusConfig(
        host=settings.milvus.host,
        port=settings.milvus.port,
        database=settings.milvus.database,
        collection=settings.milvus.collection,
        dim=settings.milvus.dim,
    )
    client = MilvusClient(config)
    client.connect()
    return client


@router.post(
    "/index/chunks/{doc_id}",
    response_model=IndexChunksResponse,
    summary="Index document chunks into Milvus",
)
async def index_chunks(
    doc_id: int,
    session: AsyncSession = Depends(get_async_session),
) -> IndexChunksResponse:
    """Embed document chunks and upsert into Milvus for retrieval."""
    chunks = await list_document_chunks(session, doc_id)
    if not chunks:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No chunks found for document {doc_id}",
        )

    texts = [chunk.text for chunk in chunks]
    bge = _bge_client()
    embeddings = await bge.embed_hybrid(EmbeddingRequest(texts=texts))

    milvus = _milvus_client()
    collection = milvus.ensure_collection()
    milvus.insert_chunks(
        collection,
        chunk_ids=[chunk.id for chunk in chunks],
        doc_ids=[chunk.doc_id for chunk in chunks],
        texts=texts,
        dense_vectors=embeddings.dense_embeddings,
        sparse_vectors=[
            {idx: val for idx, val in zip(embed.indices, embed.values)}
            for embed in embeddings.sparse_embeddings
        ],
    )
    return IndexChunksResponse(doc_id=doc_id, chunk_count=len(chunks))


@router.post(
    "/search/chunks",
    response_model=SearchChunksResponse,
    summary="Sparse search over chunks",
)
async def search_chunks_sparse(
    payload: SearchChunksRequest,
    session: AsyncSession = Depends(get_async_session),
) -> SearchChunksResponse:
    """Run sparse retrieval using learned lexical embeddings."""
    bge = _bge_client()
    query_embeddings = await bge.embed_sparse(EmbeddingRequest(texts=[payload.query]))

    milvus = _milvus_client()
    collection = milvus.ensure_collection()
    hits = milvus.sparse_search(
        collection,
        sparse_vector={
            idx: val
            for idx, val in zip(
                query_embeddings.sparse_embeddings[0].indices,
                query_embeddings.sparse_embeddings[0].values,
            )
        },
        limit=payload.top_k,
    )
    return SearchChunksResponse(query=payload.query, hits=hits)


@router.post(
    "/search/chunks/dense",
    response_model=SearchChunksResponse,
    summary="Dense search over chunks",
)
async def search_chunks_dense(
    payload: SearchChunksRequest,
    session: AsyncSession = Depends(get_async_session),
) -> SearchChunksResponse:
    """Run dense retrieval without hybrid weighting."""
    bge = _bge_client()
    query_embeddings = await bge.embed(EmbeddingRequest(texts=[payload.query]))

    milvus = _milvus_client()
    collection = milvus.ensure_collection()
    hits = milvus.dense_search(
        collection,
        dense_vector=query_embeddings.embeddings[0],
        limit=payload.top_k,
    )
    return SearchChunksResponse(query=payload.query, hits=hits)


@router.post(
    "/search/chunks/hybrid",
    response_model=SearchChunksResponse,
    summary="Hybrid search over chunks with reranking",
)
async def search_chunks_hybrid(
    payload: SearchChunksRequest,
    session: AsyncSession = Depends(get_async_session),
) -> SearchChunksResponse:
    """Run hybrid retrieval and rerank the results using BGE."""
    bge = _bge_client()
    query_embeddings = await bge.embed_hybrid(EmbeddingRequest(texts=[payload.query]))

    milvus = _milvus_client()
    collection = milvus.ensure_collection()
    hits = milvus.hybrid_search(
        collection,
        dense_vector=query_embeddings.dense_embeddings[0],
        sparse_vector={
            idx: val
            for idx, val in zip(
                query_embeddings.sparse_embeddings[0].indices,
                query_embeddings.sparse_embeddings[0].values,
            )
        },
        limit=payload.top_k,
    )

    if not hits:
        return SearchChunksResponse(query=payload.query, hits=[])

    passages = [hit.text for hit in hits]
    rerank_scores = await bge.rerank(
        RerankRequest(query=payload.query, passages=passages)
    )

    ranked = sorted(
        zip(hits, rerank_scores.scores, strict=False),
        key=lambda pair: pair[1],
        reverse=True,
    )
    final_hits = [
        hit.model_copy(update={"score": score}) for hit, score in ranked
    ]
    return SearchChunksResponse(query=payload.query, hits=final_hits)
