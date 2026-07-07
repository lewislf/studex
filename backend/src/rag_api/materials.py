import json
import logging
import os
import re
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import date

from llama_index.core import SummaryIndex
from llama_index.core.schema import BaseNode

from search_query import llm

logger = logging.getLogger(__name__)

# Resumo em cascata sobre TODOS os chunks é o maior custo de tempo em documentos
# grandes (~80% do total). Como o resumo final já comprime tudo em poucos
# parágrafos, amostrar uma fração representativa dos chunks dá um resultado
# equivalente em muito menos tempo. Default baixo pra manter o upload rápido,
# se precisar de mais cobertura pode aumentar. 0 = sem limite (resume tudo).
MAX_CHUNKS_FOR_SUMMARY = int(os.environ.get("MAX_CHUNKS_FOR_SUMMARY", "60"))
MAX_CHUNKS_FOR_MIND_MAP = 15
MAX_CATEGORIAS = 6
MAX_DETALHES_POR_CATEGORIA = 5
ENTITY_EXTRACTION_WORKERS = 5


def _sample_evenly(items: list, max_count: int) -> list:
    """Amostra até max_count itens distribuídos uniformemente ao longo da
    lista, preservando a ordem — pra cobrir o documento inteiro sem processar
    todos os chunks."""
    if max_count <= 0 or len(items) <= max_count:
        return items
    step = len(items) / max_count
    return [items[int(i * step)] for i in range(max_count)]


def _complete_json(prompt: str, attempts: int = 3):
    """Chama o LLM e extrai o JSON da resposta, tentando de novo se vier
    malformado (comum com um modelo local pequeno)."""
    last_error = None
    for _ in range(attempts):
        try:
            return _extract_json(llm.complete(prompt).text)
        except ValueError as exc:
            last_error = exc
    raise last_error


def _extract_json(text: str):
    """Extrai um JSON da resposta do LLM, mesmo com texto, markdown ou
    comentários ao redor."""
    text = re.sub(r"```(?:json)?", "", text).strip()

    start_candidates = [i for i in (text.find("{"), text.find("[")) if i != -1]
    if not start_candidates:
        raise ValueError("Nenhum JSON encontrado na resposta do LLM")

    start = min(start_candidates)
    candidate = text[start:]

    for end in range(len(candidate), 0, -1):
        try:
            return json.loads(candidate[:end])
        except json.JSONDecodeError:
            continue

    raise ValueError("Falha ao decodificar JSON da resposta do LLM")


def generate_summary_text(nodes: list[BaseNode]) -> str:
    """Resumo em cascata (map-reduce): resume os pedaços do documento e
    depois resume os resumos, pra caber documentos maiores que o contexto
    do LLM. Amostra os chunks pra manter o tempo previsível em documentos
    grandes (o resumo final comprime tudo de qualquer forma)."""
    sampled = _sample_evenly(nodes, MAX_CHUNKS_FOR_SUMMARY)
    if len(sampled) < len(nodes):
        logger.info("Resumo: amostrando %d de %d chunks", len(sampled), len(nodes))

    summary_index = SummaryIndex(sampled)
    # use_async dispara as chamadas irmãs de cada nível da árvore em paralelo;
    # o ganho real depende de OLLAMA_NUM_PARALLEL > 1 no servidor Ollama.
    engine = summary_index.as_query_engine(response_mode="tree_summarize", llm=llm, use_async=True)

    response = engine.query(
        "Resuma o conteúdo deste documento em português, cobrindo os pontos "
        "principais de forma clara e objetiva."
    )
    return str(response)


def generate_resumo(summary_text: str, fallback_titulo: str) -> dict:
    prompt = f"""Com base no resumo abaixo, gere um JSON válido, e SOMENTE o JSON, no formato:
{{"titulo": "título curto do documento", "topicos_chave": ["ponto 1", "ponto 2", "ponto 3", "ponto 4"]}}

Resumo:
\"\"\"{summary_text}\"\"\"
"""
    try:
        data = _complete_json(prompt)
    except ValueError:
        data = {}

    return {
        "titulo": data.get("titulo") or fallback_titulo,
        "conteudo": summary_text,
        "topicos_chave": data.get("topicos_chave", []),
    }


