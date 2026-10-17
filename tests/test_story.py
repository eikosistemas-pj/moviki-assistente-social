# -*- coding: utf-8 -*-
"""Grade de stories com video e trilha (17/10/2026)."""
import os
import subprocess
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from src import cartela, config, story, story_video as sv

TEM_FFMPEG = cartela._ffmpeg() is not None


def _h(tipo=None, cta=None, ramo=None, peca="p", dias=0):
    q = (datetime.now(timezone.utc) - timedelta(days=dias)).isoformat(timespec="seconds")
    return {"formato": "story", "tipo": tipo, "cta": cta, "ramo": ramo, "peca": peca, "quando": q}


# ------------------------------------------------------------------ cortes
def test_video_curto_vira_um_corte():
    assert sv.cortes(18.0, []) == [(0.0, 18.0)]


def test_cortes_terminam_na_pausa_e_cabem_no_story():
    cs = sv.cortes(40.0, [5.0, 12.4, 16.0, 27.5, 33.0])
    assert cs[0] == (0.0, 16.0)
    for ini, fim in cs:
        assert sv.CORTE_MIN <= fim - ini <= sv.CORTE_MAX
    assert all(a[1] == b[0] for a, b in zip(cs, cs[1:]))


def test_sem_pausa_usa_o_respiro_mais_fundo():
    dbs = [-20.0] * 800
    dbs[260] = dbs[261] = dbs[262] = -60.0     # vale em 13 s
    cs = sv.cortes(40.0, [], dbs=dbs)
    assert cs[0] == (0.0, 13.05)


def test_pausas_e_fundo():
    fala = [-20.0] * 40 + [-45.0] * 6 + [-20.0] * 40
    assert sv.pausas(fala) == [2.15]
    assert sv.tem_fundo([-22.0] * 60 + [-35.0] * 60)          # piso alto = ja tem trilha
    assert not sv.tem_fundo([-22.0] * 60 + [-120.0] * 60)     # silencio digital = so voz


def test_trilha_gira():
    lista = [Path("a.mp3"), Path("b.mp3"), Path("c.mp3")]
    assert sv.escolher_trilha([], lista).stem == "a"
    assert sv.escolher_trilha(["a", "b"], lista).stem == "c"
    assert sv.escolher_trilha(["c", "a", "b"], lista).stem == "b"


def test_biblioteca_de_trilhas_no_repositorio():
    assert len(sv.trilhas()) >= 6


# ------------------------------------------------------------------ grade
def test_alterna_video_e_arte():
    assert story.proximo_tipo([]) == "video"
    assert story.proximo_tipo([_h(tipo="video")]) == "arte"
    assert story.proximo_tipo([_h(tipo="arte")]) == "video"
    assert story.proximo_tipo([_h(tipo=None)]) == "video"


def test_chamada_so_no_video(monkeypatch):
    monkeypatch.setattr(config, "CARTELA_STORY", True)
    assert story.precisa_cta("video")
    assert not story.precisa_cta("arte")
    monkeypatch.setattr(config, "CARTELA_STORY", False)
    assert not story.precisa_cta("video")


def test_nao_repete_ramo_quando_ha_outro():
    lista = [{"id": "a", "categoria": "moda"}, {"id": "b", "categoria": "beleza"}]
    assert [p["id"] for p in story.sem_repetir_ramo(lista, "moda")] == ["b"]
    assert story.sem_repetir_ramo(lista[:1], "moda") == lista[:1]


def test_criador_fica_de_quarentena():
    hist = [_h(peca="c:1", dias=2), _h(peca="c:2", dias=9)]
    g = story._filtrar_criadores({"casa": [], "criador": [{"id": "c:1"}, {"id": "c:2"}]}, hist)
    assert [p["id"] for p in g["criador"]] == ["c:2"]


def test_corte_gira_pelo_video(monkeypatch):
    monkeypatch.setattr(config, "ESTADO_DIR", Path(tempfile.mkdtemp()))
    assert story.proximo_corte("video:x", 3) == 0
    story.avancar_corte("video:x", 0, 3)
    assert story.proximo_corte("video:x", 3) == 1
    story.avancar_corte("video:x", 2, 3)
    assert story.proximo_corte("video:x", 3) == 0


