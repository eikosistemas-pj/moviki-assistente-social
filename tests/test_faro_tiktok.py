# -*- coding: utf-8 -*-
"""Guias FARO no Kit TikTok e fora dos cortes de story (29/10/2026)."""
from datetime import date

from src import grade, tiktok

VIDEO = "https://app.moviki.com.br/faro/natal-por-encomenda/tiktok-mande-natal.mp4"


def _item(**extra):
    it = {"id": "faro-natal-teste", "formato": "reel", "pilar": "faro", "ramo": "confeitaria",
          "titulo": "Natal por encomenda", "video": "https://app.moviki.com.br/faro/natal-por-encomenda/reel-comente-natal.mp4",
          "legenda": "Guia para vender por encomenda no Natal.", "chamada": "Comente NATAL.", "cartela": False,
          "canais": ["instagram"], "a_partir_de": "2026-10-30", "valido_ate": "2026-12-15",
          "tiktok": {"video": VIDEO, "palavra": "NATAL", "dias": ["2026-11-02"]}}
    it.update(extra)
    return it


def test_campo_tiktok_valido():
    assert grade.validar(_item()) == []


def test_campo_tiktok_ruim():
    assert grade.validar(_item(tiktok={"video": "https://x.com/a.mp4", "palavra": "natal", "dias": []}))


def test_tiktok_do_dia_respeita_dia_e_prazo():
    dados = {"itens": [_item()]}
    assert [i["id"] for i in grade.tiktok_do_dia(date(2026, 11, 2), dados)] == ["faro-natal-teste"]
    assert grade.tiktok_do_dia(date(2026, 11, 3), dados) == []
    vencido = {"itens": [_item(valido_ate="2026-11-01", a_partir_de="2026-10-01")]}
    assert grade.tiktok_do_dia(date(2026, 11, 2), vencido) == []


def test_dia_da_grade_troca_o_video_e_nao_pede_live():
    hoje = date(2026, 11, 1)
    dias = [{"dia": "2026-11-01", "hoje": True, "id": "m1", "video": "a"},
            {"dia": "2026-11-02", "hoje": False, "id": "m2", "video": "b"}]
    it = _item()
    saida = tiktok.com_grade(dias, hoje, lambda d: [it] if d.isoformat() == "2026-11-02" else [])
    assert saida[0]["id"] == "m1"
    d = saida[1]
    assert d["video"] == VIDEO and d["sem_cartela"] is True
    assert d["legenda"].splitlines()[0].startswith("\U0001f4e9 Mande NATAL no direct")
    assert "LIVE" not in d["legenda"]
