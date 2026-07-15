"""
Testes unitários puros de rag_api/dedup.py (sem rede/Ollama, sem banco).

dedup.py não importa search_query nem llama_index, é lógica pura recebendo
embed_fn/persist_fn injetados. embed_fn é sempre em BATCH: callable(textos:
list[str]) -> list[list[float]], uma única chamada pra todo o lote (nunca um
loop de chamadas individuais). Os testes mockam esse embed_fn com vetores
fabricados à mão (cosseno controlado), no mesmo espírito do mock_llm de
test_materials.py.
"""

import json
import sys
from pathlib import Path

import pytest

RAG_API_DIR = Path(__file__).resolve().parent.parent / "rag_api"
if str(RAG_API_DIR) not in sys.path:
    sys.path.append(str(RAG_API_DIR))

import dedup  # noqa: E402


def card(pergunta, resposta="resposta padrão"):
    return {"pergunta": pergunta, "resposta": resposta}


# ---------------------------------------------------------------------------
# normalizar_pergunta
# ---------------------------------------------------------------------------

def test_normalizar_pergunta_minusculas_acentos_pontuacao_espacos():
    texto = "  Qual É a  CAPITAL do Brasil?!  "
    assert dedup.normalizar_pergunta(texto) == "qual e a capital do brasil"


def test_normalizar_pergunta_remove_acentos_via_unicodedata():
    assert dedup.normalizar_pergunta("Função e Coração") == "funcao e coracao"


def test_normalizar_pergunta_colapsa_espacos_multiplos():
    assert dedup.normalizar_pergunta("a    b\t\tc") == "a b c"


# ---------------------------------------------------------------------------
# filtrar_lote_lexical
# ---------------------------------------------------------------------------

def test_filtrar_lote_lexical_descarta_pares_parecidos():
    cards = [
        card("Qual é a capital do Brasil?"),
        card("Qual é a capital do Brasil"),  # só difere na pontuação
    ]
    resultado = dedup.filtrar_lote_lexical(cards)
    assert len(resultado) == 1
    assert resultado[0]["pergunta"] == "Qual é a capital do Brasil?"


def test_filtrar_lote_lexical_mantem_perguntas_diferentes():
    cards = [
        card("Qual é a capital do Brasil?"),
        card("Quem descobriu o Brasil?"),
    ]
    resultado = dedup.filtrar_lote_lexical(cards)
    assert len(resultado) == 2


def test_filtrar_lote_lexical_respeita_threshold_customizado():
    cards = [card("abc def"), card("abc xyz")]
    # ratio real desse par fica abaixo de 0.95, então com threshold alto
    # (quase exato) os dois sobrevivem
    resultado = dedup.filtrar_lote_lexical(cards, threshold=0.99)
    assert len(resultado) == 2


# ---------------------------------------------------------------------------
# cosine_similarity
# ---------------------------------------------------------------------------

def test_cosine_similarity_vetores_identicos_e_um():
    assert dedup.cosine_similarity([1, 0, 0], [1, 0, 0]) == pytest.approx(1.0)


def test_cosine_similarity_vetores_ortogonais_e_zero():
    assert dedup.cosine_similarity([1, 0], [0, 1]) == pytest.approx(0.0)


def test_cosine_similarity_vetor_nulo_nao_quebra():
    assert dedup.cosine_similarity([0, 0], [1, 1]) == 0.0


# ---------------------------------------------------------------------------
# filtrar_lote_semantico
# ---------------------------------------------------------------------------

def _embed_fn_fabricado(mapa: dict):
    """embed_fn de teste em BATCH: devolve, na mesma ordem dos textos
    recebidos, o vetor mapeado pelo texto "pergunta\\nresposta" exato, ou um
    vetor único (baseado no hash) se não estiver no mapa, pra nunca colidir
    por acidente. Também guarda o(s) batch(es) recebido(s) em `chamadas`,
    pra validar nos testes que embed_fn é chamado UMA VEZ só."""
    chamadas = []

    def _fn(textos):
        chamadas.append(list(textos))
        return [mapa[t] if t in mapa else [hash(t) % 97, 1.0] for t in textos]

    _fn.chamadas = chamadas
    return _fn


