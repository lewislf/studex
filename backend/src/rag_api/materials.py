import json
import logging
import os
import re
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from llama_index.core.schema import BaseNode

from search_query import llm

logger = logging.getLogger(__name__)
# handler próprio pra instrumentação aparecer no docker logs mesmo sem
# configuração global de logging no Flask
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("%(asctime)s materials %(message)s"))
    logger.addHandler(_handler)
    logger.setLevel(logging.INFO)

# O Ollama local (qwen3:30b-a3b) tem prefill rápido e decode lento (~165 tok/s
# agregado). A estratégia é: cada chamada de LLM lê muito e gera pouco, cada
# lote é lido UMA ÚNICA VEZ (resumo + entidades + relações saem da mesma
# chamada), e todas as chamadas do pipeline disparam em uma única onda
# paralela.
# Quantos chunks cabem numa chamada de análise (28 x ~950 tokens ~ 27k, dentro
# do contexto de 32k). A análise sempre cobre o documento inteiro: acima disso
# vira map-reduce em lotes paralelos.
SUMMARY_CHUNKS_PER_CALL = int(os.environ.get("SUMMARY_CHUNKS_PER_CALL", "28"))
FLASHCARD_CALLS = int(os.environ.get("FLASHCARD_CALLS", "4"))
FLASHCARD_CHUNKS_PER_CALL = int(os.environ.get("FLASHCARD_CHUNKS_PER_CALL", "4"))
MAX_TEMAS = 6
MAX_DETALHES_POR_TEMA = 8
MAX_RELACOES_NO_MAPA = 25

# Subconjunto de materiais que generate_materials sabe gerar. Usado também
# por routes/document_routes.py pra validar o campo `materials` do upload.
MATERIAIS_VALIDOS = {"resumo", "mapa_mental", "flashcards"}


def _sample_evenly(items: list, max_count: int) -> list:
    """Amostra até max_count itens distribuídos uniformemente ao longo da
    lista, preservando a ordem, pra cobrir o documento inteiro sem processar
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


# ---------------------------------------------------------------------------
# Análise de conteúdo: resumo parcial + entidades + relações numa só leitura
# ---------------------------------------------------------------------------

_REGRAS_ENTIDADES_RELACOES = """- "entidades": no máximo 8, só as mais relevantes do trecho. "tipo" é uma
  categoria curta livre (ex: "Personagem", "Conceito", "Evento", "Lugar",
  "Fórmula"). "descricao" tem no máximo 15 palavras, baseada SOMENTE no texto,
  não invente informação que não está aqui.
- DESAMBIGUAÇÃO: variações e apelidos do mesmo nome são a MESMA entidade, use
  sempre o nome mais completo (ex: "Napoleão" e "Napoleão Bonaparte" viram uma
  única entidade "Napoleão Bonaparte"). Não crie entidades para termos
  genéricos como "documento", "capítulo", "autor", "texto".
