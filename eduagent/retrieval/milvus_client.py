"""Milvus client wrapper for dense, sparse, and hybrid retrieval."""
from __future__ import annotations

from pydantic import BaseModel, Field
from pymilvus import (
    AnnSearchRequest,
    Collection,
    CollectionSchema,
    DataType,
    FieldSchema,
    WeightedRanker,
    connections,
    utility,
)

from eduagent.retrieval.models import SearchHit


class HybridWeights(BaseModel):
    dense: float = Field(default=0.5, ge=0.0, le=1.0)
    sparse: float = Field(default=0.5, ge=0.0, le=1.0)


class MilvusConfig(BaseModel):
    host: str = Field(..., description="Milvus host")
    port: int = Field(..., description="Milvus port")
    database: str = Field(default="default")
    collection: str = Field(..., description="Milvus collection name")
    dim: int = Field(..., description="Dense embedding dimension")
    hybrid_weights: HybridWeights = Field(default_factory=HybridWeights)


class MilvusClient:
    def __init__(self, config: MilvusConfig) -> None:
        self.config = config

    def connect(self) -> None:
        connections.connect(
            alias="default",
            host=self.config.host,
            port=self.config.port,
            db_name=self.config.database,
        )

    def ensure_collection(self) -> Collection:
        if utility.has_collection(self.config.collection):
            return Collection(self.config.collection)

        fields = [
            FieldSchema(
                name="chunk_id",
                dtype=DataType.INT64,
                is_primary=True,
                auto_id=False,
            ),
            FieldSchema(name="doc_id", dtype=DataType.INT64),
            FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65535),
            FieldSchema(
                name="dense_vector",
                dtype=DataType.FLOAT_VECTOR,
                dim=self.config.dim,
            ),
            FieldSchema(
                name="sparse_vector",
                dtype=DataType.SPARSE_FLOAT_VECTOR,
            ),
        ]
        schema = CollectionSchema(fields=fields, description="Document chunks")
        collection = Collection(name=self.config.collection, schema=schema)
        collection.create_index(
            field_name="dense_vector",
            index_params={
                "index_type": "HNSW",
                "metric_type": "IP",
                "params": {"M": 16, "efConstruction": 200},
            },
        )
        collection.create_index(
            field_name="sparse_vector",
            index_params={"index_type": "SPARSE_INVERTED_INDEX", "metric_type": "IP"},
        )
        collection.load()
        return collection

    def insert_chunks(
        self,
        collection: Collection,
        *,
        chunk_ids: list[int],
        doc_ids: list[int],
        texts: list[str],
        dense_vectors: list[list[float]],
        sparse_vectors: list[dict[int, float]],
    ) -> None:
        collection.insert(
            [
                chunk_ids,
                doc_ids,
                texts,
                dense_vectors,
                sparse_vectors,
            ]
        )

    def dense_search(
        self,
        collection: Collection,
        *,
        dense_vector: list[float],
        limit: int,
    ) -> list[SearchHit]:
        results = collection.search(
            data=[dense_vector],
            anns_field="dense_vector",
            param={"metric_type": "IP", "params": {"nprobe": 10}},
            limit=limit,
            output_fields=["doc_id", "text"],
        )
        hits = results[0]
        return [
            SearchHit(
                chunk_id=hit.id,
                doc_id=hit.entity.get("doc_id"),
                text=hit.entity.get("text"),
                score=hit.score,
            )
            for hit in hits
        ]

    def sparse_search(
        self,
        collection: Collection,
        *,
        sparse_vector: dict[int, float],
        limit: int,
    ) -> list[SearchHit]:
        results = collection.search(
            data=[sparse_vector],
            anns_field="sparse_vector",
            param={"metric_type": "IP"},
            limit=limit,
            output_fields=["doc_id", "text"],
        )
        hits = results[0]
        return [
            SearchHit(
                chunk_id=hit.id,
                doc_id=hit.entity.get("doc_id"),
                text=hit.entity.get("text"),
                score=hit.score,
            )
            for hit in hits
        ]

    def hybrid_search(
        self,
        collection: Collection,
        *,
        dense_vector: list[float],
        sparse_vector: dict[int, float],
        limit: int,
    ) -> list[SearchHit]:
        dense_req = AnnSearchRequest(
            data=[dense_vector],
            anns_field="dense_vector",
            param={"metric_type": "IP", "params": {"nprobe": 10}},
            limit=limit,
        )
        sparse_req = AnnSearchRequest(
            data=[sparse_vector],
            anns_field="sparse_vector",
            param={"metric_type": "IP"},
            limit=limit,
        )
        weights = self.config.hybrid_weights
        results = collection.hybrid_search(
            reqs=[dense_req, sparse_req],
            rerank=WeightedRanker(weights.dense, weights.sparse),
            limit=limit,
            output_fields=["doc_id", "text"],
        )
        hits = results[0]
        return [
            SearchHit(
                chunk_id=hit.id,
                doc_id=hit.entity.get("doc_id"),
                text=hit.entity.get("text"),
                score=hit.score,
            )
            for hit in hits
        ]
