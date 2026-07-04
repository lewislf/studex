import os
import sys
from pathlib import Path

import nest_asyncio

nest_asyncio.apply()

sys.path.append(str(Path(__file__).resolve().parent.parent / "qdrant"))
from qdrant_server import get_vector_store, collection_exists, COLLECTION_NAME

import fitz  # PyMuPDF

from llama_index.core import (
    Document,
    VectorStoreIndex,
    SimpleDirectoryReader,
    StorageContext,
    Settings,
)
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.schema import BaseNode
from llama_index.core.vector_stores import ExactMatchFilter, MetadataFilters
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.llms.ollama import Ollama

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_EMBED_HOST = os.environ.get("OLLAMA_EMBED_HOST", OLLAMA_HOST) # Permite apontar embedding e LLM pra hosts diferentes, se precisar.
OLLAMA_LLM_HOST = os.environ.get("OLLAMA_LLM_HOST", OLLAMA_HOST)
LLM_MODEL = os.environ.get("LLM_MODEL", "llama3.2:latest")
LLM_CONTEXT_WINDOW = int(os.environ.get("LLM_CONTEXT_WINDOW", "4096"))

embed_model = OllamaEmbedding(
    model_name="bge-m3",
    base_url=OLLAMA_EMBED_HOST,
    request_timeout=300.0,
)

llm = Ollama(
    model=LLM_MODEL,  # ver modelos disponíveis com `ollama list`
    base_url=OLLAMA_LLM_HOST,
    request_timeout=300.0,
    temperature=0.1,
    context_window=LLM_CONTEXT_WINDOW,
)

Settings.embed_model = embed_model
Settings.llm = llm


def _load_pdf(file_path: Path, metadata: dict | None = None) -> list[Document]:
    """Extrai o texto com PyMuPDF — o leitor padrão (baseado em pypdf) gera
    texto corrompido em PDFs com certas codificações de fonte."""
    with fitz.open(file_path) as pdf:
        text = "\n".join(page.get_text() for page in pdf)

    if not text.strip():
        raise ValueError(f"Nenhum texto extraído de: {file_path}")

    return [Document(text=text, metadata={"file_name": file_path.name, **(metadata or {})})]


def load_documents(input_files, metadata: dict | None = None) -> list[Document]:
    """Carrega um ou mais documentos do disco como Document do LlamaIndex.

    `metadata` (ex: user_id, subject_id) é anexado a cada Document para permitir
    filtrar a busca depois e evitar que um usuário veja conteúdo de outro.
    """
    if isinstance(input_files, (list, tuple)):
        input_files = [Path(f) for f in input_files]
    else:
        input_files = [Path(input_files)]

    for file_path in input_files:
        if not file_path.exists():
            raise FileNotFoundError(f"Documento não encontrado: {file_path}")

    docs = []
    other_files = []
    for file_path in input_files:
        if file_path.suffix.lower() == ".pdf":
            docs.extend(_load_pdf(file_path, metadata=metadata))
        else:
            other_files.append(str(file_path))

    if other_files:
        loaded = SimpleDirectoryReader(input_files=other_files).load_data()
        for doc in loaded:
            doc.metadata.update(metadata or {})
        docs.extend(loaded)

    if not docs:
        raise ValueError(f"Nenhum conteúdo encontrado em: {input_files}")

    return docs


def split_into_nodes(docs: list[Document]) -> list[BaseNode]:
    """Divide os documentos em chunks uma única vez, para reaproveitar entre
    indexação, resumo em cascata e extração do mapa mental — em vez de cada
    etapa re-dividir o mesmo texto do zero."""
    splitter = SentenceSplitter(chunk_size=1024, chunk_overlap=20)
    return splitter.get_nodes_from_documents(docs)


def build_vector_index(nodes: list[BaseNode], collection_name: str = COLLECTION_NAME) -> VectorStoreIndex:
    """Gera os embeddings dos nodes já divididos e armazena no Qdrant."""
    vector_store = get_vector_store(collection_name)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    return VectorStoreIndex(
        nodes,
        storage_context=storage_context,
        embed_model=embed_model,
    )


def index_documents(
    input_files, collection_name: str = COLLECTION_NAME, metadata: dict | None = None
) -> VectorStoreIndex:
    """Carrega um ou mais documentos e armazena seus embeddings no Qdrant."""
    docs = load_documents(input_files, metadata=metadata)
    nodes = split_into_nodes(docs)
    return build_vector_index(nodes, collection_name=collection_name)


def load_existing_index(collection_name: str = COLLECTION_NAME) -> VectorStoreIndex:
    """Reconecta a embeddings já armazenados no Qdrant, sem reindexar."""
    if not collection_exists(collection_name):
        raise RuntimeError(
            f"Coleção '{collection_name}' não existe no Qdrant. Rode index_documents primeiro."
        )

    vector_store = get_vector_store(collection_name)
    return VectorStoreIndex.from_vector_store(vector_store, embed_model=embed_model)


def build_metadata_filters(**kwargs) -> MetadataFilters | None:
    """Monta um filtro de metadados (ex: user_id=1, subject_id=2) para restringir
    a busca aos documentos daquele dono, evitando vazar conteúdo entre usuários."""
    filters = [ExactMatchFilter(key=key, value=value) for key, value in kwargs.items() if value is not None]
    return MetadataFilters(filters=filters) if filters else None


def create_query_engine(index: VectorStoreIndex, similarity_top_k: int = 3, filters: MetadataFilters | None = None):
    """Cria o query engine com os parâmetros de recuperação especificados.

    Passe `filters` (ver `build_metadata_filters`) para restringir a busca a um
    usuário/matéria específico dentro da coleção compartilhada.
    """
    return index.as_query_engine(
        llm=llm,
        similarity_top_k=similarity_top_k,
        response_mode="compact",
        filters=filters,
    )


if __name__ == "__main__":
    try:
        index = index_documents(list(Path("data").glob("*")))
        engine = create_query_engine(index)
        print(engine.query("Resuma este documento em 3 linhas"))
    except Exception as exc:
        print(f"Teste falhou: {exc}")
