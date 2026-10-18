# -*- coding: utf-8 -*-
"""Checklist do balcao de live (18/10/2026): no feed sai UMA vez so; no story
volta de tempos em tempos (config.STORY_FIXAS)."""
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from src import config, estado, pecas, story

FEED = "balcao-de-live-checklist"
STORY = "balcao-de-live-checklist-story"


@pytest.fixture(autouse=True)
def _estado_limpo(monkeypatch):
    monkeypatch.setattr(config, "ESTADO_DIR", Path(tempfile.mkdtemp()))


def _p(pid, formato="story", categoria="geral"):
    return {"id": pid, "origem": "material", "formato": formato, "categoria": categoria,
            "titulo": pid, "criador": None}


def _h(peca, dias, formato="story"):
    q = (datetime.now(timezone.utc) - timedelta(days=dias)).isoformat(timespec="seconds")
    return {"formato": formato, "peca": peca, "quando": q}


# ------------------------------------------------------------------ feed uma vez
def test_checklist_do_feed_esta_marcado_so_uma_vez():
    assert pecas.so_uma_vez("feed", FEED)
    assert not pecas.so_uma_vez("story", STORY)
    assert not pecas.so_uma_vez("feed", "qualquer-outra")


def test_feed_inedito_entra_e_publicado_nunca_mais_volta(monkeypatch):
    assert not pecas.ja_saiu_uma_vez("feed", FEED, hist=[])
    monkeypatch.setattr(estado, "registrar", lambda *a, **k: None)
    pecas.marcar(_p(FEED, "feed"), "mid", "instagram")
    assert f"feed:{FEED}" in estado.ler_lista(pecas.UMA_VEZ)
    assert pecas.ja_saiu_uma_vez("feed", FEED, hist=[])


def test_feed_publicado_antes_da_regra_vale_pelo_historico():
    assert pecas.ja_saiu_uma_vez("feed", FEED, hist=[_h(FEED, 1, "feed")], gravadas=[])
    # o story com o mesmo nome nao conta para o feed
    assert not pecas.ja_saiu_uma_vez("feed", FEED, hist=[_h(FEED, 1, "story")], gravadas=[])


def test_candidatas_tira_o_feed_ja_publicado(monkeypatch):
    cat = {"itens": []}
    monkeypatch.setattr(pecas.material, "carregar_catalogo", lambda: cat)
    monkeypatch.setattr(pecas.material, "pecas", lambda c, f: [_p(FEED, "feed"), _p("outra", "feed")])
    monkeypatch.setattr(pecas.triagem, "filtrar", lambda l: l)
    monkeypatch.setattr(pecas.criadores, "ativa", lambda: False)
    assert [p["id"] for p in pecas.candidatas("feed")["casa"]] == [FEED, "outra"]
    estado.gravar_lista(pecas.UMA_VEZ, [f"feed:{FEED}"])
    assert [p["id"] for p in pecas.candidatas("feed")["casa"]] == ["outra"]


# ------------------------------------------------------------------ story fixa
def test_story_fixa_inedita_sai_primeiro():
    lista = [_p("a"), _p(STORY), _p("b")]
    assert story.fixa_da_vez(lista, hist=[])["id"] == STORY


def test_story_fixa_espera_o_intervalo():
    dias = config.STORY_FIXAS[STORY]
    lista = [_p("a"), _p(STORY)]
    assert story.fixa_da_vez(lista, hist=[_h(STORY, dias - 1)]) is None
    assert story.fixa_da_vez(lista, hist=[_h(STORY, dias + 0.1)])["id"] == STORY


def test_story_fixa_fora_da_lista_nao_aparece():
    assert story.fixa_da_vez([_p("a"), _p("b")], hist=[]) is None


def test_escolher_arte_usa_a_fixa_vencida(monkeypatch):
    lista = [_p("a"), _p(STORY), _p("b")]
    monkeypatch.setattr(story.pecas, "candidatas", lambda f: {"casa": list(lista), "criador": []})
    assert story.escolher_arte(hist=[])["id"] == STORY
    assert story.escolher_arte(hist=[_h(STORY, 1)])["id"] != STORY