- "relacoes": no máximo 6, apenas entre entidades listadas acima. "descricao"
  tem no máximo 10 palavras. "forca" é um inteiro de 1 a 10 indicando a
  intensidade/importância da relação."""

_EXEMPLO_ENTIDADES_RELACOES = """Exemplo:
Texto: \"\"\"Napoleão Bonaparte venceu a Batalha de Austerlitz em 1805. A vitória
consolidou seu domínio sobre a Europa central.\"\"\"
Saída: {"entidades": [{"nome": "Napoleão Bonaparte", "tipo": "Personagem", "descricao": "Venceu a Batalha de Austerlitz em 1805"}, {"nome": "Batalha de Austerlitz", "tipo": "Evento", "descricao": "Vitória que consolidou o domínio de Napoleão na Europa central"}], "relacoes": [{"origem": "Napoleão Bonaparte", "destino": "Batalha de Austerlitz", "descricao": "venceu essa batalha", "forca": 8}]}"""


def _parse_entidades(raw) -> list[dict]:
    """Normaliza a lista de entidades vinda do JSON do LLM, descartando itens
    sem nome/tipo."""
    if not isinstance(raw, list):
        return []
    entidades = []
    for item in raw:
        if isinstance(item, dict) and item.get("nome") and item.get("tipo"):
            entidades.append({
                "nome": str(item["nome"]).strip(),
                "tipo": str(item["tipo"]).strip(),
                "descricao": str(item.get("descricao", "")).strip(),
            })
    return entidades


def _parse_relacoes(raw) -> list[dict]:
    """Normaliza a lista de relações vinda do JSON do LLM, descartando itens
    sem origem/destino."""
    if not isinstance(raw, list):
        return []
    relacoes = []
    for item in raw:
        if isinstance(item, dict) and item.get("origem") and item.get("destino"):
            relacoes.append({
                "origem": str(item["origem"]).strip(),
                "destino": str(item["destino"]).strip(),
                "descricao": str(item.get("descricao", "")).strip(),
                "forca": item.get("forca", 5),
            })
    return relacoes


def _split_prosa_json(raw: str, marker: str) -> tuple[str, dict | None]:
    """Separa uma resposta "prosa + JSON no final": o texto antes do JSON é
    o resumo, o restante é decodificado. O modelo escreve prosa muito melhor
    fora de string JSON, então os dois saem em partes distintas."""
    text = re.sub(r"```(?:json)?", "", raw).strip()
    start = text.find(marker)
    if start == -1:
        start = text.find("{")
    if start == -1:
        return text, None
    prosa = text[:start].strip()
    try:
        return prosa, _extract_json(text[start:])
    except ValueError:
        return prosa, None


def _analisar_lote(texto: str) -> dict:
    """Lê um lote de chunks UMA ÚNICA VEZ e extrai, na mesma chamada, o
    resumo parcial (prosa livre, fora do JSON) e as entidades/relações
    citadas nele (JSON ao final da resposta)."""
    prompt = f"""Leia o trecho de documento abaixo e responda em DUAS partes, nesta ordem:

PARTE 1: o resumo do trecho em português, em 2 a 4 parágrafos detalhados
separados por linha em branco, cobrindo os acontecimentos, conceitos e
exemplos na ordem em que aparecem, sem omitir eventos importantes. Escreva
como material de estudo: quem não leu o documento original deve conseguir
estudar o assunto só por este resumo. Sem títulos, listas ou markdown, só
parágrafos de texto.

PARTE 2: um JSON válido em uma linha nova após o resumo, no formato:
{{"entidades": [{{"nome": "...", "tipo": "...", "descricao": "..."}}], "relacoes": [{{"origem": "...", "destino": "...", "descricao": "...", "forca": 1}}]}}

Regras do JSON:
{_REGRAS_ENTIDADES_RELACOES}

{_EXEMPLO_ENTIDADES_RELACOES}

Trecho:
\"\"\"{texto}\"\"\"
"""
    resumo, data = "", None
    for _ in range(2):
        raw = llm.complete(prompt).text
        prosa, data = _split_prosa_json(raw, '{"entidades"')
        if prosa:
            resumo = prosa
        if isinstance(data, dict):
            break

    if not isinstance(data, dict):
        logger.warning("Falha ao analisar lote: JSON inválido após retries")
        data = {}
    # compat: se o modelo devolver tudo num JSON só (formato antigo), o
    # resumo vem dentro dele
    if not resumo and data.get("resumo_parcial"):
        resumo = str(data["resumo_parcial"]).strip()

    return {
        "resumo_parcial": resumo,
        "entidades": _parse_entidades(data.get("entidades")),
        "relacoes": _parse_relacoes(data.get("relacoes")),
    }


def _resumo_documento_pequeno(texto: str, fallback_titulo: str) -> dict:
    """Documento pequeno, chamada 1 de 2: resumo estruturado. Roda em
    paralelo com a chamada de grafo, dividir as duas mantém o decode nas
    duas streams em vez de concentrar tudo numa só."""
    prompt = f"""Leia o documento abaixo e responda com um JSON válido, e SOMENTE o JSON,
no formato:
{{"titulo": "título curto do documento", "topicos_chave": ["ponto 1", "ponto 2", "ponto 3", "ponto 4"], "texto": "resumo do documento em português, 4 a 6 parágrafos detalhados"}}

- "topicos_chave" tem de 4 a 6 itens curtos.
- "texto" cobre os acontecimentos, conceitos e exemplos do documento em 4 a 6
  parágrafos detalhados, na ordem do texto. Escreva como material de estudo:
  quem não leu o documento original deve conseguir estudar o assunto só por
  este resumo.

