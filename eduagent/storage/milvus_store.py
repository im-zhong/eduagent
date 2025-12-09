from __future__ import annotations

from collections.abc import Iterable
from typing import Any, cast

from loguru import logger
from pydantic import BaseModel, Field
from pymilvus import (
    Collection,
    CollectionSchema,
    DataType,
    FieldSchema,
)
from pymilvus import (
    connections as milvus_connections,
)
from pymilvus import (
    utility as milvus_utility,
)

from eduagent.settings import MilvusConfig, settings

_MILVUS_CONNECTIONS = cast(Any, milvus_connections)
_MILVUS_UTILITY = cast(Any, milvus_utility)


class EmbeddingRecord(BaseModel):
    record_id: str = Field(..., description="Unique chunk identifier")
    text: str = Field(..., description="Original chunk text")
    embedding: list[float] = Field(..., description="Dense embedding vector")
    metadata: dict[str, Any] = Field(default_factory=dict)


class MilvusVectorStore:
    """Minimal helper around pymilvus to manage quiz collections."""

    def __init__(
        self,
        config: MilvusConfig | None = None,
        alias: str = "eduagent",
        dim: int = 1536,
    ) -> None:
        self.config = config or settings.milvus
        self.alias = alias
        self.dim = dim
        self.collection_name = self.config.collection

    def connect(self) -> None:
        existing_connections = cast(list[str], _MILVUS_CONNECTIONS.list_connections())
        if self.alias in existing_connections:
            return
        logger.info("Connecting to Milvus at %s:%s", self.config.host, self.config.port)
        _MILVUS_CONNECTIONS.connect(
            alias=self.alias,
            host=self.config.host,
            port=str(self.config.port),
            user=self.config.username or "",
            password=self.config.password or "",
            db_name=self.config.database,
        )

    def ensure_collection(self) -> Collection:
        self.connect()
        has_collection = bool(
            _MILVUS_UTILITY.has_collection(self.collection_name, using=self.alias)
        )
        if not has_collection:
            logger.info("Creating Milvus collection %s", self.collection_name)
            fields = [
                FieldSchema(
                    name="id",
                    dtype=DataType.VARCHAR,
                    max_length=64,
                    is_primary=True,
                ),
                FieldSchema(
                    name="text",
                    dtype=DataType.VARCHAR,
                    max_length=2048,
                ),
                FieldSchema(
                    name="embedding",
                    dtype=DataType.FLOAT_VECTOR,
                    dim=self.dim,
                ),
                FieldSchema(
                    name="metadata",
                    dtype=DataType.JSON,
                ),
            ]
            schema = CollectionSchema(
                fields=fields,
                description="EduAgent quiz knowledge collection",
            )
            _ = Collection(
                name=self.collection_name,
                schema=schema,
                using=self.alias,
                shards_num=2,
            )
        collection_obj: Any = Collection(name=self.collection_name, using=self.alias)
        if not collection_obj.has_index():
            collection_obj.create_index(
                field_name="embedding",
                index_params={
                    "index_type": "IVF_FLAT",
                    "metric_type": "COSINE",
                    "params": {"nlist": 1024},
                },
            )
        collection_obj.load()
        return cast(Collection, collection_obj)

    def insert_records(self, records: list[EmbeddingRecord]) -> int:
        if not records:
            return 0
        collection = self.ensure_collection()
        insert_data = [
            [record.record_id for record in records],
            [record.text for record in records],
            [record.embedding for record in records],
            [record.metadata for record in records],
        ]
        collection_obj = cast(Any, collection)
        collection_obj.insert(insert_data)
        return len(records)

    def search(
        self,
        embedding: list[float],
        *,
        limit: int = 5,
        expr: str | None = None,
    ) -> list[dict[str, Any]]:
        collection = self.ensure_collection()
        search_params = {"metric_type": "COSINE", "params": {"nprobe": 10}}
        collection_obj = cast(Any, collection)
        results = collection_obj.search(
            data=[embedding],
            anns_field="embedding",
            param=search_params,
            limit=limit,
            expr=expr,
            output_fields=["text", "metadata"],
        )
        hits_iterable = cast(Iterable[Iterable[Any]], results)
        return [
            {
                "id": hit.id,
                "score": hit.score,
                "text": hit.entity.get("text"),
                "metadata": hit.entity.get("metadata"),
            }
            for hits in hits_iterable
            for hit in hits
        ]


milvus_store = MilvusVectorStore()
