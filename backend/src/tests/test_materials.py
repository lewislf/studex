"""
Testes unitários puros de rag_api/materials.py (com mock, sem rede/Ollama).

materials.py está sendo reestruturado; estes testes cobrem o CONTRATO NOVO do
módulo, não o código legado que pode ainda estar em disco:

- generate_materials(nodes, fallback_titulo="Documento", subject_id=None) roda
  o pipeline inteiro e devolve [resumo, mapa_mental, baralho]; se nenhuma
  entidade foi extraída, o mapa_mental é OMITIDO (lista com 2 itens).
- Documento pequeno (<= SUMMARY_CHUNKS_PER_CALL nodes): 2 chamadas paralelas,
  uma de resumo ({"titulo","topicos_chave","texto"}) e uma de grafo
  ({"entidades","relacoes","temas"}). Documento grande: lotes paralelos
  ({"resumo_parcial","entidades","relacoes"}) seguidos de uma consolidação
  ({"titulo","topicos_chave","texto","temas"}).
- build_mind_map(entities, relacoes, temas, titulo) é função pura (sem LLM),
  monta nodes/edges a partir do que já foi extraído.
- generate_flashcards(nodes) degrada graciosamente: se o LLM não atingir o
  mínimo calculado, loga e devolve os cards que saíram (mesmo que vazio), sem
  levantar ValueError. generate_materials faz o mesmo na fase de flashcards:
  uma falha ali não derruba resumo/mapa já prontos, só omite o baralho.

Só generate_materials e build_mind_map são citados no contrato; nenhum outro
nome de função interna é testado diretamente, pra não travar em detalhe de
implementação de um refactor em andamento.

Toda chamada de LLM passa por materials.llm.complete(prompt) -> objeto com
.text. Esse atributo é mockado em todo teste (fixture mock_llm), então nenhuma
chamada real chega no Ollama.

materials.py faz `from search_query import llm`, e search_query.py importa
llama_index/fitz e instancia clientes Ollama de verdade. Pra importar
materials.py isolado (sem essas dependências pesadas), stubamos
sys.modules["search_query"] (e llama_index, se não estiver instalado) ANTES
do primeiro import do módulo, do mesmo jeito que routes/document_routes.py
adiciona rag_api/ ao sys.path pra importar materials como módulo top-level.
"""

import inspect
import json
import sys
import threading
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock

import pytest

RAG_API_DIR = Path(__file__).resolve().parent.parent / "rag_api"
if str(RAG_API_DIR) not in sys.path:
    sys.path.append(str(RAG_API_DIR))


def _stub_module(name: str) -> ModuleType:
    """Cria (ou reaproveita) um módulo fake em sys.modules, com __getattr__
    devolvendo MagicMock pra qualquer nome não definido explicitamente,
    assim um `from search_query import algo_novo` não quebra o import."""
    if name in sys.modules:
        return sys.modules[name]
    mod = ModuleType(name)
    mod.__getattr__ = lambda attr: MagicMock()
    sys.modules[name] = mod
    return mod


# Se llama_index já estiver instalado (ex: dentro do container), usa o
# pacote de verdade e não mexe em nada.
try:
    import llama_index  # noqa: F401
except ImportError:
    _core = _stub_module("llama_index.core")
    _schema = _stub_module("llama_index.core.schema")
    _schema.BaseNode = object
    _core.SummaryIndex = MagicMock
    _li = _stub_module("llama_index")
    _li.core = _core

# search_query só precisa expor `llm` pra materials.py importar; se o novo
# materials.py também usa outra coisa de lá, o __getattr__ acima cobre.
_search_query_stub = _stub_module("search_query")
if not hasattr(_search_query_stub, "llm"):
    _search_query_stub.llm = MagicMock()

import materials  # noqa: E402


@pytest.fixture(autouse=True)
def mock_llm(monkeypatch):
    """Troca materials.llm por um MagicMock novo a cada teste, garantindo
    que nenhum teste escape pra uma chamada real."""
    mock = MagicMock()
    monkeypatch.setattr(materials, "llm", mock)
    return mock


def make_nodes(n=20, prefix="chunk"):
    """Nodes fake com só o que materials.py usa: get_content(). O prefixo
    "chunk" funciona como marcador: qualquer prompt que leu conteúdo bruto
    dos nodes carrega a substring "chunk " (ver CHUNK_MARKER abaixo)."""
    nodes = []
    for i in range(n):
        node = MagicMock()
        node.get_content.return_value = f"{prefix} {i}"
        nodes.append(node)
    return nodes