def _sample_chunks(nodes: list[BaseNode], max_chunks: int = MAX_CHUNKS_FOR_MIND_MAP) -> list[str]:
    """Amostra até max_chunks dos nodes já divididos, distribuídos ao longo
    do texto, pra manter o tempo de extração previsível em documentos
    grandes."""
    sampled = _sample_evenly(nodes, max_chunks)
    if len(sampled) < len(nodes):
        logger.info("Mapa mental: amostrando %d de %d chunks", len(sampled), len(nodes))
    return [node.get_content() for node in sampled]


def _extract_entities_from_chunk(chunk_text: str) -> list[dict]:
    """Extrai entidades/conceitos citados literalmente neste trecho — a
    descrição vem só do texto abaixo, sem o LLM completar com conhecimento
    externo."""
    prompt = f"""Leia o trecho abaixo e liste as entidades/conceitos importantes citados nele
(pessoas, lugares, conceitos, fórmulas, eventos — o que fizer sentido pro assunto).

Responda APENAS com um JSON no formato de lista:
[{{"nome": "...", "tipo": "...", "descricao": "..."}}]

- "tipo" é uma categoria curta (ex: "Personagem", "Conceito", "Fórmula", "Evento", "Lugar").
- "descricao" tem 1 frase, baseada SOMENTE no texto abaixo — não invente informação que não
  está aqui.
- Liste no máximo 5 entidades, só as mais relevantes deste trecho.
- Se não houver nada relevante, responda com uma lista vazia: []

Trecho:
\"\"\"{chunk_text}\"\"\"
"""
    try:
        data = _complete_json(prompt)
    except ValueError:
        return []

    if not isinstance(data, list):
        return []

    entities = []
    for item in data:
        if isinstance(item, dict) and item.get("nome") and item.get("tipo"):
            entities.append({
                "nome": str(item["nome"]).strip(),
                "tipo": str(item["tipo"]).strip(),
                "descricao": str(item.get("descricao", "")).strip(),
            })
    return entities


def _merge_entities(raw_entities: list[dict]) -> list[dict]:
    """Funde entidades com o mesmo nome extraídas de chunks diferentes.
    O número de menções vira um proxy de importância, usado depois pra
    decidir quais entidades entram no mapa mental."""
    merged: dict[str, dict] = {}
    for ent in raw_entities:
        key = ent["nome"].lower()
        if key not in merged:
            merged[key] = {"nome": ent["nome"], "descricao": ent["descricao"], "tipos": [], "mencoes": 0}
        merged[key]["tipos"].append(ent["tipo"])
        merged[key]["mencoes"] += 1

    result = []
    for ent in merged.values():
        tipo = Counter(ent["tipos"]).most_common(1)[0][0]
        result.append({"nome": ent["nome"], "tipo": tipo, "descricao": ent["descricao"], "mencoes": ent["mencoes"]})

    return result


def build_mind_map_from_entities(entities: list[dict], titulo: str) -> dict:
    """Monta nodes/edges do mapa mental a partir de entidades já extraídas
    do texto — a estrutura reflete o que foi encontrado nos chunks, o LLM
    não é chamado pra "desenhar" a árvore."""
    if not entities:
        raise ValueError("Nenhuma entidade extraída dos chunks do documento")

    by_tipo: dict[str, list[dict]] = {}
    for ent in entities:
        by_tipo.setdefault(ent["tipo"], []).append(ent)

    categorias = sorted(by_tipo.items(), key=lambda kv: sum(e["mencoes"] for e in kv[1]), reverse=True)
    if len(categorias) > MAX_CATEGORIAS:
        logger.info("Descartando %d categorias além do limite de %d", len(categorias) - MAX_CATEGORIAS, MAX_CATEGORIAS)
        categorias = categorias[:MAX_CATEGORIAS]

    nodes = [{
        "id": "1",
        "type": "tema_central",
        "data": {"label": titulo, "conteudo": f"Visão geral de {titulo}, organizada a partir do conteúdo indexado."},
    }]
    edges = []

    for cat_idx, (tipo, ents) in enumerate(categorias, start=1):
        cat_id = f"cat-{cat_idx}"
        detalhes = sorted(ents, key=lambda e: e["mencoes"], reverse=True)
        if len(detalhes) > MAX_DETALHES_POR_CATEGORIA:
            detalhes = detalhes[:MAX_DETALHES_POR_CATEGORIA]

        nodes.append({
            "id": cat_id,
            "type": "categoria",
            "data": {"label": tipo, "conteudo": f"{len(detalhes)} itens relacionados a {tipo.lower()}"},
        })
        edges.append({"id": f"e1-{cat_id}", "source": "1", "target": cat_id})

        for det_idx, ent in enumerate(detalhes, start=1):
            det_id = f"{cat_id}-det-{det_idx}"
            nodes.append({
                "id": det_id,
                "type": "detalhe",
                "data": {"label": ent["nome"], "conteudo": ent["descricao"]},
            })
            edges.append({"id": f"e{cat_id}-{det_id}", "source": cat_id, "target": det_id})

    return {"nodes": nodes, "edges": edges}