Documento:
\"\"\"{texto}\"\"\"
"""
    try:
        data = _complete_json(prompt, attempts=2)
        return {
            "titulo": data.get("titulo") or fallback_titulo,
            "topicos_chave": data.get("topicos_chave") or [],
            "texto": data.get("texto") or "",
        }
    except ValueError:
        logger.warning("Falha no resumo: JSON inválido após retries")

    # fallback: JSON falhou nas tentativas, pede só o texto puro do resumo
    texto_puro = llm.complete(
        "Resuma o conteúdo abaixo em português, cobrindo os pontos principais "
        f"de forma clara e objetiva.\n\n\"\"\"{texto}\"\"\""
    ).text
    return {"titulo": fallback_titulo, "topicos_chave": [], "texto": texto_puro}


def _grafo_documento_pequeno(texto: str) -> dict:
    """Documento pequeno, chamada 2 de 2: entidades, relações e temas do
    mapa mental numa chamada só (os temas referenciam as próprias entidades
    extraídas aqui, então ficam consistentes por construção)."""
    prompt = f"""Leia o documento abaixo e responda com um JSON válido, e SOMENTE o JSON,
no formato:
{{"entidades": [{{"nome": "...", "tipo": "...", "descricao": "..."}}], "relacoes": [{{"origem": "...", "destino": "...", "descricao": "...", "forca": 1}}], "temas": [{{"titulo": "...", "entidades": ["nome", "..."]}}]}}

