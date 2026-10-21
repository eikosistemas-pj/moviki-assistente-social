# -*- coding: utf-8 -*-
"""Rotulo 'Informacoes de IA' da Meta (17/10/2026)."""
from src import config
from src.social.instagram import Instagram


def _ig(ia, respostas=None):
    chamadas = []

    def post(caminho, params):
        chamadas.append((caminho, dict(params)))
        if respostas:
            return respostas.pop(0)
        return {"id": "c1"}
    return Instagram(account_id="1", token="t", post_fn=post, get_fn=lambda c, p: {}, ia=ia), chamadas


def test_casa_ganha_rotulo(monkeypatch):
    monkeypatch.setattr(config, "ROTULO_IA", True)
    ig, ch = _ig(True)
    ig._post("1/media", {"video_url": "https://v", "media_type": "STORIES"})
    assert ch[0][1]["is_ai_generated"] == "true"


def test_criador_e_publicacao_sem_rotulo(monkeypatch):
    monkeypatch.setattr(config, "ROTULO_IA", True)
    ig, ch = _ig(False)
    ig._post("1/media", {"video_url": "https://v"})
    assert "is_ai_generated" not in ch[0][1]
    ig, ch = _ig(True)
    ig._post("1/media_publish", {"creation_id": "c1"})
    assert "is_ai_generated" not in ch[0][1]


def test_desliga_pela_variavel(monkeypatch):
    monkeypatch.setattr(config, "ROTULO_IA", False)
    ig, ch = _ig(True)
    ig._post("1/media", {"image_url": "https://i"})
    assert "is_ai_generated" not in ch[0][1]


def test_meta_recusou_rotulo_publica_sem(monkeypatch):
    monkeypatch.setattr(config, "ROTULO_IA", True)
    ig, ch = _ig(True, [{"error": {"message": "Invalid parameter is_ai_generated"}}, {"id": "c2"}])
    r = ig._post("1/media", {"image_url": "https://i"})
    assert r == {"id": "c2"} and "is_ai_generated" not in ch[1][1]