def generate_mind_map(nodes: list[BaseNode], titulo: str) -> dict:
    """Gera o mapa mental extraindo entidades reais dos chunks do documento,
    em vez de pedir pro LLM inventar a estrutura a partir do resumo."""
    chunks = _sample_chunks(nodes)

    with ThreadPoolExecutor(max_workers=ENTITY_EXTRACTION_WORKERS) as executor:
        results = executor.map(_extract_entities_from_chunk, chunks)

    raw_entities = [ent for chunk_entities in results for ent in chunk_entities]

    entities = _merge_entities(raw_entities)
    return build_mind_map_from_entities(entities, titulo)


_FLASHCARD_PATTERN = re.compile(r"Frente:\s*(.+?)\s*Verso:\s*(.+?)(?=\s*Frente:|\Z)", re.DOTALL | re.IGNORECASE)


def _parse_flashcards(text: str) -> list[dict]:
    """Extrai pares Frente/Verso de um texto simples — um modelo local pequeno
    erra bem menos nesse formato do que tentando produzir JSON válido."""
    flashcards = []
    for frente, verso in _FLASHCARD_PATTERN.findall(text):
        frente, verso = frente.strip(), verso.strip()
        if frente and verso:
            flashcards.append({"pergunta": frente, "resposta": verso})
    return flashcards


def generate_flashcards(summary_text: str, attempts: int = 3) -> list[dict]:
    prompt = f"""Com base no resumo abaixo, gere entre 10 e 25 flashcards de estudo em português.

Responda cada flashcard EXATAMENTE neste formato de texto simples, um por bloco, sem
numeração, markdown ou JSON:

Frente: <pergunta>
Verso: <resposta>

Resumo:
\"\"\"{summary_text}\"\"\"
"""
    last_error = None
    for _ in range(attempts):
        flashcards = _parse_flashcards(llm.complete(prompt).text)
        if len(flashcards) >= 10:
            return flashcards[:25]
        last_error = ValueError(f"LLM gerou só {len(flashcards)} flashcards válidos (mínimo 10)")

    raise last_error


def generate_materials(nodes: list[BaseNode], fallback_titulo: str = "Documento", subject_id=None) -> list[dict]:
    """Roda o pipeline completo do documento e retorna [resumo, mapa_mental,
    baralho], cada um no mesmo formato: {tipo, titulo, subject_id,
    creation_date, conteudo}."""
    summary_text = generate_summary_text(nodes)
    resumo = generate_resumo(summary_text, fallback_titulo)
    mapa_mental = generate_mind_map(nodes, resumo["titulo"])
    flashcards = generate_flashcards(summary_text)

    creation_date = date.today().isoformat()
    titulo_base = resumo["titulo"]
    
    materials = [
            {
                "tipo": "resumo",
                "titulo": titulo_base,
                "subject_id": subject_id,
                "creation_date": creation_date,
                "conteudo": {
                    "texto": resumo["conteudo"],
                    "topicos_chave": resumo["topicos_chave"],
                },
            },
            {
                "tipo": "mapa_mental",
                "titulo": f"{titulo_base} — Mapa Mental de Estudo",
                "subject_id": subject_id,
                "creation_date": creation_date,
                "conteudo": {
                    "nodes": mapa_mental["nodes"],
                    "edges": mapa_mental["edges"],
                },
            },
            {
                "tipo": "baralho",
                "titulo": f"{titulo_base} — Flashcards",
                "subject_id": subject_id,
                "creation_date": creation_date,
                "conteudo": {
                    "flashcards": flashcards,
                },
            },
        ]
    
    return materials