def llm_response(text):
    """Simula o objeto de resposta do LLM: só o atributo .text importa."""
    resp = MagicMock()
    resp.text = text
    return resp


def flashcards_block(n=5, start=1):
    """Monta um bloco de texto Frente/Verso, no formato que o LLM deveria
    devolver por chamada."""
    blocks = []
    for i in range(start, start + n):
        blocks.append(f"Frente: Pergunta {i}\nVerso: Resposta {i}")
    return "\n".join(blocks)


# Marcador de conteúdo bruto dos chunks fake (ver make_nodes). Qualquer
# prompt que leu os nodes diretamente (chamadas do doc pequeno ou lote do
# doc grande) carrega isso; a chamada de consolidação (que só lê os resumos
# parciais já reduzidos) não carrega, e é assim que o side_effect diferencia
# as duas sem depender de nome de função interna.
CHUNK_MARKER = "chunk "


def _is_flashcard_prompt(prompt: str) -> bool:
    return "flashcard" in prompt.lower()


def _is_grafo_prompt(prompt: str) -> bool:
    """No doc pequeno, só o prompt de grafo pede "entidades"; o de resumo
    pede titulo/topicos_chave/texto sem citar entidades."""
    return "entidades" in prompt.lower()


def _has_chunk_marker(prompt: str) -> bool:
    return CHUNK_MARKER in prompt


def make_entity(nome, tipo="Conceito", descricao="d", mencoes=1):
    """Entidade já FUNDIDA (formato interno pós _merge_entities), que é o
    formato que build_mind_map espera: nome/tipo/descricao + mencoes (usado
    pra ranquear detalhes dentro de um tema/categoria)."""
    return {"nome": nome, "tipo": tipo, "descricao": descricao, "mencoes": mencoes}


def _node_by_label(nodes, tipo, label):
    """Acha um node do mapa mental pelo tipo e pelo label, sem depender do
    esquema de IDs (não é parte do contrato)."""
    for node in nodes:
        if node["type"] == tipo and node["data"]["label"] == label:
            return node
    raise AssertionError(f"node tipo={tipo} label={label!r} não encontrado")


def _relation_edges(edges):
    return [e for e in edges if e.get("type") == "relacao"]


def _hierarchy_edges(edges):
    return [e for e in edges if e.get("type") != "relacao"]


# ---------------------------------------------------------------------------
# Helpers estáveis: _extract_json e _parse_flashcards
# ---------------------------------------------------------------------------

def test_extract_json_objeto_simples():
    assert materials._extract_json('{"a": 1, "b": "x"}') == {"a": 1, "b": "x"}


def test_extract_json_com_markdown_e_texto_ao_redor():
    texto = 'Claro, aqui está:\n```json\n{"titulo": "T", "topicos_chave": ["a"]}\n```\nEspero ter ajudado!'
    assert materials._extract_json(texto) == {"titulo": "T", "topicos_chave": ["a"]}


def test_extract_json_lista():
    texto = 'Entidades encontradas: [{"nome": "X", "tipo": "Conceito"}] fim.'
    assert materials._extract_json(texto) == [{"nome": "X", "tipo": "Conceito"}]


def test_extract_json_sem_json_levanta_value_error():
    with pytest.raises(ValueError):
        materials._extract_json("desculpe, não consigo responder isso.")


def test_parse_flashcards_varios_blocos():
    texto = flashcards_block(3)
    cards = materials._parse_flashcards(texto)
    assert len(cards) == 3
    assert cards[0] == {"pergunta": "Pergunta 1", "resposta": "Resposta 1"}
    assert cards[-1] == {"pergunta": "Pergunta 3", "resposta": "Resposta 3"}


def test_parse_flashcards_sem_padrao_retorna_vazio():
    assert materials._parse_flashcards("não tem frente nem verso aqui") == []


# ---------------------------------------------------------------------------
# generate_flashcards (degrada graciosamente abaixo do mínimo, não levanta)
# ---------------------------------------------------------------------------

def test_generate_flashcards_entre_12_e_20_quando_llm_coopera(mock_llm):
    # cada chamada devolve 5 pares Frente/Verso; com nodes suficientes pra
    # disparar chamadas paralelas, o total agregado cai entre 12 e 20.
    mock_llm.complete.return_value = llm_response(flashcards_block(5))

    resultado = materials.generate_flashcards(make_nodes(20))

    assert 12 <= len(resultado) <= 20
    for card in resultado:
        assert set(card.keys()) == {"pergunta", "resposta"}
        assert card["pergunta"]
        assert card["resposta"]