def test_filtrar_lote_semantico_acima_do_threshold_descarta():
    c1 = card("Pergunta A", "Resposta A")
    c2 = card("Pergunta B totalmente diferente na escrita", "Resposta A")
    texto1 = f"{c1['pergunta']}\n{c1['resposta']}"
    texto2 = f"{c2['pergunta']}\n{c2['resposta']}"
    embed_fn = _embed_fn_fabricado({
        texto1: [1.0, 0.0],
        texto2: [0.99, 0.01],  # quase colinear: cosseno alto
    })

    resultado = dedup.filtrar_lote_semantico([c1, c2], [], embed_fn, threshold=0.88)

    assert len(resultado) == 1
    assert resultado[0]["pergunta"] == "Pergunta A"
    assert resultado[0]["embedding"] == [1.0, 0.0]
    # embed_fn chamado uma única vez, em batch, com os dois textos
    assert len(embed_fn.chamadas) == 1
    assert embed_fn.chamadas[0] == [texto1, texto2]


def test_filtrar_lote_semantico_abaixo_do_threshold_mantem_ambos():
    c1 = card("Pergunta A", "Resposta A")
    c2 = card("Pergunta B", "Resposta B")
    texto1 = f"{c1['pergunta']}\n{c1['resposta']}"
    texto2 = f"{c2['pergunta']}\n{c2['resposta']}"
    embed_fn = _embed_fn_fabricado({
        texto1: [1.0, 0.0],
        texto2: [0.0, 1.0],  # ortogonais: cosseno 0
    })

    resultado = dedup.filtrar_lote_semantico([c1, c2], [], embed_fn, threshold=0.88)

    assert len(resultado) == 2
    assert all("embedding" in c for c in resultado)
    assert len(embed_fn.chamadas) == 1


def test_filtrar_lote_semantico_compara_contra_pool_existente():
    novo = card("Pergunta Nova", "Resposta Nova")
    texto_novo = f"{novo['pergunta']}\n{novo['resposta']}"
    embed_fn = _embed_fn_fabricado({texto_novo: [1.0, 0.0]})

    # embedding já existente na matéria é quase idêntico ao do card novo
    resultado = dedup.filtrar_lote_semantico([novo], [[0.999, 0.001]], embed_fn, threshold=0.88)

    assert resultado == []


def test_filtrar_lote_semantico_acumula_aceitos_no_pool():
    # terceiro card é quase idêntico ao segundo (já aceito no lote), não ao
    # primeiro: só compara contra o pool acumulado prova a acumulação
    c1 = card("Alfa", "R1")
    c2 = card("Beta", "R2")
    c3 = card("Beta quase igual", "R2")
    t1, t2, t3 = (f"{c['pergunta']}\n{c['resposta']}" for c in (c1, c2, c3))
    embed_fn = _embed_fn_fabricado({
        t1: [1.0, 0.0],
        t2: [0.0, 1.0],
        t3: [0.01, 0.9999],
    })

    resultado = dedup.filtrar_lote_semantico([c1, c2, c3], [], embed_fn, threshold=0.9)

    assert [c["pergunta"] for c in resultado] == ["Alfa", "Beta"]
    # continua uma chamada só, mesmo com 3 cards
    assert len(embed_fn.chamadas) == 1


def test_filtrar_lote_semantico_lista_vazia_nao_chama_embed_fn():
    embed_fn = _embed_fn_fabricado({})
    resultado = dedup.filtrar_lote_semantico([], [], embed_fn, threshold=0.9)
    assert resultado == []
    assert embed_fn.chamadas == []


def test_filtrar_lote_semantico_ignora_none_no_pool_de_existentes():
    """Bug 9: card antigo sem embedding calculado (None no pool de
    existentes) não pode quebrar cosine_similarity. É ignorado na
    comparação, sem levantar exceção."""
    c1 = card("Pergunta A", "Resposta A")
    texto1 = f"{c1['pergunta']}\n{c1['resposta']}"
    embed_fn = _embed_fn_fabricado({texto1: [1.0, 0.0]})

    resultado = dedup.filtrar_lote_semantico(
        [c1], [None, [0.0, 1.0]], embed_fn, threshold=0.88
    )

    assert len(resultado) == 1
    assert resultado[0]["embedding"] == [1.0, 0.0]


