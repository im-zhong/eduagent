"""Schemas for retrieval APIs."""
from __future__ import annotations

from pydantic import BaseModel, Field


class IndexChunksResponse(BaseModel):
    doc_id: int
    chunk_count: int


class SearchChunksRequest(BaseModel):
    query: str = Field(..., min_length=1)
    top_k: int = Field(default=5, gt=0, le=50)


class SearchHit(BaseModel):
    chunk_id: int
    doc_id: int
    text: str
    score: float


class SearchChunksResponse(BaseModel):
    query: str
    hits: list[SearchHit]