def test_generate_flashcards_abaixo_do_minimo_nao_levanta_e_mantem_o_que_saiu(mock_llm):
    # LLM nunca devolve o padrão Frente/Verso -> 0 cards, mesmo após retry.
    # Antes derrubava o pipeline inteiro via ValueError; agora degrada.
    mock_llm.complete.return_value = llm_response("não sei gerar flashcards.")

    resultado = materials.generate_flashcards(make_nodes(20))

    assert resultado == []


def test_generate_flashcards_parcial_mantem_cards_que_sairam(mock_llm):
    # só a primeira faixa cooperou, as demais vieram vazias: mesmo abaixo do
    # mínimo, os cards que saíram não são descartados
    mock_llm.complete.side_effect = [
        llm_response(flashcards_block(5)),
        llm_response("sem cards"),
        llm_response("sem cards"),
        llm_response("sem cards"),
        # rodada de retry das faixas fracas
        llm_response("sem cards"),
        llm_response("sem cards"),
        llm_response("sem cards"),
    ]

    resultado = materials.generate_flashcards(make_nodes(20))

    assert 0 < len(resultado) < 12


# ---------------------------------------------------------------------------
# build_mind_map (função pura, sem LLM): entities/relacoes/temas -> nodes/edges
# ---------------------------------------------------------------------------

def test_build_mind_map_temas_atribuem_entidades():
    entities = [
        make_entity("TCP", "Protocolo", "controle de transporte"),
        make_entity("UDP", "Protocolo", "transporte sem conexão"),
        make_entity("Camada de Rede", "Conceito", "endereçamento e roteamento"),
    ]
    temas = [
        {"titulo": "Protocolos de Transporte", "entidades": ["TCP", "UDP"]},
        {"titulo": "Arquitetura em Camadas", "entidades": ["Camada de Rede"]},
    ]

    resultado = materials.build_mind_map(entities, [], temas, "Redes de Computadores")

    central = [n for n in resultado["nodes"] if n["type"] == "tema_central"]
    assert len(central) == 1
    assert central[0]["data"]["label"] == "Redes de Computadores"

    categorias = [n for n in resultado["nodes"] if n["type"] == "categoria"]
    # label da categoria é o TÍTULO DO TEMA, não o tipo da entidade
    assert {c["data"]["label"] for c in categorias} == {"Protocolos de Transporte", "Arquitetura em Camadas"}

    cat_transporte = _node_by_label(resultado["nodes"], "categoria", "Protocolos de Transporte")
    cat_camadas = _node_by_label(resultado["nodes"], "categoria", "Arquitetura em Camadas")
    tcp = _node_by_label(resultado["nodes"], "detalhe", "TCP")
    udp = _node_by_label(resultado["nodes"], "detalhe", "UDP")
    rede = _node_by_label(resultado["nodes"], "detalhe", "Camada de Rede")

    hierarquia = _hierarchy_edges(resultado["edges"])
    assert any(e["source"] == cat_transporte["id"] and e["target"] == tcp["id"] for e in hierarquia)
    assert any(e["source"] == cat_transporte["id"] and e["target"] == udp["id"] for e in hierarquia)
    assert any(e["source"] == cat_camadas["id"] and e["target"] == rede["id"] for e in hierarquia)


def test_build_mind_map_entidade_orfa_vai_para_outros():
    entities = [
        make_entity("X", "Conceito", "no tema"),
        make_entity("Orfa", "Conceito", "não está em nenhum tema"),
    ]
    temas = [{"titulo": "Tema A", "entidades": ["X"]}]

    resultado = materials.build_mind_map(entities, [], temas, "Titulo")

    outros = _node_by_label(resultado["nodes"], "categoria", "Outros")
    orfa = _node_by_label(resultado["nodes"], "detalhe", "Orfa")
    hierarquia = _hierarchy_edges(resultado["edges"])
    assert any(e["source"] == outros["id"] and e["target"] == orfa["id"] for e in hierarquia)


def test_build_mind_map_relacao_com_endpoint_inexistente_e_ignorada():
    entities = [
        make_entity("TCP", "Protocolo", "d1"),
        make_entity("UDP", "Protocolo", "d2"),
    ]
    temas = [{"titulo": "Transporte", "entidades": ["TCP", "UDP"]}]
    relacoes = [
        {"origem": "TCP", "destino": "UDP", "descricao": "ambos ficam na camada de transporte", "forca": 5},
        {"origem": "TCP", "destino": "Inexistente", "descricao": "endpoint não extraído", "forca": 9},
    ]

    resultado = materials.build_mind_map(entities, relacoes, temas, "Titulo")

    # não pode quebrar, e só a relação com os dois lados existentes vira edge
    relacao_edges = _relation_edges(resultado["edges"])
    assert len(relacao_edges) == 1