Regras:
{_REGRAS_ENTIDADES_RELACOES}
- "temas": de 3 a 6 temas que organizam as entidades por ASSUNTO do
  conteúdo. O "titulo" de cada tema é ESPECÍFICO do conteúdo (ex: "A Revolta
  das Cores"), NUNCA uma categoria genérica como "Personagens" ou
  "Conceitos". "entidades" é a lista de nomes (dentre os listados acima) que
  pertencem a esse tema.

{_EXEMPLO_ENTIDADES_RELACOES}

Documento:
\"\"\"{texto}\"\"\"
"""
    try:
        data = _complete_json(prompt, attempts=2)
    except ValueError:
        logger.warning("Falha no grafo: JSON inválido após retries")
        return {"entidades": [], "relacoes": [], "temas": []}

    if not isinstance(data, dict):
        return {"entidades": [], "relacoes": [], "temas": []}

    return {
        "entidades": _parse_entidades(data.get("entidades")),
        "relacoes": _parse_relacoes(data.get("relacoes")),
        "temas": data.get("temas") or [],
    }


def _consolidar(parciais: list[str], nomes_entidades: list[str], fallback_titulo: str) -> dict:
    """Etapa reduce do documento grande: recebe os resumos parciais dos
    lotes (já cobrindo o documento inteiro) e os nomes das entidades já
    fundidas, e devolve o resumo final estruturado mais os temas do mapa
    mental. Não recebe entidades/relações cruas, essas já vieram dos
    lotes."""
    texto_fonte = "\n\n".join(p for p in parciais if p)
    prompt = f"""Leia os resumos parciais abaixo (cada um cobre uma parte do documento, na
ordem em que aparece) e a lista de entidades já identificadas no documento.
Responda com um JSON válido, e SOMENTE o JSON, no formato:
{{"titulo": "...", "topicos_chave": ["...", "..."], "texto": "...", "temas": [{{"titulo": "...", "entidades": ["nome", "..."]}}]}}

Regras:
- "titulo": título curto do documento.
- "topicos_chave": 4 a 6 itens curtos com os principais pontos.
- "texto": visão geral do documento em português, 1 a 2 parágrafos que
  apresentam a obra e seus pontos centrais (os resumos parciais viram o corpo
  do resumo final, então aqui é só a abertura).
- "temas": de 3 a 6 temas que organizam as entidades listadas abaixo por
  ASSUNTO do conteúdo. O "titulo" de cada tema é ESPECÍFICO do conteúdo (ex:
  "A Revolta das Cores"), NUNCA uma categoria genérica como "Personagens" ou
  "Conceitos". "entidades" é a lista de nomes (dentre os listados abaixo)
  que pertencem a esse tema.

Resumos parciais:
\"\"\"{texto_fonte}\"\"\"

Entidades já identificadas no documento:
{", ".join(nomes_entidades) or "nenhuma"}
"""
    try:
        data = _complete_json(prompt, attempts=2)
        return {
            "titulo": data.get("titulo") or fallback_titulo,
            "topicos_chave": data.get("topicos_chave") or [],
            "texto": data.get("texto") or "",
            "temas": data.get("temas") or [],
        }
    except ValueError:
        logger.warning("Falha na consolidação: JSON inválido após retries")
        # texto vazio: os parciais já compõem o corpo do resumo no caller
        return {"titulo": fallback_titulo, "topicos_chave": [], "texto": "", "temas": []}


def _merge_entities(raw_entities: list[dict]) -> list[dict]:
    """Funde entidades com o mesmo nome extraídas de lotes (ou da mega-
    chamada) diferentes. O número de menções vira um proxy de importância,
    usado depois pra ranquear as entidades dentro de cada tema."""
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


# ---------------------------------------------------------------------------
# Mapa mental
# ---------------------------------------------------------------------------

def _no_tema_central(titulo: str) -> dict:
    return {
        "id": "1",
        "type": "tema_central",
        "data": {"label": titulo, "conteudo": f"Visão geral de {titulo}, organizada a partir do conteúdo indexado."},
    }


def _temas_validos(temas) -> list[dict]:
    """Filtra a lista de temas vinda do LLM, mantendo só os que têm título e
    ao menos uma entidade associada."""
    if not isinstance(temas, list):
        return []
    validos = []
    for tema in temas:
        if not isinstance(tema, dict):
            continue
        titulo = str(tema.get("titulo", "")).strip()
        entidades = tema.get("entidades")
        if not titulo or not isinstance(entidades, list) or not entidades:
            continue
        nomes = [str(n).strip() for n in entidades if str(n).strip()]
        if nomes:
            validos.append({"titulo": titulo, "entidades": nomes})
    return validos


def _agrupar_por_tema(entities: list[dict], temas_ok: list[dict], titulo: str) -> tuple[list, list, dict]:
    """Plano A: agrupa as entidades nos temas de conteúdo nomeados pelo LLM.
    Entidades sobrando (não citadas em nenhum tema) caem num tema "Outros",
    se houver espaço."""
    entities_by_key = {e["nome"].lower(): e for e in entities}
    nodes = [_no_tema_central(titulo)]
    edges = []
    usados: set[str] = set()
    detalhe_id_por_key: dict[str, str] = {}

    def _adicionar_categoria(cat_id: str, label: str, candidatos: list[dict]):
        detalhes = sorted(candidatos, key=lambda e: e["mencoes"], reverse=True)[:MAX_DETALHES_POR_TEMA]
        nodes.append({
            "id": cat_id,
            "type": "categoria",
            "data": {"label": label, "conteudo": f"{len(detalhes)} itens relacionados a {label.lower()}"},
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
            detalhe_id_por_key[ent["nome"].lower()] = det_id

    n_categorias = 0
    for tema in temas_ok[:MAX_TEMAS]:
        candidatos = []
        for nome in tema["entidades"]:
            key = nome.lower()
            if key in entities_by_key and key not in usados:
                candidatos.append(entities_by_key[key])
                usados.add(key)
        if not candidatos:
            continue
        n_categorias += 1
        _adicionar_categoria(f"cat-{n_categorias}", tema["titulo"], candidatos)

    sobra = [e for e in entities if e["nome"].lower() not in usados]
    if sobra and n_categorias < MAX_TEMAS:
        _adicionar_categoria(f"cat-{n_categorias + 1}", "Outros", sobra)

    return nodes, edges, detalhe_id_por_key


def _agrupar_por_tipo(entities: list[dict], titulo: str) -> tuple[list, list, dict]:
    """Plano B (fallback): agrupa por "tipo" da entidade, comportamento
    antigo preservado pra quando o LLM não devolve temas válidos."""
    by_tipo: dict[str, list[dict]] = {}
    for ent in entities:
        by_tipo.setdefault(ent["tipo"], []).append(ent)

    categorias = sorted(by_tipo.items(), key=lambda kv: sum(e["mencoes"] for e in kv[1]), reverse=True)
    if len(categorias) > MAX_TEMAS:
        categorias = categorias[:MAX_TEMAS]

    nodes = [_no_tema_central(titulo)]
    edges = []

    for cat_idx, (tipo, ents) in enumerate(categorias, start=1):
        cat_id = f"cat-{cat_idx}"
        detalhes = sorted(ents, key=lambda e: e["mencoes"], reverse=True)[:MAX_DETALHES_POR_TEMA]

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

    return nodes, edges, {}


def _adicionar_edges_relacao(edges: list, relacoes: list[dict], detalhe_id_por_key: dict[str, str]) -> list:
    """Acrescenta edges de relação entre nodes "detalhe" já presentes no
    mapa. Dedup por par de entidades (ordem indiferente), mantendo a de
    maior força, com um teto de MAX_RELACOES_NO_MAPA edges."""
    if not detalhe_id_por_key or not relacoes:
        return edges

    melhores: dict[frozenset, tuple] = {}
    for rel in relacoes:
        origem_key = rel["origem"].lower()
        destino_key = rel["destino"].lower()
        if not origem_key or not destino_key or origem_key == destino_key:
            continue
        source_id = detalhe_id_por_key.get(origem_key)
        target_id = detalhe_id_por_key.get(destino_key)
        if not source_id or not target_id:
            continue
        try:
            forca = int(rel.get("forca", 5))
        except (TypeError, ValueError):
            forca = 5
        forca = max(1, min(10, forca))

        par = frozenset((origem_key, destino_key))
        if par not in melhores or forca > melhores[par][0]:
            melhores[par] = (forca, rel["descricao"], source_id, target_id)

    ranqueadas = sorted(melhores.values(), key=lambda v: v[0], reverse=True)[:MAX_RELACOES_NO_MAPA]
    for idx, (forca, descricao, source_id, target_id) in enumerate(ranqueadas, start=1):
        edges.append({
            "id": f"rel-{idx}",
            "source": source_id,
            "target": target_id,
            "type": "relacao",
            "data": {"label": descricao, "forca": forca},
        })
    return edges


def build_mind_map(entities: list[dict], relacoes: list[dict], temas: list, titulo: str) -> dict:
    """Monta nodes/edges do mapa mental agrupando as entidades por TEMA de
    conteúdo nomeado pelo LLM (plano A), com fallback pro agrupamento por
    tipo (plano B) quando os temas vierem vazios ou inválidos. Entidades
    "detalhe" que aparecem em relações ganham edges extras entre si."""
    if not entities:
        raise ValueError("Nenhuma entidade extraída do documento")

    temas_ok = _temas_validos(temas)
    if temas_ok:
        nodes, edges, detalhe_id_por_key = _agrupar_por_tema(entities, temas_ok, titulo)
        edges = _adicionar_edges_relacao(edges, relacoes, detalhe_id_por_key)
    else:
        nodes, edges, _ = _agrupar_por_tipo(entities, titulo)

    return {"nodes": nodes, "edges": edges}


_FLASHCARD_PATTERN = re.compile(r"Frente:\s*(.+?)\s*Verso:\s*(.+?)(?=\s*Frente:|\Z)", re.DOTALL | re.IGNORECASE)


def _parse_flashcards(text: str) -> list[dict]:
    """Extrai pares Frente/Verso de um texto simples, um modelo local pequeno
    erra bem menos nesse formato do que tentando produzir JSON válido."""
    flashcards = []
    for frente, verso in _FLASHCARD_PATTERN.findall(text):
        frente, verso = frente.strip(), verso.strip()
        if frente and verso:
            flashcards.append({"pergunta": frente, "resposta": verso})
    return flashcards


def _flashcards_from_range(chunks_range: list[BaseNode], n_cards: int = 5) -> list[dict]:
    """Amostra uma faixa de chunks e pede n_cards flashcards dela."""
    sampled = _sample_evenly(chunks_range, FLASHCARD_CHUNKS_PER_CALL)
    texto = "\n\n".join(node.get_content() for node in sampled)

    prompt = f"""Com base nos trechos abaixo, gere EXATAMENTE {n_cards} flashcards de estudo em português.

Responda cada flashcard EXATAMENTE neste formato de texto simples, um por bloco, sem
numeração, markdown ou JSON. A resposta do Verso tem no máximo 2 frases curtas:

Frente: <pergunta>
Verso: <resposta>

Trechos:
\"\"\"{texto}\"\"\"
"""
    return _parse_flashcards(llm.complete(prompt).text)


def generate_flashcards(nodes: list[BaseNode]) -> list[dict]:
    """Divide os nodes em faixas contíguas e gera flashcards de cada faixa em
    paralelo, direto dos chunks, sem depender do resumo."""
    if not nodes:
        raise ValueError("Documento sem chunks para gerar flashcards")

    faixa_size = max(1, len(nodes) // FLASHCARD_CALLS)
    faixas = [nodes[i:i + faixa_size] for i in range(0, len(nodes), faixa_size)][:FLASHCARD_CALLS]

    # documento pequeno gera menos faixas: cada chamada pede mais cards e o
    # mínimo aceito escala junto, senão 1 a 2 chunks nunca chegariam a 12
    n_cards = 5 if len(faixas) >= FLASHCARD_CALLS else min(10, -(-20 // len(faixas)))
    minimo = min(12, n_cards * len(faixas))

    def _gerar(faixa):
        return _flashcards_from_range(faixa, n_cards)

    with ThreadPoolExecutor(max_workers=len(faixas)) as executor:
        resultados = list(executor.map(_gerar, faixas))

    flashcards = [card for cards in resultados for card in cards]

    # só faz a rodada extra de retry se o total ficou abaixo do mínimo
    if len(flashcards) < minimo:
        fracas = [i for i, cards in enumerate(resultados) if len(cards) < n_cards]
        if fracas:
            with ThreadPoolExecutor(max_workers=len(fracas)) as executor:
                retries = list(executor.map(_gerar, [faixas[i] for i in fracas]))
            for idx, cards in zip(fracas, retries):
                if len(cards) > len(resultados[idx]):
                    resultados[idx] = cards
            flashcards = [card for cards in resultados for card in cards]

    if len(flashcards) < minimo:
        # degradação graciosa: mantém os cards que saíram em vez de derrubar
        # o pipeline inteiro (resumo e mapa mental não dependem disso)
        logger.warning(
            "LLM gerou só %d flashcards válidos (mínimo %d), seguindo com o que saiu",
            len(flashcards), minimo,
        )

    return flashcards[:20]


def _analisar_documento_grande(
    lotes: list[str], fallback_titulo: str, inicio_etapa: float, executor: ThreadPoolExecutor, flash_future,
    on_phase_done=None,
) -> tuple[dict, list, list, list, dict]:
    """Caminho de documento grande: lotes de análise disparam em paralelo com
    os flashcards (mesma onda). A consolidação roda assim que os lotes
    terminam, mesmo que os flashcards ainda estejam rodando. Os parciais são
    devolvidos na ordem do documento (viram o corpo do resumo final).

    on_phase_done(nome), se passado, é chamado assim que cada material fica
    pronto de verdade: "flashcards" quando os cards terminam; "mapa_mental"
    assim que os lotes terminam (entidades/relações já são suficientes pra
    montar o grafo, só os NOMES dos temas ainda dependem da consolidação, o
    que não impede a montagem em si); "resumo" só quando a consolidação
    termina (o texto final depende dela). Usado pro frontend acompanhar o
    progresso real, inclusive pra distinguir qual etapa termina primeiro.

    flash_future é None quando flashcards não foi pedido: nesse caso a onda
    paralela cobre só os lotes de análise, sem agendar a fase de flashcards."""
    futures = {executor.submit(_analisar_lote, texto): idx for idx, texto in enumerate(lotes)}
    if flash_future is not None:
        futures[flash_future] = "flashcards"

    resultados_lote = [None] * len(lotes)
    concluidos = 0
    flashcards = None
    consolidado = None
    for future in as_completed(futures):
        chave = futures[future]
        if chave == "flashcards":
            try:
                flashcards = future.result()
            except Exception:
                # falha na fase de flashcards não pode derrubar resumo/mapa
                # já prontos: loga e segue sem o baralho
                logger.exception("Falha ao gerar flashcards, material de baralho será omitido")
                flashcards = []
            logger.info("flashcards: %.1fs", time.perf_counter() - inicio_etapa)
            if on_phase_done:
                on_phase_done("flashcards")
            continue

        resultado = future.result()
        resultados_lote[chave] = resultado
        concluidos += 1
        if concluidos == len(lotes):
            logger.info("analise: %.1fs", time.perf_counter() - inicio_etapa)
            raw_entidades = [ent for r in resultados_lote for ent in r["entidades"]]
            relacoes = [rel for r in resultados_lote for rel in r["relacoes"]]
            parciais = [r["resumo_parcial"] for r in resultados_lote if r["resumo_parcial"]]
            entidades = _merge_entities(raw_entidades)

            # entidades/relações já dão pra montar o grafo (a nomeação dos
            # temas na consolidação só refina os rótulos das categorias),
            # então o mapa mental conta como pronto aqui, antes do resumo.
            if on_phase_done:
                on_phase_done("mapa_mental")

            inicio_consolidacao = time.perf_counter()
            consolidado = _consolidar(parciais, [e["nome"] for e in entidades], fallback_titulo)
            logger.info("consolidacao: %.1fs", time.perf_counter() - inicio_consolidacao)
            if on_phase_done:
                on_phase_done("resumo")

    return consolidado, entidades, relacoes, parciais, flashcards


def generate_materials(
    nodes: list[BaseNode],
    fallback_titulo: str = "Documento",
    subject_id=None,
    on_phase_done=None,
    tipos: set[str] | None = None,
) -> list[dict]:
    """Roda o pipeline do documento e retorna só os materiais pedidos, cada
    um no mesmo formato: {tipo, titulo, subject_id, creation_date, conteudo}.

    tipos: subconjunto de MATERIAIS_VALIDOS ("resumo", "mapa_mental",
    "flashcards"). None (default) gera os três. A onda paralela só agenda o
    que foi pedido: sem "resumo" nem "mapa_mental", a análise do documento
    (mega-chamada do doc pequeno ou lotes map-reduce do doc grande) nem roda,
    já que ela só serve pra montar esses dois materiais.

    Documento pequeno: uma mega-chamada lê o texto inteiro UMA vez e devolve
    resumo + entidades + relações + temas juntos. Documento grande: lotes de
    análise em paralelo (cada um também lido uma única vez) seguidos de uma
    consolidação. Em ambos os casos, os flashcards rodam na mesma onda
    paralela, sem depender do resultado da análise.

    on_phase_done(nome: "resumo"|"mapa_mental"|"flashcards"), se passado, só
    é chamado pras fases pedidas, assim que cada material fica pronto de
    verdade (não é uma simulação: reflete quando aquela etapa realmente
    terminou no backend).
    """
    tipos = tipos if tipos is not None else set(MATERIAIS_VALIDOS)
    quer_resumo = "resumo" in tipos
    quer_mapa = "mapa_mental" in tipos
    quer_flash = "flashcards" in tipos
    precisa_analise = quer_resumo or quer_mapa

    def _notify(nome: str) -> None:
        if on_phase_done and nome in tipos:
            on_phase_done(nome)

    inicio_total = time.perf_counter()
    pequeno = len(nodes) <= SUMMARY_CHUNKS_PER_CALL

    titulo_base = fallback_titulo
    topicos_chave: list = []
    texto_resumo = ""
    entidades: list[dict] = []
    relacoes: list[dict] = []
    temas: list = []
    flashcards = None

    if pequeno:
        texto = "\n\n".join(node.get_content() for node in nodes) if precisa_analise else None
        with ThreadPoolExecutor(max_workers=max(1, quer_resumo + quer_mapa + quer_flash)) as executor:
            futures = {}
            if quer_resumo:
                futures[executor.submit(_resumo_documento_pequeno, texto, fallback_titulo)] = "resumo"
            if quer_mapa:
                futures[executor.submit(_grafo_documento_pequeno, texto)] = "grafo"
            if quer_flash:
                futures[executor.submit(generate_flashcards, nodes)] = "flashcards"

            inicio_etapa = time.perf_counter()
            resumo = None
            grafo = None
            for future in as_completed(futures):
                nome = futures[future]
                if nome == "flashcards":
                    try:
                        flashcards = future.result()
                    except Exception:
                        # falha na fase de flashcards não pode derrubar
                        # resumo/mapa já prontos: loga e segue sem o baralho
                        logger.exception("Falha ao gerar flashcards, material de baralho será omitido")
                        flashcards = []
                    logger.info("%s: %.1fs", nome, time.perf_counter() - inicio_etapa)
                    _notify("flashcards")
                    continue

                resultado = future.result()
                logger.info("%s: %.1fs", nome, time.perf_counter() - inicio_etapa)
                if nome == "resumo":
                    resumo = resultado
                    _notify("resumo")
                else:
                    grafo = resultado
                    _notify("mapa_mental")

        if quer_resumo:
            titulo_base = resumo["titulo"]
            topicos_chave = resumo["topicos_chave"]
            texto_resumo = resumo["texto"]
        if quer_mapa:
            entidades = _merge_entities(grafo["entidades"])
            relacoes = grafo["relacoes"]
            temas = grafo["temas"]
    elif precisa_analise:
        lotes = [
            "\n\n".join(node.get_content() for node in nodes[i:i + SUMMARY_CHUNKS_PER_CALL])
            for i in range(0, len(nodes), SUMMARY_CHUNKS_PER_CALL)
        ]
        logger.info("Análise: map-reduce de %d chunks em %d lotes", len(nodes), len(lotes))

        with ThreadPoolExecutor(max_workers=len(lotes) + (1 if quer_flash else 0)) as executor:
            inicio_etapa = time.perf_counter()
            flash_future = executor.submit(generate_flashcards, nodes) if quer_flash else None
            consolidado, entidades, relacoes, parciais, flashcards = _analisar_documento_grande(
                lotes, fallback_titulo, inicio_etapa, executor, flash_future, on_phase_done=_notify
            )

        titulo_base = consolidado["titulo"]
        topicos_chave = consolidado["topicos_chave"]
        temas = consolidado["temas"]
        # o corpo do resumo são os parciais na ordem do documento (cobrem o
        # texto inteiro), a consolidação entra como visão geral de abertura
        partes = ([consolidado["texto"]] if consolidado["texto"] else []) + parciais
        texto_resumo = "\n\n".join(partes)
    elif quer_flash:
        # nem resumo nem mapa_mental pedidos: pula a análise do documento
        # inteira (mega-chamada/lotes só servem a esses dois materiais)
        inicio_etapa = time.perf_counter()
        try:
            flashcards = generate_flashcards(nodes)
        except Exception:
            logger.exception("Falha ao gerar flashcards, material de baralho será omitido")
            flashcards = []
        logger.info("flashcards: %.1fs", time.perf_counter() - inicio_etapa)
        _notify("flashcards")

    mapa_mental = None
    if quer_mapa:
        # degradação graciosa: sem entidades (LLM falhou no grafo), entrega
        # resumo e flashcards mesmo assim, só omite o mapa mental
        try:
            mapa_mental = build_mind_map(entidades, relacoes, temas, titulo_base)
        except ValueError:
            logger.warning("Sem entidades para o mapa mental, material omitido")
            mapa_mental = None

    logger.info("total: %.1fs", time.perf_counter() - inicio_total)

    creation_date = datetime.now().isoformat(timespec="seconds")
    materials = []

    if quer_resumo:
        materials.append({
            "tipo": "resumo",
            "titulo": titulo_base,
            "subject_id": subject_id,
            "creation_date": creation_date,
            "conteudo": {
                "texto": texto_resumo,
                "topicos_chave": topicos_chave,
            },
        })

    if quer_mapa and mapa_mental is not None:
        materials.append({
            "tipo": "mapa_mental",
            "titulo": f"{titulo_base} — Mapa Mental de Estudo",
            "subject_id": subject_id,
            "creation_date": creation_date,
            "conteudo": {
                "nodes": mapa_mental["nodes"],
                "edges": mapa_mental["edges"],
            },
        })

    if quer_flash:
        # degradação graciosa: sem flashcards (LLM falhou nessa fase),
        # entrega resumo e mapa mental mesmo assim, só omite o baralho
        if flashcards:
            materials.append({
                "tipo": "baralho",
                "titulo": f"{titulo_base} — Flashcards",
                "subject_id": subject_id,
                "creation_date": creation_date,
                "conteudo": {
                    "flashcards": flashcards,
                },
            })
        else:
            logger.warning("Sem flashcards para incluir no baralho, material omitido")

    return materials
