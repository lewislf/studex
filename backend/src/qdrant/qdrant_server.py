import os

from qdrant_client import QdrantClient
from llama_index.vector_stores.qdrant import QdrantVectorStore

QDRANT_URL = os.environ.get("QDRANT_URL", "http://localhost:6333")
COLLECTION_NAME = "studex_books"

client = QdrantClient(url=QDRANT_URL)


def collection_exists(collection_name: str = COLLECTION_NAME) -> bool:
    """Verifica se a coleção já tem embeddings armazenados no Qdrant."""
    return client.collection_exists(collection_name)


def get_vector_store(collection_name: str = COLLECTION_NAME) -> QdrantVectorStore:
    """Retorna o vector store do LlamaIndex ligado a essa coleção do Qdrant."""
    return QdrantVectorStore(client=client, collection_name=collection_name)
