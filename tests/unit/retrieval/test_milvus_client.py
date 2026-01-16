"""Integration-style unit test for Milvus client connectivity."""
from __future__ import annotations

from uuid import uuid4

from pymilvus import utility

from eduagent.retrieval.milvus_client import HybridWeights, MilvusClient, MilvusConfig
from eduagent.settings import settings


def test_milvus_connect_and_create_collection() -> None:
    """Ensure Milvus is reachable and can create a collection.

    This test intentionally connects to the real Milvus service in the dev
    container to catch configuration/network issues early.
    """
    collection_name = f"test_chunks_{uuid4().hex}"
    config = MilvusConfig(
        host=settings.milvus.host,
        port=settings.milvus.port,
        database=settings.milvus.database,
        collection=collection_name,
        dim=settings.milvus.dim,
        hybrid_weights=HybridWeights(
            dense=settings.milvus.hybrid_dense_weight,
            sparse=settings.milvus.hybrid_sparse_weight,
        ),
    )
    client = MilvusClient(config)
    client.connect()
    try:
        client.ensure_collection()
        assert utility.has_collection(collection_name)
    finally:
        if utility.has_collection(collection_name):
            utility.drop_collection(collection_name)
