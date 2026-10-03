# -*- coding: utf-8 -*-
"""Card de pauta so de texto aposentado em 02/10/2026.

Em 02/10 sairam dois cards seguidos no Instagram: a rodada de quinta atrasou,
rodou depois da meia-noite UTC e o robo achou que era sexta. Estes testes
garantem que o card nao volta por caminho nenhum.
"""
from datetime import datetime, timezone

import pytest

import run_feed


class _Sexta(datetime):
    @classmethod
    def now(cls, tz=None):
        return datetime(2026, 10, 2, 0, 58, tzinfo=timezone.utc)  # sexta UTC


def test_sexta_publica_peca_e_nao_card(monkeypatch):
    monkeypatch.setattr(run_feed, "datetime", _Sexta)
    monkeypatch.setattr(run_feed, "vitrines_na_semana", lambda: 99)
    monkeypatch.setattr(run_feed, "montar_peca", lambda origem=None: {"tipo": "peca"})
    assert run_feed.escolher_post("")["tipo"] == "peca"


def test_sem_peca_nao_cai_em_card(monkeypatch):
    monkeypatch.setattr(run_feed, "vitrines_na_semana", lambda: 99)

    def falha(origem=None):
        raise RuntimeError("catalogo fora do ar")

    monkeypatch.setattr(run_feed, "montar_peca", falha)
    with pytest.raises(SystemExit) as e:
        run_feed.escolher_post("")
    assert "NAO sai" in str(e.value)


def test_forcar_institucional_recusado():
    with pytest.raises(SystemExit):
        run_feed.escolher_post("institucional")


def test_funcao_do_card_nao_existe_mais():
    assert not hasattr(run_feed, "montar_institucional")
    assert not hasattr(run_feed, "_material_ou_pauta")
