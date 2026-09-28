# -*- coding: utf-8 -*-
"""Triagem "so parceiro" e Kit TikTok do dia (28/09/2026), sem rede."""
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path

import run_metricas
from src import config, estado, material, tiktok, triagem

LEG = ("#publi Ninguém compra de quem não acha.\n\n30 dias grátis. Sem cartão, "
       "sem fidelidade — você só continua se fizer sentido.\nComece pelo meu link: {link}")


def _tmp(monkeypatch, chave="x"):
    monkeypatch.setattr(config, "ESTADO_DIR", Path(tempfile.mkdtemp()))
    monkeypatch.setattr(config, "ANTHROPIC_API_KEY", chave)
    monkeypatch.setattr(config, "LIVE_NA_PAGINA", True)


def _feed(i, **kw):
    b = {"id": f"feed-{i}", "tipo": "feed", "categoria": "moda", "titulo": f"Feed {i}",
         "w": "1080", "h": "1350", "arquivo": f"material/feed/feed-{i}.jpg", "legenda": LEG}
    b.update(kw)
    return b


def _video(i, cat="moda", **kw):
    b = {"id": f"video-{i}", "tipo": "video", "categoria": cat, "titulo": f"Vídeo {i}",
         "w": 1080, "h": 1920, "duracao": "0:40", "arquivo": f"material/video-{i}.mp4",
         "capa": f"material/capas/video-{i}.webp", "legenda": LEG}
    b.update(kw)
    return b


def _cat(*itens):
    return {"versao": "t", "itens": list(itens)}


# ------------------------------------------------------------- so_parceiro
def test_campo_so_parceiro_tira_a_peca_da_pagina(monkeypatch):
    _tmp(monkeypatch)
    cat = _cat(_feed(1), _feed(2, so_parceiro=True), _feed(3, so_parceiro="sim"))
    assert [p["id"] for p in material.pecas(cat, "feed")] == ["feed-1"]


def test_video_leva_capa_para_a_triagem(monkeypatch):
    _tmp(monkeypatch)
    p = material.pecas(_cat(_video(1)), "reel")[0]
    assert p["capa"] is None                      # webp nao serve de capa do Instagram
    assert p["capa_triagem"].endswith("material/capas/video-1.webp")
    assert triagem.imagem_da_peca(p) == p["capa_triagem"]


# ------------------------------------------------------------- triagem
def test_triagem_barra_arte_com_texto_de_parceiro_e_guarda_o_veredito(monkeypatch):
    _tmp(monkeypatch)
    pecas = material.pecas(_cat(_feed(1), _feed(2)), "feed")
    chamadas = []

    def ia(url):
        chamadas.append(url)
        return {"parceiro": url.endswith("feed-2.jpg"), "trecho": "link deste parceiro" if url.endswith("feed-2.jpg") else ""}

    assert [p["id"] for p in triagem.filtrar(pecas, perguntar=ia)] == ["feed-1"]
    assert len(chamadas) == 2
    # segunda vez: nao pergunta de novo
    assert [p["id"] for p in triagem.filtrar(pecas, perguntar=ia)] == ["feed-1"]
    assert len(chamadas) == 2


def test_triagem_falha_fechada_quando_a_ia_cai(monkeypatch):
    _tmp(monkeypatch)
    pecas = material.pecas(_cat(_feed(1)), "feed")

    def ia(url):
        raise RuntimeError("fora do ar")

    assert triagem.filtrar(pecas, perguntar=ia) == []
    assert triagem.resumo(pecas)["pendentes"] == 1


def test_arte_trocada_no_mesmo_id_e_olhada_de_novo(monkeypatch):
    _tmp(monkeypatch)
    v1 = material.pecas(_cat(_feed(1)), "feed")
    triagem.filtrar(v1, perguntar=lambda u: {"parceiro": False})
    v2 = material.pecas(_cat(_feed(1, arquivo="material/feed/feed-1-v2.jpg")), "feed")
    assert triagem.veredito(v2[0]) is None


def test_limite_por_rodada(monkeypatch):
    _tmp(monkeypatch)
    pecas = material.pecas(_cat(*[_feed(i) for i in range(10)]), "feed")
    n = []
    triagem.filtrar(pecas, limite=3, perguntar=lambda u: n.append(u) or {"parceiro": False})
    assert len(n) == 3


def test_sem_chave_a_triagem_desliga_e_nada_muda(monkeypatch):
    _tmp(monkeypatch, chave="")
    pecas = material.pecas(_cat(_feed(1), _feed(2)), "feed")
    assert len(triagem.filtrar(pecas)) == 2


def test_resposta_da_ia_com_texto_em_volta():
    assert triagem._ler_json('Claro: {"parceiro": true, "trecho": "meu link"}')["parceiro"] is True


# ------------------------------------------------------------- tiktok
def _videos(monkeypatch, *itens):
    return material.pecas(_cat(*itens), "reel")


def test_agenda_de_7_dias_sem_repetir_e_sem_ramo_seguido(monkeypatch):
    _tmp(monkeypatch)
    vids = _videos(monkeypatch, *[_video(i, cat=("moda" if i % 2 else "pet")) for i in range(8)])
    ag = tiktok.planejar(vids, date(2026, 10, 1))
    dias = sorted(ag)
    assert len(dias) == 7
    assert len(set(ag.values())) == 7
    cats = [next(v["categoria"] for v in vids if v["id"] == ag[d]) for d in dias]
    assert all(a != b for a, b in zip(cats, cats[1:]))


