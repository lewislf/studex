from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import routes.chat_routes  # noqa: F401  (coloca rag_api no sys.path)
import chat


def _trecho(texto, arquivo="grafos.pdf", score=0.8):
    node = SimpleNamespace(get_content=lambda: texto, metadata={"file_name": arquivo})
    return SimpleNamespace(node=node, score=score)


HISTORICO = [
    {"papel": "user", "msg": "Quais os tipos de coloração?"},
    {"papel": "assistant", "msg": "1) vértices, 2) arestas [1]"},
]


def test_prompt_sem_historico_nao_tem_bloco():
    prompt = chat.montar_prompt("O que é k-coloração?", [_trecho("texto A")])
    assert "[1] (arquivo: grafos.pdf)\ntexto A" in prompt
    assert "Usuário:" not in prompt and "Assistente:" not in prompt
    assert prompt.endswith("Pergunta: O que é k-coloração?")


def test_prompt_com_historico_em_ordem_e_antes_dos_trechos():
    prompt = chat.montar_prompt("E o segundo?", [_trecho("texto A")], HISTORICO)

    # rindex: as regras do SYS_PROMPT também citam as tags
    inicio, fim = prompt.rindex("<historico>"), prompt.rindex("</historico>")
    bloco = prompt[inicio:fim]
    # ordem cronológica: a pergunta antiga vem antes da resposta
    assert bloco.index("Usuário: Quais os tipos de coloração?") < bloco.index("Assistente: 1) vértices, 2) arestas [1]")
    assert fim < prompt.rindex("<trechos>")


def test_prompt_corta_mensagens_longas_do_historico():
    longa = "a" * 2000
    prompt = chat.montar_prompt("e aí?", [_trecho("t")], [{"papel": "user", "msg": longa}])
    assert "a" * 440 in prompt
    assert "a" * 441 not in prompt


def test_responder_busca_com_a_pergunta_anterior_e_manda_historico_ao_prompt():
    llm = MagicMock()
    llm.complete.return_value = SimpleNamespace(text="Coloração de arestas [1].")
    with patch.object(chat, "buscar_trechos", return_value=[_trecho("arestas...")]) as busca, \
         patch.object(chat, "llm", llm):
        out = chat.responder("E o segundo?", 1, 2, HISTORICO)

    # a busca leva o assunto da pergunta anterior
    assert busca.call_args.args[0] == "Quais os tipos de coloração?\nE o segundo?"
    # o prompt recebe o histórico e a pergunta original
    prompt = llm.complete.call_args.args[0]
    assert "Assistente: 1) vértices, 2) arestas [1]" in prompt
    assert prompt.endswith("Pergunta: E o segundo?")
    assert out["answer"] == "Coloração de arestas [1]."


def test_responder_sem_trechos_nao_chama_llm():
    llm = MagicMock()
    with patch.object(chat, "buscar_trechos", return_value=[]), patch.object(chat, "llm", llm):
        out = chat.responder("bolo de cenoura?", 1, 2, HISTORICO)
    assert out == {"answer": chat.SEM_RESPOSTA, "sources": []}
    llm.complete.assert_not_called()