def test_build_mind_map_dedup_de_relacao_fica_com_maior_forca():
    entities = [
        make_entity("TCP", "Protocolo", "d1"),
        make_entity("UDP", "Protocolo", "d2"),
    ]
    temas = [{"titulo": "Transporte", "entidades": ["TCP", "UDP"]}]
    relacoes = [
        {"origem": "TCP", "destino": "UDP", "descricao": "fraca", "forca": 3},
        {"origem": "TCP", "destino": "UDP", "descricao": "forte", "forca": 9},
    ]

    resultado = materials.build_mind_map(entities, relacoes, temas, "Titulo")

    relacao_edges = _relation_edges(resultado["edges"])
    assert len(relacao_edges) == 1
    assert relacao_edges[0]["data"]["forca"] == 9


def test_build_mind_map_teto_de_temas_e_detalhes():
    # 8 temas (teto é 6), um item cada
    entities = [make_entity(f"Item{i}") for i in range(8)]
    temas = [{"titulo": f"Tema{i}", "entidades": [f"Item{i}"]} for i in range(8)]

    resultado = materials.build_mind_map(entities, [], temas, "Titulo")
    categorias = [n for n in resultado["nodes"] if n["type"] == "categoria"]
    assert len(categorias) == 6

    # 1 tema com 10 entidades (teto é 8 detalhes por tema)
    entities_muitas = [make_entity(f"Sub{i}") for i in range(10)]
    temas_muitas = [{"titulo": "TemaGrande", "entidades": [f"Sub{i}" for i in range(10)]}]

    resultado2 = materials.build_mind_map(entities_muitas, [], temas_muitas, "Titulo")
    detalhes = [n for n in resultado2["nodes"] if n["type"] == "detalhe"]
    assert len(detalhes) == 8


def test_build_mind_map_teto_de_relacoes_em_25():
    nomes = [f"E{i}" for i in range(8)]
    entities = [make_entity(nome) for nome in nomes]
    temas = [{"titulo": "Tema", "entidades": nomes}]

    # todos os pares distintos entre 8 entidades: C(8,2) = 28, acima do teto de 25
    relacoes = []
    for i in range(len(nomes)):
        for j in range(i + 1, len(nomes)):
            relacoes.append({
                "origem": nomes[i],
                "destino": nomes[j],
                "descricao": f"{nomes[i]}-{nomes[j]}",
                "forca": 5,
            })
    assert len(relacoes) == 28

    resultado = materials.build_mind_map(entities, relacoes, temas, "Titulo")
    assert len(_relation_edges(resultado["edges"])) == 25


def test_build_mind_map_temas_vazio_agrupa_por_tipo():
    # comportamento antigo: sem temas, cai pra agrupar por "tipo" da entidade
    entities = [
        make_entity("TCP", "Protocolo", "d1"),
        make_entity("Camada de Rede", "Conceito", "d2"),
    ]

    resultado = materials.build_mind_map(entities, [], [], "Titulo")

    categorias = {n["data"]["label"] for n in resultado["nodes"] if n["type"] == "categoria"}
    assert categorias == {"Protocolo", "Conceito"}


def test_build_mind_map_sem_entidades_levanta_value_error():
    with pytest.raises(ValueError):
        materials.build_mind_map([], [], [], "Tema Vazio")


# ---------------------------------------------------------------------------
# generate_materials: pipeline completo via mock de materials.llm.complete
# ---------------------------------------------------------------------------

