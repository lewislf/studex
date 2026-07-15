"""
Deduplicação de materiais (flashcards, resumo, mapa mental) gerados por
upload de PDF.

Flashcards: funil em 2 estágios, aplicado ao lote de cards NOVOS de um
baralho antes de salvar no banco:

1) Lexical: dentro do próprio lote novo, normaliza a pergunta (minúsculas,
   sem acentos, sem pontuação, espaços colapsados) e compara pares com
   difflib.SequenceMatcher. Ratio >= DEDUP_LEXICAL_THRESHOLD descarta o
   segundo card do par.

2) Semântico: embedding de "pergunta\nresposta" comparado, por similaridade
   de cosseno, contra os cards já existentes na MATÉRIA (e contra os cards
   já aceitos deste mesmo lote, que entram no mesmo pool de comparação).
   Similaridade >= DEDUP_SEMANTIC_THRESHOLD descarta o novo card.

Resumo/mapa mental: só o estágio lexical (filtrar_materiais_duplicados), sem
embedding (reenvio do mesmo PDF gera um texto praticamente idêntico, não
precisa de similaridade semântica). Resumo compara título + início do texto;
mapa mental (conteúdo é um grafo, não texto corrido) é normalizado primeiro
extraindo os labels dos nós, ordenados, antes do comparador lexical.

Módulo é lógica pura: não importa search_query nem llama_index. embed_model
e a função de persistência de embedding são injetados pelo caller
(routes/document_routes.py), o que permite testar com mock.

embed_fn é sempre em BATCH: callable(textos: list[str]) -> list[list[float]],
uma única chamada HTTP pro Ollama por lote em vez de uma por card (era o
gargalo em matérias com muitos flashcards existentes).
"""

import difflib
import json
import os
import re
import unicodedata

import numpy as np

DEDUP_LEXICAL_THRESHOLD = float(os.environ.get("DEDUP_LEXICAL_THRESHOLD", "0.85"))
DEDUP_SEMANTIC_THRESHOLD = float(os.environ.get("DEDUP_SEMANTIC_THRESHOLD", "0.88"))
DEDUP_MIN_CARDS_NOVOS = int(os.environ.get("DEDUP_MIN_CARDS_NOVOS", "5"))

# Dedup lexical de resumo/mapa mental (reenvio do mesmo PDF não pode duplicar
# esses materiais). Threshold conservador: só descarta quase-idêntico de
# verdade, não "sobre o mesmo assunto".
DEDUP_MATERIAL_THRESHOLD = float(os.environ.get("DEDUP_MATERIAL_THRESHOLD", "0.9"))
# quantos caracteres do corpo do resumo entram na comparação (título + início
# do texto já é suficiente pra pegar reenvio do mesmo PDF, sem comparar
# documentos inteiros)
DEDUP_MATERIAL_CONTEUDO_CHARS = int(os.environ.get("DEDUP_MATERIAL_CONTEUDO_CHARS", "500"))


def normalizar_pergunta(pergunta: str) -> str:
    """Minúsculas, sem acentos (via unicodedata), sem pontuação, espaços
    colapsados. Base da comparação lexical."""
    texto = unicodedata.normalize("NFKD", pergunta.lower())
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = re.sub(r"[^\w\s]", " ", texto)
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto


def _lexical_ratio(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, a, b).ratio()


def filtrar_lote_lexical(cards: list[dict], threshold: float | None = None) -> list[dict]:
    """Remove duplicatas dentro do MESMO lote de cards novos, comparando a
    pergunta normalizada. Mantém o primeiro card de cada par parecido."""
    threshold = DEDUP_LEXICAL_THRESHOLD if threshold is None else threshold

    aceitos = []
    normalizadas = []
    for card in cards:
        norm = normalizar_pergunta(card["pergunta"])
        duplicado = any(_lexical_ratio(norm, existente) >= threshold for existente in normalizadas)
        if duplicado:
            continue
        aceitos.append(card)
        normalizadas.append(norm)

    return aceitos


