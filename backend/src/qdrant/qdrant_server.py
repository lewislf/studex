import os

from qdrant_client import QdrantClient
from qdrant_client.models import FieldCondition, Filter, MatchValue
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


def _match_any(key: str, value) -> FieldCondition | Filter:
    """Casa o valor no payload tanto no tipo original quanto como string.

    Payloads gravados pelo pipeline de indexação (via LlamaIndex) têm tipos
    inconsistentes entre pontos (ex: user_id às vezes int, às vezes string),
    então casamos os dois pra não deixar vetor órfão para trás.
    """
    candidates = {value, str(value)}
    if len(candidates) == 1:
        return FieldCondition(key=key, match=MatchValue(value=value))
    return Filter(should=[FieldCondition(key=key, match=MatchValue(value=v)) for v in candidates])


def delete_vectors_by_metadata(
    user_id=None, subject_id=None, collection_name: str = COLLECTION_NAME
) -> None:
    """Remove do Qdrant os vetores indexados com o user_id e/ou subject_id dados.

    Usado para limpar vetores órfãos quando uma matéria ou usuário é deletado.
    Chamada esperada dentro de try/except: uma falha aqui nunca pode impedir
    o delete no banco relacional.
    """
    conditions = []
    if user_id is not None:
        conditions.append(_match_any("user_id", user_id))
    if subject_id is not None:
        conditions.append(_match_any("subject_id", subject_id))

    if not conditions:
        return

    if not client.collection_exists(collection_name):
        return

    client.delete(collection_name=collection_name, points_selector=Filter(must=conditions))
