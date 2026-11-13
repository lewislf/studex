import os
import sys

from qdrant_client import QdrantClient
from qdrant_client.models import FieldCondition, Filter, MatchValue, PayloadSchemaType
from llama_index.vector_stores.qdrant import QdrantVectorStore

# Garante uma única instância mesmo quando importado como `qdrant.qdrant_server` e `qdrant_server`
sys.modules.setdefault("qdrant_server", sys.modules[__name__])
sys.modules.setdefault("qdrant.qdrant_server", sys.modules[__name__])

QDRANT_URL = os.environ.get("QDRANT_URL")
QDRANT_API_KEY = os.environ.get("QDRANT_API_KEY")
QDRANT_PATH = os.environ.get("QDRANT_PATH")
COLLECTION_NAME = "studex_books"

if QDRANT_URL:
    client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
elif QDRANT_PATH:
    client = QdrantClient(path=QDRANT_PATH)
else:
    client = QdrantClient(url="http://localhost:6333")


def collection_exists(collection_name: str = COLLECTION_NAME) -> bool:
    """Verifica se a coleção já tem embeddings armazenados no Qdrant."""
    return client.collection_exists(collection_name)


def get_vector_store(collection_name: str = COLLECTION_NAME) -> QdrantVectorStore:
    """Retorna o vector store do LlamaIndex ligado a essa coleção do Qdrant."""
    return QdrantVectorStore(client=client, collection_name=collection_name)


# Campos usados nos filtros. O Qdrant Cloud recusa filtro em campo sem índice
# ("Index required but not found"), então os índices são criados antes de filtrar.
_CAMPOS_FILTRO = ("user_id", "subject_id")
_indexadas: set[str] = set()


def ensure_payload_indexes(collection_name: str = COLLECTION_NAME) -> None:
    """Cria (uma vez por processo) os índices inteiros de user_id e subject_id.

    Recriar um índice que já existe não dá erro no Qdrant, então é seguro após um deploy.
    """
    if collection_name in _indexadas:
        return
    for campo in _CAMPOS_FILTRO:
        client.create_payload_index(
            collection_name=collection_name,
            field_name=campo,
            field_schema=PayloadSchemaType.INTEGER,
            wait=True,
        )
    _indexadas.add(collection_name)


def delete_vectors_by_metadata(
    user_id=None, subject_id=None, collection_name: str = COLLECTION_NAME
) -> None:
    """Remove do Qdrant os vetores indexados com o user_id e/ou subject_id dados.

    Usado para limpar vetores órfãos quando uma matéria ou usuário é deletado.
    Chamada esperada dentro de try/except: uma falha aqui nunca pode impedir
    o delete no banco relacional.
    """
    # só int: com índice inteiro (exigido no Cloud), um filtro por texto seria recusado.
    # shortcut: vetores antigos gravados com id em texto (só no Qdrant local) ficam para trás; apague o volume local se precisar
    conditions = [
        FieldCondition(key=campo, match=MatchValue(value=int(valor)))
        for campo, valor in (("user_id", user_id), ("subject_id", subject_id))
        if valor is not None
    ]

    if not conditions:
        return

    if not client.collection_exists(collection_name):
        return

    ensure_payload_indexes(collection_name)
    client.delete(collection_name=collection_name, points_selector=Filter(must=conditions))