def test_filtrar_lote_semantico_ignora_none_no_proprio_lote():
    """embed_fn devolvendo None pra um card do lote (caso extremo) também não
    pode quebrar: o card é aceito sem comparação em vez de derrubar o dedup
    inteiro."""
    c1 = card("Pergunta sem embedding", "Resposta A")
    c2 = card("Pergunta com embedding", "Resposta B")
    texto1 = f"{c1['pergunta']}\n{c1['resposta']}"
    texto2 = f"{c2['pergunta']}\n{c2['resposta']}"

    def embed_fn(textos):
        return [None if t == texto1 else [1.0, 0.0] for t in textos]

    resultado = dedup.filtrar_lote_semantico([c1, c2], [], embed_fn, threshold=0.88)

    assert len(resultado) == 2
    assert resultado[0]["embedding"] is None
    assert resultado[1]["embedding"] == [1.0, 0.0]


# ---------------------------------------------------------------------------
# garantir_embeddings_existentes (migração preguiçosa)
# ---------------------------------------------------------------------------

class _FlashcardFake:
    def __init__(self, id, pergunta, resposta, embedding=None):
        self.id = id
        self.pergunta = pergunta
        self.resposta = resposta
        self.embedding = embedding


def test_garantir_embeddings_existentes_backfill_de_none():
    fc_sem_embedding = _FlashcardFake(1, "P1", "R1", embedding=None)
    fc_com_embedding = _FlashcardFake(2, "P2", "R2", embedding=[9.0, 9.0])

    persistidos = []

    def persist_fn(flashcard_id, embedding):
        persistidos.append((flashcard_id, embedding))

    embed_fn = _embed_fn_fabricado({"P1\nR1": [1.0, 2.0]})

    embeddings = dedup.garantir_embeddings_existentes(
        [fc_sem_embedding, fc_com_embedding], embed_fn, persist_fn
    )

    # card sem embedding foi calculado E persistido
    assert embeddings[0] == [1.0, 2.0]
    assert persistidos == [(1, [1.0, 2.0])]

    # card que já tinha embedding não foi recalculado nem persistido de novo
    assert embeddings[1] == [9.0, 9.0]

    # embed_fn chamado uma única vez, só com o texto do card pendente
    assert embed_fn.chamadas == [["P1\nR1"]]


def test_garantir_embeddings_existentes_aceita_dict_tambem():
    fc_dict = {"id": 3, "pergunta": "P3", "resposta": "R3", "embedding": None}
    persistidos = []

    embed_fn = _embed_fn_fabricado({"P3\nR3": [5.0]})

    embeddings = dedup.garantir_embeddings_existentes(
        [fc_dict], embed_fn, lambda fid, emb: persistidos.append((fid, emb))
    )

    assert embeddings == [[5.0]]
    assert persistidos == [(3, [5.0])]


def test_garantir_embeddings_existentes_todos_ja_tem_embedding_nao_chama_embed_fn():
    fc1 = _FlashcardFake(1, "P1", "R1", embedding=[1.0])
    fc2 = _FlashcardFake(2, "P2", "R2", embedding=[2.0])

    embed_fn = _embed_fn_fabricado({})

    embeddings = dedup.garantir_embeddings_existentes(
        [fc1, fc2], embed_fn, lambda fid, emb: None
    )

    assert embeddings == [[1.0], [2.0]]
    assert embed_fn.chamadas == []


def test_garantir_embeddings_existentes_batch_unico_para_varios_pendentes():
    fc1 = _FlashcardFake(1, "P1", "R1", embedding=None)
    fc2 = _FlashcardFake(2, "P2", "R2", embedding=[9.0])
    fc3 = _FlashcardFake(3, "P3", "R3", embedding=None)

    embed_fn = _embed_fn_fabricado({"P1\nR1": [1.0], "P3\nR3": [3.0]})
    persistidos = []

    embeddings = dedup.garantir_embeddings_existentes(
        [fc1, fc2, fc3], embed_fn, lambda fid, emb: persistidos.append((fid, emb))
    )

    # ordem preservada, mesmo com fc2 (já tinha embedding) no meio
    assert embeddings == [[1.0], [9.0], [3.0]]
    assert persistidos == [(1, [1.0]), (3, [3.0])]
    # uma única chamada, só com os dois textos pendentes (fc2 fora do batch)
    assert embed_fn.chamadas == [["P1\nR1", "P3\nR3"]]


