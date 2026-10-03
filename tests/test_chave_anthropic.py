# -*- coding: utf-8 -*-
"""03/10/2026 — alarme da chave da Anthropic (run_verificar.py / src/ia.py).

Nenhum teste chama a rede: net.get e trocado por um falso.
"""
import datetime

import pytest

from src import config, ia, util_net

HOJE = datetime.date(2026, 10, 3)


class _Resp:
    def __init__(self, status):
        self.status_code = status


def _api(monkeypatch, status=200, chamadas=None):
    def falso(url, **kw):
        if chamadas is not None:
            chamadas.append((url, kw))
        return _Resp(status)
    monkeypatch.setattr(ia.net, "get", falso)


def _chave(monkeypatch, chave="sk-ant-api03-TESTE", validade=""):
    monkeypatch.setattr(config, "ANTHROPIC_API_KEY", chave)
    monkeypatch.setattr(config, "ANTHROPIC_CHAVE_VALIDADE", validade)
    monkeypatch.setattr(config, "ANTHROPIC_AVISO_DIAS", 21)
    monkeypatch.setattr(config, "ANTHROPIC_MODEL", "claude-haiku-4-5")
    monkeypatch.setattr(config, "ANTHROPIC_MODEL_VISAO", "claude-haiku-4-5")


def test_chave_boa_sem_validade(monkeypatch):
    chamadas = []
    _chave(monkeypatch)
    _api(monkeypatch, 200, chamadas)
    txt = ia.conferir_chave(hoje=HOJE)
    assert "chave aceita" in txt and "sem validade" in txt
    # consulta o modelo, nao gera texto (nao gasta credito)
    assert len(chamadas) == 1
    url, kw = chamadas[0]
    assert url.endswith("/v1/models/claude-haiku-4-5")
    assert kw["headers"]["x-api-key"] == "sk-ant-api03-TESTE"
    # a chave nunca aparece no resumo que vai para o log publico
    assert "sk-ant" not in txt


def test_sem_chave(monkeypatch):
    _chave(monkeypatch, chave="")
    _api(monkeypatch, 200)
    with pytest.raises(RuntimeError, match="ausente"):
        ia.conferir_chave(hoje=HOJE)


def test_chave_recusada(monkeypatch):
    _chave(monkeypatch)
    _api(monkeypatch, 401)
    with pytest.raises(RuntimeError, match="RECUSOU"):
        ia.conferir_chave(hoje=HOJE)


def test_modelo_aposentado(monkeypatch):
    _chave(monkeypatch)
    _api(monkeypatch, 404)
    with pytest.raises(RuntimeError, match="aposentado"):
        ia.conferir_chave(hoje=HOJE)


def test_validade_longe(monkeypatch):
    _chave(monkeypatch, validade="2026-12-31")
    _api(monkeypatch, 200)
    assert "vence em 31/12/2026 (faltam 89 dias)" in ia.conferir_chave(hoje=HOJE)


def test_validade_perto_acende_alarme(monkeypatch):
    _chave(monkeypatch, validade="31/12/2026")
    _api(monkeypatch, 200)
    with pytest.raises(RuntimeError, match="faltam 21 dias"):
        ia.conferir_chave(hoje=datetime.date(2026, 12, 10))


def test_validade_vencida(monkeypatch):
    _chave(monkeypatch, validade="2026-12-31")
    _api(monkeypatch, 200)
    with pytest.raises(RuntimeError, match="venceu"):
        ia.conferir_chave(hoje=datetime.date(2027, 1, 2))


def test_validade_mal_escrita(monkeypatch):
    _chave(monkeypatch, validade="31 dez")
    _api(monkeypatch, 200)
    with pytest.raises(RuntimeError, match="invalida"):
        ia.conferir_chave(hoje=HOJE)


def test_chave_anthropic_mascarada_no_log():
    msg = util_net.sem_segredo("falhou com x-api-key sk-ant-api03-AbC_9-xyz no corpo")
    assert "AbC_9" not in msg and "sk-ant-***" in msg