def test_agenda_nao_muda_entre_as_duas_rodadas_do_dia(monkeypatch):
    _tmp(monkeypatch)
    vids = _videos(monkeypatch, *[_video(i) for i in range(5)])
    hoje = date(2026, 10, 1)
    a1 = tiktok.planejar(vids, hoje)
    a2 = tiktok.planejar(vids, hoje, a1)
    assert a1 == a2


def test_video_que_saiu_do_catalogo_sai_da_agenda(monkeypatch):
    _tmp(monkeypatch)
    vids = _videos(monkeypatch, *[_video(i) for i in range(9)])
    hoje = date(2026, 10, 1)
    a1 = tiktok.planejar(vids, hoje)
    fora = a1[hoje.isoformat()]
    a2 = tiktok.planejar([v for v in vids if v["id"] != fora], hoje, a1)
    assert fora not in a2.values()
    assert len([d for d in a2 if d >= hoje.isoformat()]) == 7


def test_video_nunca_usado_vem_antes(monkeypatch):
    _tmp(monkeypatch)
    vids = _videos(monkeypatch, *[_video(i) for i in range(9)])
    hoje = date(2026, 10, 8)
    antes = {"2026-10-01": "video-0", "2026-10-02": "video-1"}
    ag = tiktok.planejar(vids, hoje, antes)
    semana = [ag[d] for d in sorted(ag) if d >= hoje.isoformat()]
    assert "video-0" not in semana and "video-1" not in semana


def test_kit_leva_legenda_da_marca_com_hashtags(monkeypatch):
    _tmp(monkeypatch)
    vids = _videos(monkeypatch, _video(1))
    hoje = date(2026, 10, 1)
    kit = tiktok.kit(vids, hoje, tiktok.planejar(vids, hoje))
    k = kit[0]
    assert k["hoje"] and k["video"].endswith("material/video-1.mp4")
    assert "#publi" not in k["legenda"] and "{link}" not in k["legenda"] and "meu link" not in k["legenda"]
    assert "link da bio" in k["legenda"]
    assert k["legenda"].endswith(k["hashtags"]) and len(k["hashtags"].split()) <= 5


def test_relatorio_monta_triagem_e_kit(monkeypatch):
    _tmp(monkeypatch)
    cat = _cat(_feed(1), _feed(2), _video(1), _video(2, cat="pet"), _video(3, so_parceiro=True))

    def ia(url):
        return {"parceiro": url.endswith("feed-2.jpg") or url.endswith("video-2.webp"), "trecho": "fale comigo"}

    out = run_metricas.material_e_tiktok(datetime(2026, 10, 1, 12, tzinfo=timezone.utc), cat, ia)
    assert out["triagem"]["barradas"] == 2 and out["triagem"]["pendentes"] == 0
    assert out["tiktok"]["videos_disponiveis"] == 1
    assert {d["id"] for d in out["tiktok"]["dias"]} == {"video-1"}
    assert estado.ler_lista("tiktok.json")["agenda"]


def test_relatorio_sem_video_acende_alerta(monkeypatch):
    _tmp(monkeypatch)
    out = run_metricas.material_e_tiktok(datetime(2026, 10, 1, 12, tzinfo=timezone.utc),
                                         _cat(_feed(1)), lambda u: {"parceiro": False})
    assert out["tiktok"]["dias"] == []
    assert any(a["tipo"] == "tiktok" for a in out["_alertas_extra"])


def test_poucos_videos_nao_repetem_na_semana(monkeypatch):
    _tmp(monkeypatch)
    vids = _videos(monkeypatch, _video(1), _video(2, cat="pet"))
    ag = tiktok.planejar(vids, date(2026, 10, 1))
    assert sorted(ag.values()) == ["video-1", "video-2"]


def test_video_no_firebase_storage_continua_valendo(monkeypatch):
    _tmp(monkeypatch)
    url = ("https://firebasestorage.googleapis.com/v0/b/moviki-app.firebasestorage.app/o/"
           "material%2Fvideo-9.mp4?alt=media&token=abc")
    capa = ("https://firebasestorage.googleapis.com/v0/b/moviki-app.firebasestorage.app/o/"
            "material%2Fcapas%2Fvideo-9.webp?alt=media&token=def")
    p = material.pecas(_cat(_video(9, arquivo=url, capa=capa)), "reel")
    assert len(p) == 1 and p[0]["url"] == url and p[0]["capa_triagem"] == capa


def test_relatorio_olha_video_antes_de_feed_e_story(monkeypatch):
    _tmp(monkeypatch)
    monkeypatch.setattr(triagem, "POR_RELATORIO", 3)
    cat = _cat(*[_feed(i) for i in range(5)], _video(1), _video(2, cat="pet"))
    out = run_metricas.material_e_tiktok(datetime(2026, 10, 1, 12, tzinfo=timezone.utc), cat,
                                         lambda u: {"parceiro": False})
    assert out["tiktok"]["videos_disponiveis"] == 2
