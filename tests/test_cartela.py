# -*- coding: utf-8 -*-
"""Cartela "Comente LIVE" (08/10/2026)."""
import subprocess

import pytest

from src import cartela, compliance, config, pecas


def test_imagem_nos_dois_modos():
    for modo in ("reel", "story"):
        img = cartela.imagem(modo)
        assert img.size == (1080, 1920)


def test_voz_no_repositorio():
    assert cartela.VOZ.exists() and cartela.VOZ.stat().st_size > 20000


def test_textos_passam_na_trava():
    for t in ("Escreva LIVE nos comentários e eu te mando no direct o link de uma live de exemplo do seu ramo.",
              "Responda esta história com LIVE e eu te mando no direct o link de uma live de exemplo do seu ramo.",
              "Quer ver a live da sua loja funcionando?"):
        assert compliance.violacoes(t) == []


@pytest.mark.skipif(cartela._ffmpeg() is None, reason="sem ffmpeg")
@pytest.mark.parametrize("com_audio", [True, False])
def test_montar_emenda_cartela_no_fim(tmp_path, com_audio):
    exe = cartela._ffmpeg()
    video = tmp_path / "v.mp4"
    cmd = [exe, "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=size=720x1280:rate=25"]
    if com_audio:
        cmd += ["-f", "lavfi", "-i", "sine=frequency=440"]
    cmd += ["-t", "3", "-c:v", "libx264"] + (["-c:a", "aac", "-shortest"] if com_audio else []) + [str(video)]
    subprocess.run(cmd, check=True)
    img = cartela.arte.salvar(cartela.imagem("reel"), str(tmp_path / "c.png"))
    saida = cartela.montar(video, cartela.VOZ, img, str(tmp_path / "s.mp4"), exe)
    dur, audio = cartela._sondar(exe, saida)
    dur_voz, _ = cartela._sondar(exe, cartela.VOZ)
    assert audio
    assert dur == pytest.approx(3 + dur_voz + cartela.FOLGA_FINAL, abs=0.5)


class _IG:
    def __init__(self, recusa=False):
        self.recusa, self.urls = recusa, []

    def reel(self, url, *a, **k):
        self.urls.append(url)
        if self.recusa and url == "https://cartela":
            raise RuntimeError("Instagram recusou")
        return "m1"

    def story(self, url):
        self.urls.append(url)
        return "s1"


def test_reel_usa_cartela_e_apaga_o_asset(monkeypatch):
    apagados = []
    monkeypatch.setattr(cartela, "reel_com_cartela", lambda u: ("https://cartela", 7))
    monkeypatch.setattr(cartela, "apagar", apagados.append)
    ig = _IG()
    assert pecas._reel_instagram(ig, {"id": "x"}, "https://orig", "leg", "") == "m1"
    assert ig.urls == ["https://cartela"] and apagados == [7]


def test_reel_volta_ao_original_se_o_instagram_recusar(monkeypatch):
    monkeypatch.setattr(cartela, "reel_com_cartela", lambda u: ("https://cartela", 7))
    monkeypatch.setattr(cartela, "apagar", lambda a: None)
    ig = _IG(recusa=True)
    assert pecas._reel_instagram(ig, {"id": "x"}, "https://orig", "leg", "") == "m1"
    assert ig.urls == ["https://cartela", "https://orig"]


def test_reel_sem_cartela_publica_original(monkeypatch):
    monkeypatch.setattr(cartela, "reel_com_cartela", lambda u: (None, None))
    ig = _IG()
    pecas._reel_instagram(ig, {"id": "x"}, "https://orig", "leg", "")
    assert ig.urls == ["https://orig"]


def test_cartela_desligada_nao_faz_nada(monkeypatch):
    monkeypatch.setattr(config, "CARTELA_REEL", False)
    monkeypatch.setattr(config, "CARTELA_STORY", False)
    assert cartela.reel_com_cartela("https://orig") == (None, None)
    assert cartela.story_cartela() is None


def test_story_cartela_falha_nao_quebra(monkeypatch):
    monkeypatch.setattr(cartela, "story_cartela", lambda: "https://card")

    class IGQuebra:
        def story(self, url):
            raise RuntimeError("x")
    pecas._story_cartela(IGQuebra())   # nao levanta
