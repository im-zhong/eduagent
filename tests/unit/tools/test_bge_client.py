from __future__ import annotations

import pytest

from eduagent.settings import settings
from eduagent.tools.bge_client import (
    BGEClient,
    BGEClientConfig,
    EmbeddingRequest,
    RerankRequest,
)


def _client() -> BGEClient:
    config = BGEClientConfig(
        base_url=settings.bge.base_url,
        timeout_seconds=settings.bge.timeout_seconds,
    )
    return BGEClient(config)


@pytest.mark.asyncio
async def test_bge_embed() -> None:
    client = _client()
    result = await client.embed(EmbeddingRequest(texts=["hello world"]))
    assert len(result.embeddings) == 1
    assert len(result.embeddings[0]) > 0
    print(len(result.embeddings[0]))


@pytest.mark.asyncio
async def test_bge_embed_sparse() -> None:
    client = _client()
    result = await client.embed_sparse(EmbeddingRequest(texts=["hello world"]))
    assert len(result.sparse_embeddings) == 1
    assert len(result.sparse_embeddings[0].indices) == len(
        result.sparse_embeddings[0].values
    )


@pytest.mark.asyncio
async def test_bge_embed_hybrid() -> None:
    client = _client()
    result = await client.embed_hybrid(EmbeddingRequest(texts=["hello world"]))
    assert len(result.dense_embeddings) == 1
    assert len(result.sparse_embeddings) == 1


@pytest.mark.asyncio
async def test_bge_rerank() -> None:
    client = _client()
    result = await client.rerank(
        RerankRequest(query="hello", passages=["a", "b"], normalize=True)
    )
    assert len(result.scores) == 2
