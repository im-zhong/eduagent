"""
Vector Store Factory for EduAgent

Provides factory methods for creating different vector store implementations
based on configuration.
"""

from .base import VectorStore, VectorStoreConfig, VectorStoreFactory


class DefaultVectorStoreFactory(VectorStoreFactory):
    """
    Default implementation of VectorStoreFactory that creates vector stores
    based on the backend specified in the configuration.
    """

    def __init__(self) -> None:
        """Initialize the factory with registered implementations."""
        self._backends: dict[str, type[VectorStore]] = {}

    def register_backend(
        self, backend_name: str, backend_class: type[VectorStore]
    ) -> None:
        """
        Register a vector store backend implementation.

        Args:
            backend_name: Name of the backend (e.g., "pgvector", "qdrant")
            backend_class: Class that implements VectorStore interface
        """
        self._backends[backend_name.lower()] = backend_class

    def create_vector_store(self, config: VectorStoreConfig) -> VectorStore:
        """
        Create a vector store instance with the given configuration.

        Args:
            config: Configuration for the vector store

        Returns:
            Configured vector store instance

        Raises:
            ValueError: If the specified backend is not supported
        """
        backend_name = config.backend.lower()

        if backend_name not in self._backends:
            available_backends = ", ".join(self._backends.keys())
            msg = (
                f"Unsupported vector store backend: {backend_name}. "
                f"Available backends: {available_backends}"
            )
            raise ValueError(msg)

        backend_class = self._backends[backend_name]
        return backend_class(config)

    def get_supported_backends(self) -> list[str]:
        """
        Get list of supported backend names.

        Returns:
            List of supported backend names
        """
        return list(self._backends.keys())

    def is_backend_supported(self, backend_name: str) -> bool:
        """
        Check if a backend is supported.

        Args:
            backend_name: Name of the backend to check

        Returns:
            True if supported, False otherwise
        """
        return backend_name.lower() in self._backends


# Global factory instance
_default_factory = DefaultVectorStoreFactory()


def get_vector_store_factory() -> DefaultVectorStoreFactory:
    """
    Get the default vector store factory instance.

    Returns:
        Default vector store factory
    """
    return _default_factory


def create_vector_store(config: VectorStoreConfig) -> VectorStore:
    """
    Convenience function to create a vector store using the default factory.

    Args:
        config: Configuration for the vector store

    Returns:
        Configured vector store instance
    """
    return get_vector_store_factory().create_vector_store(config)


def register_backend(backend_name: str, backend_class: type[VectorStore]) -> None:
    """
    Convenience function to register a backend with the default factory.

    Args:
        backend_name: Name of the backend
        backend_class: Class that implements VectorStore interface
    """
    get_vector_store_factory().register_backend(backend_name, backend_class)


# Import and register available backends here when they are implemented
# Example:
# from .pgvector import PGVectorStore
# register_backend("pgvector", PGVectorStore)
#
# from .qdrant import QdrantVectorStore
# register_backend("qdrant", QdrantVectorStore)