def test_generate_materials_doc_pequeno_duas_chamadas(mock_llm):
    """Documento <= SUMMARY_CHUNKS_PER_CALL: 2 chamadas paralelas, uma de
    resumo (titulo/topicos_chave/texto) e uma de grafo (entidades/relacoes/
    temas), + FLASHCARD_CALLS chamadas de flashcards, nenhuma outra."""
    resumo_json = json.dumps({
        "titulo": "Modelo TCP/IP",
        "topicos_chave": ["camadas", "protocolos"],
        "texto": "Resumo do conteúdo sobre TCP/IP.",
    })
    grafo_json = json.dumps({
        "entidades": [
            {"nome": "TCP", "tipo": "Protocolo", "descricao": "controle de transporte"},
            {"nome": "IP", "tipo": "Protocolo", "descricao": "endereçamento"},
            {"nome": "UDP", "tipo": "Protocolo", "descricao": "transporte sem conexão"},
        ],
        "relacoes": [
            {"origem": "TCP", "destino": "IP", "descricao": "TCP roda sobre IP", "forca": 8},
        ],
        "temas": [
            {"titulo": "Camadas de Rede", "entidades": ["TCP", "IP"]},
            {"titulo": "Protocolos", "entidades": ["UDP"]},
        ],
    })

    def _side_effect(prompt):
        if _is_flashcard_prompt(prompt):
            return llm_response(flashcards_block(5))
        if _is_grafo_prompt(prompt):
            return llm_response(grafo_json)
        return llm_response(resumo_json)

    mock_llm.complete.side_effect = _side_effect

    nodes = make_nodes(10)
    materiais = materials.generate_materials(nodes, fallback_titulo="Fallback", subject_id=3)

    prompts = [c.args[0] if c.args else c.kwargs["prompt"] for c in mock_llm.complete.call_args_list]
    chamadas_resumo = [p for p in prompts if not _is_flashcard_prompt(p) and not _is_grafo_prompt(p)]
    chamadas_grafo = [p for p in prompts if not _is_flashcard_prompt(p) and _is_grafo_prompt(p)]
    chamadas_flash = [p for p in prompts if _is_flashcard_prompt(p)]
    # exatamente 1 de resumo + 1 de grafo: prova que não teve lote/consolidação
    assert len(chamadas_resumo) == 1
    assert len(chamadas_grafo) == 1
    assert len(chamadas_flash) == materials.FLASHCARD_CALLS

    assert len(materiais) == 3
    assert {m["tipo"] for m in materiais} == {"resumo", "mapa_mental", "baralho"}
    for m in materiais:
        assert m["subject_id"] == 3

    resumo = next(m for m in materiais if m["tipo"] == "resumo")
    assert resumo["titulo"] == "Modelo TCP/IP"  # titulo veio do JSON, não do fallback
    assert resumo["conteudo"]["texto"] == "Resumo do conteúdo sobre TCP/IP."
    assert resumo["conteudo"]["topicos_chave"] == ["camadas", "protocolos"]

    mapa = next(m for m in materiais if m["tipo"] == "mapa_mental")
    categorias = {n["data"]["label"] for n in mapa["conteudo"]["nodes"] if n["type"] == "categoria"}
    # mapa agrupado pelos temas nomeados, não pelo tipo ("Protocolo")
    assert categorias == {"Camadas de Rede", "Protocolos"}

    relacao_edges = _relation_edges(mapa["conteudo"]["edges"])
    assert len(relacao_edges) == 1
    assert relacao_edges[0]["data"]["forca"] == 8

    baralho = next(m for m in materiais if m["tipo"] == "baralho")
    assert len(baralho["conteudo"]["flashcards"]) > 0


