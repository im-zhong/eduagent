from __future__ import annotations

import uuid
from collections.abc import Iterator
from contextlib import suppress
from typing import Any, cast

import pytest
from pymilvus import connections as milvus_connections
from pymilvus import utility as milvus_utility

from eduagent.settings import MilvusConfig, settings
from eduagent.storage.milvus_store import EmbeddingRecord, MilvusVectorStore

_MILVUS_CONNECTIONS = cast(Any, milvus_connections)
_MILVUS_UTILITY = cast(Any, milvus_utility)


def _make_config(prefix: str) -> tuple[MilvusConfig, str]:
    unique = uuid.uuid4().hex
    collection = f"test_{prefix}_{unique}"
    alias = f"alias_{prefix}_{unique}"
    config = settings.milvus.model_copy(
        update={
            "collection": collection,
        }
    )
    return config, alias


def _list_connections() -> list[str]:
    return cast(list[str], _MILVUS_CONNECTIONS.list_connections())


def _has_collection(collection: str, *, alias: str) -> bool:
    return bool(_MILVUS_UTILITY.has_collection(collection, using=alias))


def _list_collections(alias: str) -> list[str]:
    return cast(list[str], _MILVUS_UTILITY.list_collections(using=alias))


@pytest.fixture
def milvus_env() -> Iterator[tuple[MilvusConfig, str]]:
    config, alias = _make_config("milvus_store")
    try:
        yield config, alias
    finally:
        if alias not in _list_connections():
            _MILVUS_CONNECTIONS.connect(
                alias=alias,
                host=config.host,
                port=str(config.port),
                user=config.username or "",
                password=config.password or "",
                db_name=config.database,
            )
        if _has_collection(config.collection, alias=alias):
            _MILVUS_UTILITY.drop_collection(config.collection, using=alias)
        with suppress(Exception):
            _MILVUS_CONNECTIONS.disconnect(alias)


def test_milvus_store_ensure_collection(milvus_env: tuple[MilvusConfig, str]) -> None:
    config, alias = milvus_env
    store = MilvusVectorStore(config=config, alias=alias, dim=8)

    collection = store.ensure_collection()
    collection_any = cast(Any, collection)

    assert collection.name == config.collection
    assert collection_any.has_index()
    assert config.collection in _list_collections(alias)


def test_milvus_store_reuses_existing_connection(
    milvus_env: tuple[MilvusConfig, str],
) -> None:
    config, alias = milvus_env
    store = MilvusVectorStore(config=config, alias=alias)

    store.ensure_collection()
    connection_count_before = len(_list_connections())
    store.ensure_collection()
    connection_count_after = len(_list_connections())

    assert connection_count_after == connection_count_before
    assert config.collection in _list_collections(alias)


def test_milvus_store_insert_and_search(milvus_env: tuple[MilvusConfig, str]) -> None:
    config, alias = milvus_env
    store = MilvusVectorStore(config=config, alias=alias, dim=3)
    records = [
        EmbeddingRecord(
            record_id="chunk-1",
            text="first chunk",
            embedding=[0.1, 0.2, 0.3],
            metadata={"page": 1},
        ),
        EmbeddingRecord(
            record_id="chunk-2",
            text="second chunk",
            embedding=[0.3, 0.1, 0.8],
            metadata={"page": 2},
        ),
    ]

    inserted = store.insert_records(records)

    assert inserted == len(records)
    collection = store.ensure_collection()
    collection_any = cast(Any, collection)
    collection_any.flush()
    collection_any.load()

    results = store.search(records[0].embedding, limit=2)

    assert len(results) >= 1
    assert results[0]["id"] == "chunk-1"
    assert results[0]["text"] == "first chunk"
    assert results[0]["metadata"]["page"] == 1
