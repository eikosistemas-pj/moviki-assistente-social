# -*- coding: utf-8 -*-
"""
Corrida da Meta no media_publish e alerta do painel (15/10/2026, marca
2026-10-15-republicar). Incidente de origem: feed de 12/10 18h39 caiu no plano
B com "Media ID is not available" e o aviso ficou vermelho 7 dias com o
Instagram publicando normal.
"""
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

import run_metricas
from src import config
from src.social.instagram import Instagram

CORRIDA = {"error": {"message": "Media ID is not available", "code": 9007,
                     "error_subcode": 2207027}}


class Meta:
    """Graph API falsa: respostas do media_publish em fila e status do
    container depois da espera."""

    def __init__(self, publicar, status_depois="FINISHED", lista=None):
        self.publicar = list(publicar)
        self.status_depois = status_depois
        self.lista = lista or []
        self.chamadas = []
        self.esperas = []
        self._esperou = False

    def post(self, caminho, params):
        self.chamadas.append(caminho)
        if caminho.endswith("/media"):
            return {"id": "container-1"}
        if caminho.endswith("/media_publish"):
            return self.publicar.pop(0)
        return {}

    def get(self, caminho, params):
        self.chamadas.append("GET " + caminho)
        if caminho == "container-1":
            return {"status_code": self.status_depois if self._esperou else "FINISHED"}
        return {"data": self.lista}

    def sleep(self, s):
        self.esperas.append(s)
        self._esperou = True


def _ig(meta):
    return Instagram(account_id="123", token="t", post_fn=meta.post,
                     get_fn=meta.get, sleep_fn=meta.sleep)


def _publicacoes(meta):
    return sum(1 for c in meta.chamadas if c.endswith("/media_publish"))


def test_corrida_da_meta_tenta_mais_uma_vez_e_publica():
    meta = Meta([CORRIDA, {"id": "media-77"}])
    assert _ig(meta).foto("https://img", "legenda") == "media-77"
    assert _publicacoes(meta) == 2


def test_so_uma_nova_tentativa_nunca_em_laco():
    meta = Meta([CORRIDA, CORRIDA, {"id": "nunca"}])
    with pytest.raises(RuntimeError, match="publicar"):
        _ig(meta).foto("https://img", "legenda")
    assert _publicacoes(meta) == 2


def test_container_ja_publicado_nao_publica_de_novo():
    agora = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+0000")
    meta = Meta([CORRIDA], status_depois="PUBLISHED",
                lista=[{"id": "media-que-entrou", "timestamp": agora}])
    assert _ig(meta).foto("https://img", "legenda") == "media-que-entrou"
    assert _publicacoes(meta) == 1
    assert "GET 123/media" in meta.chamadas


def test_story_procura_na_lista_de_stories():
    agora = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+0000")
    meta = Meta([CORRIDA], status_depois="PUBLISHED",
                lista=[{"id": "story-1", "timestamp": agora}])
    assert _ig(meta).story("https://img") == "story-1"
    assert "GET 123/stories" in meta.chamadas


def test_publicado_mas_post_antigo_nao_vale():
    velho = (datetime.now(timezone.utc) - timedelta(hours=3)).strftime("%Y-%m-%dT%H:%M:%S+0000")
    meta = Meta([CORRIDA], status_depois="PUBLISHED",
                lista=[{"id": "post-de-ontem", "timestamp": velho}])
    with pytest.raises(RuntimeError, match="nao apareceu"):
        _ig(meta).foto("https://img", "legenda")
    assert _publicacoes(meta) == 1


def test_container_com_erro_cai_no_plano_b_sem_insistir():
    meta = Meta([CORRIDA], status_depois="ERROR")
    with pytest.raises(RuntimeError, match="Media ID is not available"):
        _ig(meta).foto("https://img", "legenda")
    assert _publicacoes(meta) == 1


def test_recusa_de_verdade_nao_tenta_de_novo():
    recusa = {"error": {"message": "Application request limit reached", "code": 4}}
    meta = Meta([recusa, {"id": "nunca"}])
    with pytest.raises(RuntimeError, match="publicar"):
        _ig(meta).foto("https://img", "legenda")
    assert _publicacoes(meta) == 1
    assert meta.esperas == []


# ------------------------------------------------------------- alerta do painel
def _cfg(monkeypatch):
    monkeypatch.setattr(config, "SO_FACEBOOK", False)
    monkeypatch.setattr(config, "IG_FORMATOS", {"feed", "story", "reel"})
    monkeypatch.setattr(config, "ESTADO_DIR", Path(tempfile.mkdtemp()))


def test_falha_superada_sai_do_vermelho(monkeypatch):
    _cfg(monkeypatch)
    agora = datetime(2026, 10, 15, 23, tzinfo=timezone.utc)

    def q(h):
        return (agora - timedelta(hours=h)).isoformat(timespec="seconds")

    hist = [
        {"quando": q(6), "formato": "story", "descricao": "Story", "media_id": "s1",
         "rede": "instagram"},
        {"quando": q(74), "formato": "feed", "descricao": "Feed", "media_id": "f1",
         "rede": "facebook", "planoB": True, "erroInstagram": "publicar: Media ID is not available"},
    ]
    r = run_metricas.montar(hist, agora)
    pb = [a for a in r["alertas"] if a["tipo"] == "plano_b"]
    assert len(pb) == 1
    assert pb[0]["nivel"] == "atencao"
    assert "voltou a publicar em 15/10 14:00" in pb[0]["texto"]


def test_falha_sem_recuperacao_continua_grave(monkeypatch):
    _cfg(monkeypatch)
    agora = datetime(2026, 10, 15, 23, tzinfo=timezone.utc)

    def q(h):
        return (agora - timedelta(hours=h)).isoformat(timespec="seconds")

    hist = [
        {"quando": q(74), "formato": "story", "descricao": "Story", "media_id": "s1",
         "rede": "instagram"},
        {"quando": q(6), "formato": "feed", "descricao": "Feed", "media_id": "f1",
         "rede": "facebook", "planoB": True, "erroInstagram": "conta restrita"},
    ]
    r = run_metricas.montar(hist, agora)
    pb = [a for a in r["alertas"] if a["tipo"] == "plano_b"]
    assert len(pb) == 1 and pb[0]["nivel"] == "grave"
    assert "voltou" not in pb[0]["texto"]
