# -*- coding: utf-8 -*-
"""Kit TikTok com a chamada do direct e a cartela "Mande LIVE no direct" (09/10/2026)."""
from datetime import date

import pytest

from src import cartela, compliance, config, tiktok


def test_imagem_e_voz_do_tiktok():
    assert cartela.imagem("tiktok").size == (1080, 1920)
    assert cartela.VOZ_TIKTOK.exists() and cartela.VOZ_TIKTOK.stat().st_size > 20000
    assert cartela.VOZ_TIKTOK != cartela.VOZ        # a voz do Instagram fala "comenta", que no TikTok nao dispara


def test_textos_do_tiktok_passam_na_trava():
    for t in (config.CHAMADA_TIKTOK,
              "Mande LIVE no direct do @moviki.oficial e eu te mando o link de uma live de exemplo."):
        assert t and compliance.violacoes(t) == []


def test_legenda_do_kit_abre_com_a_chamada_do_direct():
    peca = {"id": "v1", "titulo": "Vídeo", "categoria": "moda",
            "legenda_ig": "Sua loja ao vivo.\n\nConheça pelo link da bio."}
    texto, tags = tiktok.legenda(peca, date(2026, 10, 9))
    assert texto.startswith(config.CHAMADA_TIKTOK)
    assert "Comente" not in texto and "comentários" not in texto
    assert texto.endswith(tags)


def test_chamada_desligada(monkeypatch):
    monkeypatch.setattr(config, "CHAMADA_TIKTOK", "")
    texto, _ = tiktok.legenda({"id": "v1", "legenda_ig": "Sua loja ao vivo."}, date(2026, 10, 9))
    assert texto.startswith("Sua loja ao vivo.")


def test_nome_do_asset_e_fixo_e_limpo():
    assert cartela.nome_tiktok("2026-10-09", "video-comercio-Açaí 2") == "tiktok-2026-10-09-video-comercio-a-a-2.mp4"
    assert cartela._dia_do_nome("tiktok-2026-10-09-x.mp4") == "2026-10-09"
    assert cartela._dia_do_nome("reel-2026.mp4") == ""


def _dias():
    return [{"dia": f"2026-10-{d:02d}", "hoje": d == 9, "id": f"v{d}", "video": f"https://v/{d}.mp4"}
            for d in range(9, 16)]


class _Release:
    """Release falso: guarda nomes subidos e apagados, sem rede."""
    def __init__(self, monkeypatch, existentes=(), falha_montar=False):
        self.subidos, self.apagados, self.montados = [], [], []
        self.lista = [{"id": 100 + i, "name": n, "browser_download_url": "https://github.com/x/" + n}
                      for i, n in enumerate(existentes)]
        monkeypatch.setattr(config, "CARTELA_TIKTOK", True)
        monkeypatch.setattr(config, "DRY_RUN", False)
        monkeypatch.setattr(cartela, "_ffmpeg", lambda: "/bin/ffmpeg")
        monkeypatch.setattr(cartela, "_cabecalhos", lambda: {})
        monkeypatch.setattr(cartela, "_release_id", lambda h, tag=None: 1)
        monkeypatch.setattr(cartela, "_assets", lambda h, rid: list(self.lista))

        def montar(url, exe):
            self.montados.append(url)
            if falha_montar:
                raise RuntimeError("ffmpeg falhou")
            return __file__
        monkeypatch.setattr(cartela, "_montar_tiktok", montar)

        def subir(h, rid, caminho, nome):
            self.subidos.append(nome)
            return {"id": 9, "name": nome, "browser_download_url": "https://github.com/x/" + nome}
        monkeypatch.setattr(cartela, "_subir", subir)
        monkeypatch.setattr(cartela, "apagar", self.apagados.append)


def test_monta_hoje_primeiro_e_respeita_o_limite(monkeypatch):
    r = _Release(monkeypatch)
    dias = cartela.kit_tiktok(_dias(), "2026-10-09", novos=2)
    assert r.subidos == [cartela.nome_tiktok("2026-10-09", "v9"), cartela.nome_tiktok("2026-10-10", "v10")]
    com = [d["dia"] for d in dias if d.get("video_cartela")]
    assert com == ["2026-10-09", "2026-10-10"]


def test_reaproveita_o_que_ja_subiu_e_apaga_o_vencido(monkeypatch):
    ja = cartela.nome_tiktok("2026-10-09", "v9")
    velho = cartela.nome_tiktok("2026-10-01", "antigo")
    recente = cartela.nome_tiktok("2026-10-07", "ontem")
    r = _Release(monkeypatch, existentes=[ja, velho, recente])
    dias = cartela.kit_tiktok(_dias(), "2026-10-09", novos=0)
    assert r.subidos == [] and r.montados == []
    assert dias[0]["video_cartela"].endswith(ja)
    assert r.apagados == [101]            # so o de 01/10; o de 07/10 ainda esta na folga


def test_falha_na_montagem_deixa_o_video_original(monkeypatch):
    _Release(monkeypatch, falha_montar=True)
    dias = cartela.kit_tiktok(_dias(), "2026-10-09", novos=3)
    assert all("video_cartela" not in d for d in dias)
    assert all(d["video"].startswith("https://v/") for d in dias)


def test_sem_token_nao_quebra(monkeypatch):
    monkeypatch.setattr(config, "CARTELA_TIKTOK", True)
    monkeypatch.setattr(cartela, "_ffmpeg", lambda: "/bin/ffmpeg")

    def sem():
        raise RuntimeError("GITHUB_TOKEN ausente")
    monkeypatch.setattr(cartela, "_cabecalhos", sem)
    dias = cartela.kit_tiktok(_dias(), "2026-10-09")
    assert all("video_cartela" not in d for d in dias)


def test_desligada_nao_faz_nada(monkeypatch):
    monkeypatch.setattr(config, "CARTELA_TIKTOK", False)
    monkeypatch.setattr(cartela, "_cabecalhos", lambda: pytest.fail("nao devia chamar o GitHub"))
    assert cartela.kit_tiktok(_dias(), "2026-10-09") == _dias()


@pytest.mark.skipif(cartela._ffmpeg() is None, reason="sem ffmpeg")
def test_montagem_real_com_a_voz_do_tiktok(tmp_path):
    import subprocess
    exe = cartela._ffmpeg()
    video = tmp_path / "v.mp4"
    subprocess.run([exe, "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=size=720x1280:rate=25",
                    "-t", "3", "-c:v", "libx264", str(video)], check=True)
    img = cartela.arte.salvar(cartela.imagem("tiktok"), str(tmp_path / "c.png"))
    saida = cartela.montar(video, cartela.VOZ_TIKTOK, img, str(tmp_path / "s.mp4"), exe)
    dur, audio = cartela._sondar(exe, saida)
    dur_voz, _ = cartela._sondar(exe, cartela.VOZ_TIKTOK)
    assert audio and dur == pytest.approx(3 + dur_voz + cartela.FOLGA_FINAL, abs=0.5)