# ---------------------------------------------------------------------------
# deve_criar_baralho (regra de corte dos 5 mínimos)
# ---------------------------------------------------------------------------

def test_deve_criar_baralho_falso_com_menos_de_5():
    cards = [card(f"P{i}") for i in range(4)]
    assert dedup.deve_criar_baralho(cards) is False


def test_deve_criar_baralho_verdadeiro_com_5_ou_mais():
    cards = [card(f"P{i}") for i in range(5)]
    assert dedup.deve_criar_baralho(cards) is True


def test_deve_criar_baralho_respeita_minimo_customizado():
    cards = [card(f"P{i}") for i in range(3)]
    assert dedup.deve_criar_baralho(cards, minimo=3) is True
    assert dedup.deve_criar_baralho(cards, minimo=4) is False


# ---------------------------------------------------------------------------
# deduplicar_flashcards (funil completo)
# ---------------------------------------------------------------------------

def test_deduplicar_flashcards_funil_completo_lexical_e_semantico():
    # c2 é lexicalmente quase igual a c1 (estágio 1 descarta)
    # c3 é semanticamente igual a um card já existente na matéria (estágio 2 descarta)
    c1 = card("Qual é a capital do Brasil?", "Brasília")
    c2 = card("Qual é a capital do Brasil", "Brasília")
    c3 = card("Pergunta única", "Resposta única")

    existente = _FlashcardFake(10, "Pergunta antiga", "Resposta antiga", embedding=[1.0, 0.0])

    t1 = f"{c1['pergunta']}\n{c1['resposta']}"
    t3 = f"{c3['pergunta']}\n{c3['resposta']}"

    def embed_fn(textos):
        def _embed(texto):
            if texto == t1:
                return [1.0, 0.0]  # quase igual ao existente
            if texto == t3:
                return [0.0, 1.0]  # bem diferente do existente
            return [0.5, 0.5]
        return [_embed(t) for t in textos]

    persistidos = []
    resultado = dedup.deduplicar_flashcards(
        [c1, c2, c3],
        [existente],
        embed_fn=embed_fn,
        persist_embedding_fn=lambda fid, emb: persistidos.append((fid, emb)),
        semantic_threshold=0.88,
    )

    # c2 caiu no lexical, c1 caiu no semântico (igual ao existente), sobra só c3
    assert [c["pergunta"] for c in resultado] == ["Pergunta única"]
    # existente já tinha embedding: não precisou de backfill
    assert persistidos == []


def test_deduplicar_flashcards_faz_backfill_de_existente_sem_embedding():
    novo = card("Pergunta Nova", "Resposta Nova")
    existente_sem_embedding = _FlashcardFake(20, "Antiga", "R", embedding=None)

    persistidos = []

    def embed_fn(textos):
        def _embed(texto):
            if texto.startswith("Antiga"):
                return [0.0, 1.0]
            return [1.0, 0.0]  # ortogonal ao existente: não é duplicata
        return [_embed(t) for t in textos]

    resultado = dedup.deduplicar_flashcards(
        [novo],
        [existente_sem_embedding],
        embed_fn=embed_fn,
        persist_embedding_fn=lambda fid, emb: persistidos.append((fid, emb)),
    )

    assert len(resultado) == 1
    assert persistidos == [(20, [0.0, 1.0])]


# ---------------------------------------------------------------------------
# filtrar_materiais_duplicados (dedup lexical de resumo/mapa mental)
# ---------------------------------------------------------------------------

class _MaterialFake:
    """Simula Resumo/MapaMental do banco: conteudo vem como STRING JSON
    (save_materials_db grava com json.dumps), não dict."""

    def __init__(self, titulo, conteudo_dict):
        self.titulo = titulo
        self.conteudo = json.dumps(conteudo_dict, ensure_ascii=False)