def cosine_similarity(vec_a, vec_b) -> float:
    """Similaridade de cosseno entre dois vetores. Vetor nulo (norma 0)
    devolve 0.0 em vez de dividir por zero."""
    a = np.asarray(vec_a, dtype=float)
    b = np.asarray(vec_b, dtype=float)
    norma_a = np.linalg.norm(a)
    norma_b = np.linalg.norm(b)
    if norma_a == 0 or norma_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norma_a * norma_b))


def _texto_embedding(pergunta: str, resposta: str) -> str:
    return f"{pergunta}\n{resposta}"


def filtrar_lote_semantico(
    cards: list[dict],
    embeddings_existentes: list,
    embed_fn,
    threshold: float | None = None,
) -> list[dict]:
    """
    Descarta cards cujo embedding tem similaridade de cosseno >= threshold
    com QUALQUER embedding do pool (cards já existentes na matéria + cards já
    aceitos neste mesmo lote). Cards aceitos saem com a chave "embedding"
    preenchida (o vetor já calculado, pronto pra persistir sem recalcular).

    embed_fn: callable(textos: list[str]) -> list[list[float]], em BATCH.
    Todos os textos do lote são embeddados numa única chamada, no início; a
    ORDEM de aceitação continua sequencial (o pool cresce card a card) pra
    manter a comparação incremental correta, só a chamada ao embed_fn é que
    vira uma única chamada em vez de um loop.
    """
    threshold = DEDUP_SEMANTIC_THRESHOLD if threshold is None else threshold

    textos = [_texto_embedding(card["pergunta"], card["resposta"]) for card in cards]
    embeddings = embed_fn(textos) if textos else []

    # pool de comparação: ignora embeddings None (cards antigos sem embedding
    # calculado, ex. cadastrados antes do dedup semântico existir), senão
    # cosine_similarity quebra ao tentar np.asarray(None)
    pool = [e for e in embeddings_existentes if e is not None]
    aceitos = []
    for card, embedding in zip(cards, embeddings):
        if embedding is None:
            # sem embedding pra este card novo: não dá pra comparar, aceita
            # sem checar duplicata em vez de levantar exceção
            card_aceito = dict(card)
            card_aceito["embedding"] = None
            aceitos.append(card_aceito)
            continue
        duplicado = any(cosine_similarity(embedding, existente) >= threshold for existente in pool)
        if duplicado:
            continue
        card_aceito = dict(card)
        card_aceito["embedding"] = embedding
        aceitos.append(card_aceito)
        pool.append(embedding)

    return aceitos


def _get_attr(obj, name):
    """Aceita tanto dict quanto objeto (ex: Flashcard) pra ler um campo."""
    if isinstance(obj, dict):
        return obj.get(name)
    return getattr(obj, name, None)


def _conteudo_como_dict(conteudo) -> dict:
    """conteudo de um material vem como dict (material novo, ainda não
    persistido) ou como string JSON (material existente lido do banco:
    save_materials_db grava com json.dumps). Normaliza pros dois formatos."""
    if isinstance(conteudo, str):
        try:
            return json.loads(conteudo)
        except (TypeError, ValueError):
            return {}
    return conteudo or {}


def _texto_dedup_mapa_mental(conteudo: dict) -> str:
    """Mapa mental é um grafo (nodes/edges), não um texto corrido: comparar o
    JSON bruto seria ruidoso (ordem, ids). Normaliza ESTRUTURALMENTE primeiro:
    extrai só os labels dos nós, ordenados (independe de ordem/id), e junta
    num texto canônico, que aí sim passa pelo mesmo comparador lexical de
    texto usado no resto do módulo."""
    nodes = conteudo.get("nodes", []) or []
    labels = sorted(
        str(node.get("data", {}).get("label", ""))
        for node in nodes
        if isinstance(node, dict)
    )
    return " | ".join(labels)


def _texto_dedup_material(titulo: str, conteudo, tipo: str) -> str:
    """Texto canônico de comparação de um material: título + início do corpo
    (resumo) ou labels dos nós (mapa mental), normalizado (minúsculas, sem
    acento/pontuação, espaços colapsados, via normalizar_pergunta)."""
    conteudo_dict = _conteudo_como_dict(conteudo)
    if tipo == "mapa_mental":
        corpo = _texto_dedup_mapa_mental(conteudo_dict)
    else:
        corpo = str(conteudo_dict.get("texto", "") or "")[:DEDUP_MATERIAL_CONTEUDO_CHARS]

    return normalizar_pergunta(f"{titulo or ''} {corpo}")


