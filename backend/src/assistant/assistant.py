import argparse
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent / "rag_api"))
sys.path.append(str(Path(__file__).resolve().parent.parent / "qdrant"))

from search_query import index_documents, load_existing_index, create_query_engine, build_metadata_filters
from qdrant_server import collection_exists, COLLECTION_NAME

DOCS_DIR = Path(__file__).resolve().parent.parent / "docs"


def _parse_args():
    parser = argparse.ArgumentParser(description="Chat de teste sobre um documento indexado no Qdrant.")
    parser.add_argument("file", nargs="?", help="Caminho do PDF a indexar (se ainda não indexado).")
    parser.add_argument("--user-id", help="Filtra a busca pelos documentos deste usuário.")
    parser.add_argument("--subject-id", help="Filtra a busca pelos documentos desta matéria.")
    return parser.parse_args()


def _resolve_doc_path(file_arg: str | None) -> Path:
    """Usa o PDF passado por argumento, senão, pega o primeiro .pdf encontrado em docs/."""
    if file_arg:
        return Path(file_arg).resolve()

    pdfs = sorted(DOCS_DIR.glob("*.pdf"))
    if not pdfs:
        raise FileNotFoundError(
            f"Nenhum PDF encontrado em {DOCS_DIR}. Passe o caminho como argumento: "
            "python assistant.py caminho/do/arquivo.pdf"
        )
    return pdfs[0]


def get_index(file_arg: str | None, user_id: str | None, subject_id: str | None):
    """Reaproveita a coleção do Qdrant se o livro já estiver indexado; senão, indexa."""
    if collection_exists(COLLECTION_NAME):
        print(f"Usando coleção existente '{COLLECTION_NAME}' no Qdrant.")
        return load_existing_index(COLLECTION_NAME)

    doc_path = _resolve_doc_path(file_arg)
    metadata = {k: v for k, v in {"user_id": user_id, "subject_id": subject_id}.items() if v is not None}
    print(f"Indexando documento '{doc_path.name}' no Qdrant...")
    return index_documents([doc_path], collection_name=COLLECTION_NAME, metadata=metadata)


def run_chat():
    """Loop de chat no terminal: o usuário pergunta e o assistente responde com base no
    documento indexado, restrito ao user_id/subject_id informados (se houver)."""
    args = _parse_args()
    index = get_index(args.file, args.user_id, args.subject_id)
    filters = build_metadata_filters(user_id=args.user_id, subject_id=args.subject_id)
    query_engine = create_query_engine(index, filters=filters)

    print("\nAssistente pronto. Pergunte algo sobre o documento (digite 'sair' para encerrar).\n")

    while True:
        question = input("Você: ").strip()
        if question.lower() in {"sair", "exit", "quit"}:
            print("Encerrando o assistente.")
            break
        if not question:
            continue

        response = query_engine.query(question)
        print(f"\nAssistente: {response}\n")


if __name__ == "__main__":
    run_chat()
