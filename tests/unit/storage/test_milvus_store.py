from __future__ import annotations

from unittest.mock import MagicMock

from _pytest.monkeypatch import MonkeyPatch

from eduagent.settings import MilvusConfig
from eduagent.storage.milvus_store import MilvusVectorStore

EXPECTED_COLLECTION_CREATIONS = 2


def test_milvus_store_ensure_collection(monkeypatch: MonkeyPatch) -> None:
    config = MilvusConfig(host="milvus", port=19530)
    store = MilvusVectorStore(config=config, alias="test-alias", dim=8)

    mock_connections = MagicMock()
    mock_connections.list_connections.return_value = []
    monkeypatch.setattr(
        "eduagent.storage.milvus_store._MILVUS_CONNECTIONS", mock_connections
    )

    created_collections: list[tuple[tuple[object, ...], dict[str, object]]] = []
    collection_instance = MagicMock()
    collection_instance.has_index.return_value = False
    collection_instance.create_index.return_value = None

    def fake_collection(*args: object, **kwargs: object) -> MagicMock:
        created_collections.append((args, kwargs))
        return collection_instance

    def always_false(*_args: object, **_kwargs: object) -> bool:
        return False

    monkeypatch.setattr(
        "eduagent.storage.milvus_store._MILVUS_UTILITY.has_collection", always_false
    )
    monkeypatch.setattr("eduagent.storage.milvus_store.Collection", fake_collection)

    returned = store.ensure_collection()

    assert returned is collection_instance
    assert mock_connections.connect.called
    assert collection_instance.create_index.called
    assert collection_instance.load.called
    assert len(created_collections) == EXPECTED_COLLECTION_CREATIONS


def test_milvus_store_reuses_existing_connection(monkeypatch: MonkeyPatch) -> None:
    store = MilvusVectorStore(config=MilvusConfig(), alias="reuse-test")
    mock_connections = MagicMock()
    mock_connections.list_connections.return_value = ["reuse-test"]
    monkeypatch.setattr(
        "eduagent.storage.milvus_store._MILVUS_CONNECTIONS", mock_connections
    )
    mock_collection = MagicMock()

    def always_true(*_args: object, **_kwargs: object) -> bool:
        return True

    def return_mock_collection(*_args: object, **_kwargs: object) -> MagicMock:
        return mock_collection

    monkeypatch.setattr(
        "eduagent.storage.milvus_store._MILVUS_UTILITY.has_collection", always_true
    )
    monkeypatch.setattr(
        "eduagent.storage.milvus_store.Collection", return_mock_collection
    )

    store.ensure_collection()
    mock_connections.connect.assert_not_called()