def test_textos_da_chamada_passam_na_trava():
    from src import compliance
    for t in sv.TITULOS_CTA:
        assert compliance.violacoes(t) == []


# ------------------------------------------------------------------ montagem
def _video(tmp, com_audio=True, seg=6):
    exe = cartela._ffmpeg()
    v = tmp / ("a.mp4" if com_audio else "m.mp4")
    cmd = [exe, "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=size=720x1280:rate=25"]
    if com_audio:
        cmd += ["-f", "lavfi", "-i", "sine=frequency=440"]
    cmd += ["-t", str(seg), "-c:v", "libx264"] + (["-c:a", "aac", "-shortest"] if com_audio else []) + [str(v)]
    subprocess.run(cmd, check=True)
    return v


@pytest.mark.skipif(not TEM_FFMPEG, reason="sem ffmpeg")
@pytest.mark.parametrize("com_audio,fundo,cta", [(True, False, True), (True, True, True),
                                                 (False, False, False), (True, False, False)])
def test_corte_de_video(tmp_path, com_audio, fundo, cta):
    v = _video(tmp_path, com_audio)
    c = sv.salvar_cta("t", tmp_path) if cta else None
    s = sv.montar(str(tmp_path / "s.mp4"), video=v, ini=1.0, fim=5.0, trilha=sv.trilhas()[0],
                  cta=c, fundo=fundo, audio=com_audio)
    dur, audio = cartela._sondar(cartela._ffmpeg(), s)
    esperado = 4.0
    assert audio and abs(dur - esperado) < 0.3


@pytest.mark.skipif(not TEM_FFMPEG, reason="sem ffmpeg")
def test_faixa_da_chamada_e_transparente_no_miolo():
    img = sv.imagem_cta("x")
    assert img.size == (1080, 1920) and img.mode == "RGBA"
    assert img.getpixel((540, 600))[3] == 0          # o video aparece inteiro em cima
    assert img.getpixel((540, 1700))[3] > 0          # faixa embaixo
    assert all(img.getpixel((540, y))[3] == 0 for y in range(1780, 1920, 20))  # caixa de resposta livre


def test_trilha_sempre_de_fundo():
    assert sv.VOL_TRILHA_SOZINHA <= 0.5 and sv.VOL_TRILHA_SOB_VOZ <= 0.12


@pytest.mark.skipif(not TEM_FFMPEG, reason="sem ffmpeg")
def test_video_com_trilha_propria_nao_recebe_a_nossa(tmp_path):
    v = _video(tmp_path, True)
    a = sv.montar(str(tmp_path / "s1.mp4"), video=v, ini=0, fim=4, trilha=sv.trilhas()[0], fundo=True)
    b = sv.montar(str(tmp_path / "s2.mp4"), video=v, ini=0, fim=4, trilha=None, fundo=True)
    assert abs(os.path.getsize(a) - os.path.getsize(b)) < 2000


@pytest.mark.skipif(not TEM_FFMPEG, reason="sem ffmpeg")
def test_arte_animada_com_trilha(tmp_path):
    img = cartela.arte.salvar(cartela.imagem("story"), str(tmp_path / "arte.jpg"))
    s = sv.montar(str(tmp_path / "s.mp4"), imagem=img, trilha=sv.trilhas()[0])
    dur, audio = cartela._sondar(cartela._ffmpeg(), s)
    assert audio and abs(dur - sv.ARTE_SEG) < 0.3


def test_story_longo_demais_recusa(tmp_path):
    with pytest.raises(Exception):
        sv.montar(str(tmp_path / "s.mp4"), video="x.mp4", ini=0, fim=70)


def test_arte_parada_nao_solta_mais_cartela_separada(monkeypatch):
    """O story estatico 'Responda LIVE' depois de toda arte acabou."""
    import inspect
    from src import pecas
    assert "_story_cartela(ig)" not in inspect.getsource(pecas.publicar).split("def _reel_instagram")[0]
