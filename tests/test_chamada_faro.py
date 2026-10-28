# -*- coding: utf-8 -*-
"""Chamada propria por video da grade (28/10/2026, Guias FARO).

O video do guia pede "Comente GUIA" (palavra que o ManyChat responde com o
link do guia) e nao pode ganhar a cartela falada "Comenta LIVE" no fim.
"""
from src import compliance, config, grade, pecas
from src.social.instagram import Instagram

CHAMADA = "\U0001f4ac Comente GUIA que eu te mando no direct o link do guia."


def _item(**extra):
    it = {"id": "faro-verao-teste", "formato": "reel", "pilar": "faro", "titulo": "Vender na praia",
          "video": "https://github.com/eikosistemas-pj/moviki-assistente-social/releases/download/acervo/faro-verao-teste.mp4",
          "legenda": "Guia para vender na praia. Link na bio.", "canais": ["instagram", "facebook"],
          "a_partir_de": "2026-11-01", "valido_ate": "2027-02-28"}
    it.update(extra)
    return it


def test_chamada_da_peca_troca_a_padrao():
    leg = Instagram.legenda_final("Guia da praia.", "", CHAMADA)
    assert leg.splitlines()[0] == CHAMADA
    assert "Comente LIVE" not in leg


def test_chamada_vazia_tira_a_chamada():
    assert Instagram.legenda_final("Guia da praia.", "", "") == "Guia da praia."


def test_sem_chamada_da_peca_continua_a_padrao():
    assert Instagram.legenda_final("Texto.", "").splitlines()[0] == config.CHAMADA_COMENTE


def test_chamada_da_peca_nao_repete():
    leg = Instagram.legenda_final(CHAMADA + "\n\nTexto.", "", CHAMADA)
    assert leg.count("Comente GUIA") == 1


def test_desligar_geral_desliga_a_da_peca(monkeypatch):
    monkeypatch.setattr(config, "CHAMADA_COMENTE", "")
    assert Instagram.legenda_final("Texto.", "", CHAMADA) == "Texto."


def test_grade_aceita_chamada_com_cartela_desligada():
    assert grade.validar(_item(chamada=CHAMADA, cartela=False)) == []
    p = grade.peca(_item(chamada=CHAMADA, cartela=False))
    assert p["chamada"] == CHAMADA and p["cartela"] is False


def test_grade_recusa_chamada_sem_live_com_cartela_live():
    assert any("cartela" in e for e in grade.validar(_item(chamada=CHAMADA)))


def test_grade_sem_campos_novos_fica_como_antes():
    p = grade.peca(_item())
    assert p["chamada"] is None and p["cartela"] is True


def test_chamada_faro_passa_na_trava():
    assert compliance.violacoes(CHAMADA) == []


def test_reel_sem_cartela_nao_monta_cartela(monkeypatch):
    from src import cartela
    chamou = []
    monkeypatch.setattr(cartela, "reel_com_cartela", lambda url: chamou.append(url) or ("x", "a"))

    class IG:
        def reel(self, url, leg, hashtags, capa_url=None, colaboradores=None, chamada=None):
            return {"url": url, "chamada": chamada}

    r = pecas._reel_instagram(IG(), {"cartela": False, "chamada": CHAMADA, "capa": None}, "orig.mp4", "leg", "")
    assert chamou == [] and r == {"url": "orig.mp4", "chamada": CHAMADA}
