"""Client for the BGE-M3 embedding/rerank microservice."""
from __future__ import annotations

import httpx
from pydantic import BaseModel, Field


class EmbeddingRequest(BaseModel):
    texts: list[str]


class DenseEmbeddingsResponse(BaseModel):
    embeddings: list[list[float]]


class SparseEmbedding(BaseModel):
    indices: list[int]
    values: list[float]


class SparseEmbeddingsResponse(BaseModel):
    sparse_embeddings: list[SparseEmbedding]


class HybridEmbeddingsResponse(BaseModel):
    dense_embeddings: list[list[float]]
    sparse_embeddings: list[SparseEmbedding]


class RerankRequest(BaseModel):
    query: str
    passages: list[str]
    normalize: bool = True


class RerankResponse(BaseModel):
    scores: list[float]


class BGEClientConfig(BaseModel):
    base_url: str = Field(..., description="BGE service base URL")
    timeout_seconds: float = Field(default=30.0, gt=0)


class BGEClient:
    def __init__(self, config: BGEClientConfig) -> None:
        self.config = config

    async def embed(self, request: EmbeddingRequest) -> DenseEmbeddingsResponse:
        async with httpx.AsyncClient(
            base_url=self.config.base_url,
            timeout=self.config.timeout_seconds,
        ) as client:
            response = await client.post(
                "/v1/embeddings", json=request.model_dump()
            )
        response.raise_for_status()
        return DenseEmbeddingsResponse.model_validate(response.json())

    async def embed_sparse(
        self, request: EmbeddingRequest
    ) -> SparseEmbeddingsResponse:
        async with httpx.AsyncClient(
            base_url=self.config.base_url,
            timeout=self.config.timeout_seconds,
        ) as client:
            response = await client.post(
                "/v1/embeddings/sparse", json=request.model_dump()
            )
        response.raise_for_status()
        return SparseEmbeddingsResponse.model_validate(response.json())

    async def embed_hybrid(
        self, request: EmbeddingRequest
    ) -> HybridEmbeddingsResponse:
        async with httpx.AsyncClient(
            base_url=self.config.base_url,
            timeout=self.config.timeout_seconds,
        ) as client:
            response = await client.post(
                "/v1/embeddings/hybrid", json=request.model_dump()
            )
        response.raise_for_status()
        return HybridEmbeddingsResponse.model_validate(response.json())

    async def rerank(self, request: RerankRequest) -> RerankResponse:
        async with httpx.AsyncClient(
            base_url=self.config.base_url,
            timeout=self.config.timeout_seconds,
        ) as client:
            response = await client.post("/v1/rerank", json=request.model_dump())
        response.raise_for_status()
        return RerankResponse.model_validate(response.json())