def test_generate_materials_doc_grande_lotes_mais_consolidacao(mock_llm):
    """Documento > SUMMARY_CHUNKS_PER_CALL: N chamadas de lote (resumo_parcial
    + entidades + relações) rodando em paralelo, seguidas de 1 consolidação
    (titulo + topicos_chave + texto + temas). Entidades repetidas em lotes
    diferentes são fundidas num único node no mapa final."""
    n_nodes = 60
    n_lotes_esperado = -(-n_nodes // materials.SUMMARY_CHUNKS_PER_CALL)  # ceil

    lote_respostas = [
        json.dumps({
            "resumo_parcial": "parcial 1",
            "entidades": [{"nome": "Rede Neural", "tipo": "Conceito", "descricao": "modelo de aprendizado"}],
            "relacoes": [],
        }),
        json.dumps({
            "resumo_parcial": "parcial 2",
            "entidades": [
                {"nome": "Rede Neural", "tipo": "Conceito", "descricao": "camadas de neurônios"},
                {"nome": "Grafo", "tipo": "Estrutura", "descricao": "nós e arestas"},
            ],
            "relacoes": [],
        }),
        json.dumps({
            "resumo_parcial": "parcial 3",
            "entidades": [{"nome": "Grafo", "tipo": "Estrutura", "descricao": "representação de dados"}],
            "relacoes": [],
        }),
    ]
    consolidacao_json = json.dumps({
        "titulo": "Aprendizado de Máquina",
        "topicos_chave": ["modelos", "estruturas"],
        "texto": "Resumo consolidado do documento inteiro.",
        "temas": [
            {"titulo": "Modelos e Estruturas", "entidades": ["Rede Neural", "Grafo"]},
        ],
    })

    lock = threading.Lock()
    contador = {"lote": 0}

    def _side_effect(prompt):
        if _is_flashcard_prompt(prompt):
            return llm_response(flashcards_block(5))
        if _has_chunk_marker(prompt):
            with lock:
                idx = contador["lote"]
                contador["lote"] += 1
            return llm_response(lote_respostas[idx % len(lote_respostas)])
        # sem marcador de chunk bruto: só pode ser a consolidação, que lê
        # os "resumo_parcial" já reduzidos, nunca o texto original dos nodes
        return llm_response(consolidacao_json)

    mock_llm.complete.side_effect = _side_effect

    nodes = make_nodes(n_nodes)
    materiais = materials.generate_materials(nodes, fallback_titulo="Fallback", subject_id=None)

    prompts = [c.args[0] if c.args else c.kwargs["prompt"] for c in mock_llm.complete.call_args_list]
    chamadas_lote = [p for p in prompts if not _is_flashcard_prompt(p) and _has_chunk_marker(p)]
    chamadas_consolidacao = [p for p in prompts if not _is_flashcard_prompt(p) and not _has_chunk_marker(p)]
    assert len(chamadas_lote) == n_lotes_esperado
    assert len(chamadas_consolidacao) == 1

    mapa = next(m for m in materiais if m["tipo"] == "mapa_mental")
    # "Rede Neural" apareceu em 2 lotes e "Grafo" em outros 2: cada um vira
    # UM SÓ node de detalhe no mapa final, não um por lote (fusão de entidades)
    detalhes_rede_neural = [n for n in mapa["conteudo"]["nodes"] if n["type"] == "detalhe" and n["data"]["label"] == "Rede Neural"]
    detalhes_grafo = [n for n in mapa["conteudo"]["nodes"] if n["type"] == "detalhe" and n["data"]["label"] == "Grafo"]
    assert len(detalhes_rede_neural) == 1
    assert len(detalhes_grafo) == 1

    resumo = next(m for m in materiais if m["tipo"] == "resumo")
    assert resumo["titulo"] == "Aprendizado de Máquina"


def test_generate_materials_sem_entidades_omite_mapa_mental(mock_llm):
    """Degradação graciosa: se a chamada de grafo (doc pequeno) falha o JSON
    nas 2 tentativas, nenhuma entidade é extraída e o material mapa_mental é
    OMITIDO, sem levantar erro: a lista sai com 2 itens (resumo + baralho).
    Aqui o resumo também falha o JSON e cai no texto puro (titulo=fallback),
    o pior cenário de LLM ainda entrega resumo e flashcards."""

    def _side_effect(prompt):
        if _is_flashcard_prompt(prompt):
            return llm_response(flashcards_block(5))
        if _is_grafo_prompt(prompt):
            # grafo nunca acerta o JSON -> entidades vazias
            return llm_response("não consigo gerar um JSON de grafo agora.")
        if "topicos_chave" in prompt:
            # resumo estruturado também falha o JSON nas 2 tentativas
            return llm_response("não consigo gerar um JSON válido agora.")
        # fallback do resumo: pedido de texto puro
        return llm_response("Resumo em texto puro, sem JSON.")

    mock_llm.complete.side_effect = _side_effect

    nodes = make_nodes(10)
    materiais = materials.generate_materials(nodes, fallback_titulo="Titulo Fallback", subject_id=None)

    # mapa_mental omitido: 2 materiais em vez de 3
    assert len(materiais) == 2
    assert [m["tipo"] for m in materiais if m["tipo"] == "mapa_mental"] == []
    assert {m["tipo"] for m in materiais} == {"resumo", "baralho"}

    resumo = next(m for m in materiais if m["tipo"] == "resumo")
    assert resumo["titulo"] == "Titulo Fallback"
    assert resumo["conteudo"]["texto"] == "Resumo em texto puro, sem JSON."
    assert resumo["conteudo"]["topicos_chave"] == []

    baralho = next(m for m in materiais if m["tipo"] == "baralho")
    assert len(baralho["conteudo"]["flashcards"]) > 0


def test_generate_materials_flashcards_abaixo_do_minimo_omite_baralho(mock_llm):
    """Bug 1 da auditoria: doc pequeno, LLM nunca acerta o padrão Frente/
    Verso -> 0 flashcards. Antes isso levantava ValueError no future.result()
    e derrubava resumo/mapa já prontos (rota caía pro 207 sem nada). Agora o
    pipeline degrada como já fazia pro mapa_mental: baralho OMITIDO, resumo e
    mapa_mental saem normalmente."""
    resumo_json = json.dumps({
        "titulo": "Modelo TCP/IP",
        "topicos_chave": ["camadas"],
        "texto": "Resumo do conteúdo.",
    })
    grafo_json = json.dumps({
        "entidades": [{"nome": "TCP", "tipo": "Protocolo", "descricao": "d"}],
        "relacoes": [],
        "temas": [{"titulo": "Protocolos", "entidades": ["TCP"]}],
    })

    def _side_effect(prompt):
        if _is_flashcard_prompt(prompt):
            return llm_response("não sei gerar flashcards nesse formato.")
        if _is_grafo_prompt(prompt):
            return llm_response(grafo_json)
        return llm_response(resumo_json)

    mock_llm.complete.side_effect = _side_effect

    nodes = make_nodes(10)
    materiais = materials.generate_materials(nodes, fallback_titulo="Fallback", subject_id=None)

    # baralho omitido: 2 materiais em vez de 3, resumo e mapa_mental intactos
    assert len(materiais) == 2
    assert {m["tipo"] for m in materiais} == {"resumo", "mapa_mental"}

    resumo = next(m for m in materiais if m["tipo"] == "resumo")
    assert resumo["titulo"] == "Modelo TCP/IP"

    mapa = next(m for m in materiais if m["tipo"] == "mapa_mental")
    assert mapa["conteudo"]["nodes"]


def test_generate_materials_flashcards_falha_com_excecao_nao_derruba_resumo_mapa(mock_llm):
    """Mesmo se a fase de flashcards levantar uma exceção de verdade (não só
    ficar abaixo do mínimo), o pipeline captura, loga e segue com resumo e
    mapa mental prontos, sem propagar."""
    resumo_json = json.dumps({
        "titulo": "Modelo TCP/IP",
        "topicos_chave": ["camadas"],
        "texto": "Resumo do conteúdo.",
    })
    grafo_json = json.dumps({
        "entidades": [{"nome": "TCP", "tipo": "Protocolo", "descricao": "d"}],
        "relacoes": [],
        "temas": [{"titulo": "Protocolos", "entidades": ["TCP"]}],
    })

    def _side_effect(prompt):
        if _is_flashcard_prompt(prompt):
            raise RuntimeError("Ollama indisponível")
        if _is_grafo_prompt(prompt):
            return llm_response(grafo_json)
        return llm_response(resumo_json)

    mock_llm.complete.side_effect = _side_effect

    nodes = make_nodes(10)
    materiais = materials.generate_materials(nodes, fallback_titulo="Fallback", subject_id=None)

    assert {m["tipo"] for m in materiais} == {"resumo", "mapa_mental"}


def test_generate_materials_fallback_consolidacao_apos_json_invalido(mock_llm):
    """Doc grande: se só a CONSOLIDAÇÃO falhar o JSON (os lotes já rodaram e
    já extraíram entidades com sucesso), o resumo ainda sai em texto puro e o
    mapa cai no agrupamento por tipo. Aqui não tem gap, porque as entidades
    não dependem da consolidação, só os temas dependem."""
    n_nodes = 60
    lote_json = json.dumps({
        "resumo_parcial": "parcial do lote",
        "entidades": [
            {"nome": "Entidade A", "tipo": "Conceito", "descricao": "d"},
            {"nome": "Entidade B", "tipo": "Evento", "descricao": "d"},
        ],
        "relacoes": [],
    })

    def _side_effect(prompt):
        if _is_flashcard_prompt(prompt):
            return llm_response(flashcards_block(5))
        if _has_chunk_marker(prompt):
            return llm_response(lote_json)
        # consolidação: nunca acerta o JSON
        return llm_response("não consigo consolidar isso em JSON agora.")

    mock_llm.complete.side_effect = _side_effect

    nodes = make_nodes(n_nodes)
    materiais = materials.generate_materials(nodes, fallback_titulo="Titulo Fallback", subject_id=None)

    resumo = next(m for m in materiais if m["tipo"] == "resumo")
    assert resumo["titulo"] == "Titulo Fallback"
    assert resumo["conteudo"]["texto"]  # não vazio (vira o texto puro dos parciais)

    mapa = next(m for m in materiais if m["tipo"] == "mapa_mental")
    categorias = {n["data"]["label"] for n in mapa["conteudo"]["nodes"] if n["type"] == "categoria"}
    # sem temas (a consolidação falhou), o mapa cai no agrupamento por tipo
    assert categorias == {"Conceito", "Evento"}


def test_generate_materials_defaults_do_contrato():
    assinatura = inspect.signature(materials.generate_materials)
    assert assinatura.parameters["fallback_titulo"].default == "Documento"
    assert assinatura.parameters["subject_id"].default is None
    assert assinatura.parameters["tipos"].default is None


# ---------------------------------------------------------------------------
# generate_materials(tipos=...): geração parcial (subconjunto de materiais)
# ---------------------------------------------------------------------------

def test_generate_materials_tipos_none_gera_os_tres(mock_llm):
    """tipos=None (default) continua gerando os três materiais, sem
    diferença de comportamento em relação a antes do parâmetro existir."""
    resumo_json = json.dumps({"titulo": "T", "topicos_chave": [], "texto": "resumo"})
    grafo_json = json.dumps({
        "entidades": [{"nome": "TCP", "tipo": "Protocolo", "descricao": "d"}],
        "relacoes": [],
        "temas": [{"titulo": "Tema", "entidades": ["TCP"]}],
    })

    def _side_effect(prompt):
        if _is_flashcard_prompt(prompt):
            return llm_response(flashcards_block(5))
        if _is_grafo_prompt(prompt):
            return llm_response(grafo_json)
        return llm_response(resumo_json)

    mock_llm.complete.side_effect = _side_effect

    materiais = materials.generate_materials(make_nodes(10), tipos=None)

    assert {m["tipo"] for m in materiais} == {"resumo", "mapa_mental", "baralho"}


def test_generate_materials_tipos_so_resumo_doc_pequeno(mock_llm):
    """tipos={"resumo"}: só a chamada de resumo roda (nem grafo, nem
    flashcards), e on_phase_done só dispara pra "resumo"."""
    resumo_json = json.dumps({"titulo": "T", "topicos_chave": ["a"], "texto": "resumo"})
    mock_llm.complete.return_value = llm_response(resumo_json)

    fases_disparadas = []
    materiais = materials.generate_materials(
        make_nodes(10), tipos={"resumo"}, on_phase_done=fases_disparadas.append
    )

    assert len(materiais) == 1
    assert materiais[0]["tipo"] == "resumo"
    assert fases_disparadas == ["resumo"]
    # nenhuma chamada de grafo (pediria "entidades") nem de flashcards
    prompts = [c.args[0] if c.args else c.kwargs["prompt"] for c in mock_llm.complete.call_args_list]
    assert all(not _is_grafo_prompt(p) and not _is_flashcard_prompt(p) for p in prompts)
    assert len(prompts) == 1


def test_generate_materials_tipos_so_flashcards_nao_roda_analise(mock_llm):
    """tipos={"flashcards"}: não roda a análise do documento (nem mega-
    chamada nem map-reduce), só as chamadas de flashcard. on_phase_done só
    dispara "flashcards"."""
    mock_llm.complete.return_value = llm_response(flashcards_block(5))

    fases_disparadas = []
    materiais = materials.generate_materials(
        make_nodes(10), tipos={"flashcards"}, on_phase_done=fases_disparadas.append
    )

    assert len(materiais) == 1
    assert materiais[0]["tipo"] == "baralho"
    assert fases_disparadas == ["flashcards"]
    prompts = [c.args[0] if c.args else c.kwargs["prompt"] for c in mock_llm.complete.call_args_list]
    # todas as chamadas foram de flashcard, nenhuma leu o documento pra análise
    assert all(_is_flashcard_prompt(p) for p in prompts)


def test_generate_materials_tipos_so_flashcards_doc_grande_nao_roda_lotes(mock_llm):
    """Mesmo caso, mas no caminho de documento grande: os lotes map-reduce
    (que só servem resumo/mapa_mental) também não devem rodar."""
    mock_llm.complete.return_value = llm_response(flashcards_block(5))

    n_nodes = 60
    materiais = materials.generate_materials(make_nodes(n_nodes), tipos={"flashcards"})

    assert {m["tipo"] for m in materiais} == {"baralho"}
    prompts = [c.args[0] if c.args else c.kwargs["prompt"] for c in mock_llm.complete.call_args_list]
    # sem lotes de análise: nenhum prompt carrega o marcador de chunk bruto
    # fora do formato de flashcard (todas as chamadas são de flashcard aqui)
    assert all(_is_flashcard_prompt(p) for p in prompts)


def test_generate_materials_tipos_so_mapa_mental(mock_llm):
    """tipos={"mapa_mental"}: só a chamada de grafo roda, resumo e
    flashcards ficam de fora do retorno e das notificações."""
    grafo_json = json.dumps({
        "entidades": [{"nome": "TCP", "tipo": "Protocolo", "descricao": "d"}],
        "relacoes": [],
        "temas": [{"titulo": "Tema", "entidades": ["TCP"]}],
    })
    mock_llm.complete.return_value = llm_response(grafo_json)

    fases_disparadas = []
    materiais = materials.generate_materials(
        make_nodes(10), tipos={"mapa_mental"}, on_phase_done=fases_disparadas.append
    )

    assert len(materiais) == 1
    assert materiais[0]["tipo"] == "mapa_mental"
    assert fases_disparadas == ["mapa_mental"]