def resumo(titulo, texto, topicos=None):
    return {
        "tipo": "resumo",
        "titulo": titulo,
        "conteudo": {"texto": texto, "topicos_chave": topicos or []},
    }


def mapa_mental(titulo, labels):
    nodes = [{"data": {"label": label}} for label in labels]
    return {"tipo": "mapa_mental", "titulo": titulo, "conteudo": {"nodes": nodes, "edges": []}}


def test_filtrar_materiais_duplicados_resumo_exato_e_descartado():
    novo = resumo("Aula 1", "Texto idêntico ao já existente na matéria.")
    existente = _MaterialFake("Aula 1", {"texto": "Texto idêntico ao já existente na matéria.", "topicos_chave": []})

    resultado = dedup.filtrar_materiais_duplicados([novo], [existente], tipo="resumo")

    assert resultado == []


def test_filtrar_materiais_duplicados_resumo_quase_igual_acima_do_threshold_e_descartado():
    novo = resumo("Aula 1 - Introdução", "Texto quase igual ao existente, só um detalhe diferente aqui.")
    existente = _MaterialFake(
        "Aula 1 - Introducao",
        {"texto": "Texto quase igual ao existente, só um detalhe diferente ali.", "topicos_chave": []},
    )

    resultado = dedup.filtrar_materiais_duplicados([novo], [existente], tipo="resumo")

    assert resultado == []


def test_filtrar_materiais_duplicados_resumo_distinto_abaixo_do_threshold_sobrevive():
    novo = resumo("Genética", "Herança mendeliana e cruzamentos di-híbridos.")
    existente = _MaterialFake(
        "Revolução Francesa",
        {"texto": "Queda da Bastilha e o fim do Antigo Regime na França.", "topicos_chave": []},
    )

    resultado = dedup.filtrar_materiais_duplicados([novo], [existente], tipo="resumo")

    assert resultado == [novo]


def test_filtrar_materiais_duplicados_resumo_sem_existentes_sobrevive():
    novo = resumo("Aula 1", "Conteúdo qualquer.")
    assert dedup.filtrar_materiais_duplicados([novo], [], tipo="resumo") == [novo]


def test_filtrar_materiais_duplicados_mapa_mental_mesmos_labels_e_descartado():
    """Compara ESTRUTURALMENTE: mesmos labels de nó, ordem diferente no JSON
    (ids/posições podem mudar entre gerações do LLM) ainda é duplicado."""
    novo = mapa_mental("Aula 1 — Mapa Mental de Estudo", ["Napoleão", "Waterloo", "França"])
    existente = _MaterialFake(
        "Aula 1 — Mapa Mental de Estudo",
        {"nodes": [{"data": {"label": l}} for l in ["França", "Napoleão", "Waterloo"]], "edges": []},
    )

    resultado = dedup.filtrar_materiais_duplicados([novo], [existente], tipo="mapa_mental")

    assert resultado == []


def test_filtrar_materiais_duplicados_mapa_mental_labels_diferentes_sobrevive():
    novo = mapa_mental("Genética — Mapa Mental de Estudo", ["Mendel", "Ervilhas", "Alelos"])
    existente = _MaterialFake(
        "Revolução Francesa — Mapa Mental de Estudo",
        {"nodes": [{"data": {"label": l}} for l in ["Bastilha", "Robespierre", "Girondinos"]], "edges": []},
    )

    resultado = dedup.filtrar_materiais_duplicados([novo], [existente], tipo="mapa_mental")

    assert resultado == [novo]


def test_filtrar_materiais_duplicados_acumula_aceitos_no_pool_do_lote():
    """Dois materiais novos quase idênticos entre si (mesmo lote): o segundo
    é descartado por comparação contra o primeiro, já aceito."""
    r1 = resumo("Aula 1", "Conteúdo do documento sobre fotossíntese e clorofila.")
    r2 = resumo("Aula 1", "Conteúdo do documento sobre fotossíntese e clorofila.")

    resultado = dedup.filtrar_materiais_duplicados([r1, r2], [], tipo="resumo")

    assert resultado == [r1]