def filtrar_materiais_duplicados(
    materiais_novos: list[dict],
    materiais_existentes: list,
    tipo: str,
    threshold: float | None = None,
) -> list[dict]:
    """
    Dedup lexical de resumo/mapa mental: descarta materiais novos cujo texto
    canônico (ver _texto_dedup_material) é quase-idêntico (ratio >=
    threshold, difflib) a algum já existente na MATÉRIA, ou a um já aceito
    neste mesmo lote (mesmo funil de filtrar_lote_lexical).

    materiais_existentes: objetos Resumo/MapaMental (banco, .titulo/.conteudo)
    ou dicts, todos do MESMO `tipo` de materiais_novos (quem chama já separa
    por tipo, ex. get_summaries_db para "resumo").
    """
    threshold = DEDUP_MATERIAL_THRESHOLD if threshold is None else threshold

    pool = [
        _texto_dedup_material(_get_attr(existente, "titulo"), _get_attr(existente, "conteudo"), tipo)
        for existente in materiais_existentes
    ]

    aceitos = []
    for material in materiais_novos:
        texto_novo = _texto_dedup_material(material.get("titulo"), material.get("conteudo"), tipo)
        duplicado = any(_lexical_ratio(texto_novo, existente) >= threshold for existente in pool)
        if duplicado:
            continue
        aceitos.append(material)
        pool.append(texto_novo)

    return aceitos


def garantir_embeddings_existentes(flashcards: list, embed_fn, persist_fn) -> list:
    """
    Migração preguiçosa: para os flashcards EXISTENTES sem embedding (None),
    calcula os embeddings numa ÚNICA chamada em batch a embed_fn e persiste
    cada um via persist_fn(flashcard_id, embedding). Cards que já tinham
    embedding são reaproveitados sem recálculo. Retorna a lista de
    embeddings, na mesma ordem de `flashcards`.

    embed_fn: callable(textos: list[str]) -> list[list[float]].
    """
    pendentes_idx = []
    pendentes_textos = []
    embeddings: list = [None] * len(flashcards)

    for i, fc in enumerate(flashcards):
        embedding = _get_attr(fc, "embedding")
        if embedding is None:
            pergunta = _get_attr(fc, "pergunta")
            resposta = _get_attr(fc, "resposta")
            pendentes_idx.append(i)
            pendentes_textos.append(_texto_embedding(pergunta, resposta))
        else:
            embeddings[i] = embedding

    if pendentes_textos:
        novos_embeddings = embed_fn(pendentes_textos)
        for i, embedding in zip(pendentes_idx, novos_embeddings):
            embeddings[i] = embedding
            persist_fn(_get_attr(flashcards[i], "id"), embedding)

    return embeddings


def deve_criar_baralho(cards: list, minimo: int | None = None) -> bool:
    """Regra de corte: com menos de `minimo` cards novos sobrando após o
    dedup, o baralho não deve ser criado."""
    minimo = DEDUP_MIN_CARDS_NOVOS if minimo is None else minimo
    return len(cards) >= minimo


def deduplicar_flashcards(
    cards_novos: list[dict],
    flashcards_existentes: list,
    embed_fn,
    persist_embedding_fn,
    lexical_threshold: float | None = None,
    semantic_threshold: float | None = None,
) -> list[dict]:
    """
    Funil completo de deduplicação de um lote de flashcards novos:

    1. filtro lexical dentro do próprio lote
    2. backfill preguiçoso de embedding dos cards existentes da matéria
    3. filtro semântico contra os embeddings existentes (+ os já aceitos
       neste lote)

    Retorna os cards sobreviventes, cada um já com "embedding" setado.
    """
    apos_lexical = filtrar_lote_lexical(cards_novos, threshold=lexical_threshold)

    embeddings_existentes = garantir_embeddings_existentes(
        flashcards_existentes, embed_fn, persist_embedding_fn
    )

    return filtrar_lote_semantico(
        apos_lexical, embeddings_existentes, embed_fn, threshold=semantic_threshold
    )
