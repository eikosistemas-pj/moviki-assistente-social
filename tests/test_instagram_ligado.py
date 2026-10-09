# -*- coding: utf-8 -*-
"""
Instagram formato a formato, hashtags e alarme do plano B (27/09/2026).
"""
import os

from src import config, conteudo, pecas
from src.social.instagram import Instagram


def _cfg(monkeypatch, so_fb=False, ig_id="17841440001427879", formatos=""):
    monkeypatch.setattr(config, "SO_FACEBOOK", so_fb)
    monkeypatch.setattr(config, "IG_ACCOUNT_ID", ig_id)
    monkeypatch.setattr(config, "IG_FORMATOS",
                        {x.strip() for x in formatos.split(",") if x.strip()})


# ------------------------------------------------------------ chave por formato
def test_so_facebook_manda_em_tudo(monkeypatch):
    _cfg(monkeypatch, so_fb=True, formatos="feed,story,reel")
    assert not any(config.instagram_ligado(f) for f in ("feed", "story", "reel"))


def test_sem_ig_account_id_nada_vai_ao_instagram(monkeypatch):
    _cfg(monkeypatch, ig_id="")
    assert not config.instagram_ligado("feed")


def test_ig_formatos_vazio_liga_todos(monkeypatch):
    _cfg(monkeypatch)
    assert all(config.instagram_ligado(f) for f in ("feed", "story", "reel"))


def test_rampa_so_feed(monkeypatch):
    _cfg(monkeypatch, formatos="feed")
    assert config.instagram_ligado("feed")
    assert not config.instagram_ligado("story")
    assert not config.instagram_ligado("reel")


def test_rampa_feed_e_reel_com_espaco(monkeypatch):
    _cfg(monkeypatch, formatos=" feed , reel ")
    assert config.instagram_ligado("reel") and not config.instagram_ligado("story")


def test_nenhum_desliga(monkeypatch):
    _cfg(monkeypatch, formatos="nenhum")
    assert not config.instagram_ligado("feed")


# ------------------------------------------------------------ hashtags
def test_hashtags_no_maximo_cinco_e_moviki_primeiro():
    for ramo in list(conteudo.HASHTAGS_RAMO) + [None, "inexistente"]:
        tags = conteudo.hashtags("conversao", ramo).split()
        assert len(tags) <= config.HASHTAGS_MAX
        assert tags[0] == "#moviki"
        assert len(set(tags)) == len(tags)


def test_hashtag_segue_o_ramo():
    assert "#farmacia" in conteudo.hashtags("conversao", "farmacia")
    assert "#foodtruck" not in conteudo.hashtags("conversao", "farmacia")
    assert "#petshop" in conteudo.hashtags("conversao", "pet")


def test_legenda_final_respeita_hashtags_ja_no_texto():
    leg = Instagram.legenda_final("Texto #um #dois #tres", "#moviki #a #b #c")
    assert len([t for t in leg.split() if t.startswith("#")]) == 5


def test_legenda_final_corta_texto_mas_preserva_hashtags():
    leg = Instagram.legenda_final("x" * 5000, "#moviki #pet")
    assert len(leg) <= 2200
    assert leg.endswith("#moviki #pet")


# ------------------------------------------------------------ alarme do plano B
def _peca():
    return {"id": "st1", "formato": "story", "midia": "imagem", "origem": "material",
            "url": "https://app.moviki.com.br/material/a.jpg", "titulo": "t"}


def test_plano_b_publica_na_pagina_e_deixa_alarme(monkeypatch):
    _cfg(monkeypatch)
    alerta = "/tmp/teste-alerta-instagram.txt"
    if os.path.exists(alerta):
        os.remove(alerta)
    monkeypatch.setattr(config, "ALERTA_INSTAGRAM", alerta)
    monkeypatch.setattr(config, "DRY_RUN", False)
    import tempfile
    from pathlib import Path
    monkeypatch.setattr(config, "ESTADO_DIR", Path(tempfile.mkdtemp()))
    marcados = []
    monkeypatch.setattr(pecas, "marcar", lambda p, mid, rede, extra=None: marcados.append((rede, extra)))

    import src.social.instagram as ig_mod
    import src.social.facebook as fb_mod

    class IgQuebrado:
        def story(self, url):
            raise RuntimeError("conta restrita")

    class FbOk:
        def story_foto(self, url):
            return "fb-1"

    monkeypatch.setattr(ig_mod, "Instagram", IgQuebrado)
    monkeypatch.setattr(fb_mod, "Facebook", FbOk)

    assert pecas.publicar(_peca()) == "fb-1"
    assert len(marcados) == 1 and marcados[0][0] == "facebook"
    assert marcados[0][1]["planoB"] is True
    assert "conta restrita" in marcados[0][1]["erroInstagram"]
    assert "conta restrita" in open(alerta, encoding="utf-8").read()
    os.remove(alerta)


def test_formato_fora_da_rampa_vai_direto_na_pagina_sem_alarme(monkeypatch):
    _cfg(monkeypatch, formatos="feed")
    alerta = "/tmp/teste-alerta-instagram-2.txt"
    monkeypatch.setattr(config, "ALERTA_INSTAGRAM", alerta)
    monkeypatch.setattr(config, "DRY_RUN", False)
    import tempfile
    from pathlib import Path
    monkeypatch.setattr(config, "ESTADO_DIR", Path(tempfile.mkdtemp()))
    monkeypatch.setattr(pecas, "marcar", lambda *a, **k: None)

    import src.social.instagram as ig_mod
    import src.social.facebook as fb_mod

    class IgNaoPodeSerChamado:
        def __init__(self):
            raise AssertionError("story fora da rampa nao pode ir ao Instagram")

    class FbOk:
        def story_foto(self, url):
            return "fb-2"

    monkeypatch.setattr(ig_mod, "Instagram", IgNaoPodeSerChamado)
    monkeypatch.setattr(fb_mod, "Facebook", FbOk)
    assert pecas.publicar(_peca()) == "fb-2"
    assert not os.path.exists(alerta)


# ------------------------------------------------- chamada "Comente LIVE" (08/10/2026)
def test_chamada_comente_live_na_primeira_linha():
    leg = Instagram.legenda_final("Sua loja ao vivo.", "#moviki")
    assert leg.splitlines()[0] == config.CHAMADA_COMENTE
    assert "Sua loja ao vivo." in leg


def test_chamada_nao_repete():
    leg = Instagram.legenda_final("Comente LIVE aqui embaixo.", "")
    assert leg.lower().count("comente live") == 1


def test_chamada_passa_na_trava():
    from src import compliance
    assert compliance.violacoes(config.CHAMADA_COMENTE) == []


def test_chamada_desligada(monkeypatch):
    monkeypatch.setattr(config, "CHAMADA_COMENTE", "")
    assert Instagram.legenda_final("Texto.", "") == "Texto."
