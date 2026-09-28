# -*- coding: utf-8 -*-
"""
Rampa por data, freio automatico, hashtag de data comemorativa e relatorio
das redes para o painel do dono (28/09/2026).
"""
import tempfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import run_metricas
from src import config, conteudo, freio


def _cfg(monkeypatch, formatos="", so_fb=False, ig="17841440001427879"):
    monkeypatch.setattr(config, "SO_FACEBOOK", so_fb)
    monkeypatch.setattr(config, "IG_ACCOUNT_ID", ig)
    monkeypatch.setattr(config, "IG_FORMATOS",
                        {x.strip() for x in formatos.split(",") if x.strip()})
    monkeypatch.setattr(config, "ESTADO_DIR", Path(tempfile.mkdtemp()))


# ------------------------------------------------------------ rampa por data
def test_rampa_liga_cada_formato_no_seu_dia(monkeypatch):
    _cfg(monkeypatch, "feed,reel@2026-10-05,story@2026-10-12")
    d = date(2026, 10, 4)
    assert config.instagram_ligado("feed", d)
    assert not config.instagram_ligado("reel", d)
    assert config.instagram_ligado("reel", date(2026, 10, 5))
    assert not config.instagram_ligado("story", date(2026, 10, 11))
    assert config.instagram_ligado("story", date(2026, 10, 12))


def test_data_mal_escrita_nunca_liga(monkeypatch):
    _cfg(monkeypatch, "feed,reel@05/10/2026")
    assert not config.instagram_ligado("reel", date(2027, 1, 1))
    assert config.instagram_ligado("feed", date(2027, 1, 1))


def test_so_facebook_vence_a_rampa(monkeypatch):
    _cfg(monkeypatch, "feed,reel@2026-10-05", so_fb=True)
    assert not config.instagram_ligado("feed", date(2026, 12, 1))


# ------------------------------------------------------------ freio
def test_duas_falhas_seguidas_acionam_o_freio(monkeypatch):
    _cfg(monkeypatch)
    t0 = datetime(2026, 10, 6, 12, tzinfo=timezone.utc)
    assert freio.no_instagram("feed", t0)
    assert freio.falhou("feed", "erro 1", t0) is False
    assert freio.no_instagram("feed", t0)
    assert freio.falhou("reel", "erro 2", t0) is True
    assert not freio.no_instagram("feed", t0 + timedelta(hours=71))
    assert freio.no_instagram("feed", t0 + timedelta(hours=73))


def test_sucesso_no_meio_zera_a_contagem(monkeypatch):
    _cfg(monkeypatch)
    t0 = datetime(2026, 10, 6, 12, tzinfo=timezone.utc)
    freio.falhou("feed", "x", t0)
    freio.sucesso()
    assert freio.falhou("feed", "y", t0) is False
    assert freio.no_instagram("feed", t0)


# ------------------------------------------------------------ hashtags de data
def test_data_comemorativa_entra_em_segundo_e_teto_continua_5():
    tags = conteudo.hashtags("conversao", "infantil", date(2026, 10, 5)).split()
    assert tags[0] == "#moviki" and tags[1] == "#diadascriancas" and len(tags) == 5


def test_data_de_outro_ramo_nao_entra():
    assert "#diadascriancas" not in conteudo.hashtags("conversao", "farmacia", date(2026, 10, 5))


def test_black_friday_so_em_2026():
    assert "#blackfriday" in conteudo.hashtags("conversao", "farmacia", date(2026, 11, 20))
    assert "#blackfriday" not in conteudo.hashtags("conversao", "farmacia", date(2027, 11, 20))


def test_joalheria_e_otica_tem_hashtag_propria():
    assert "#joias" in conteudo.hashtags("conversao", "joalheria", date(2026, 9, 1))
    assert "#oculos" in conteudo.hashtags("conversao", "otica", date(2026, 9, 1))


# ------------------------------------------------------------ relatorio
def _hist(agora):
    q = lambda h: (agora - timedelta(hours=h)).isoformat(timespec="seconds")  # noqa: E731
    return [
        {"quando": q(2), "formato": "feed", "descricao": "Farmacia", "media_id": "ig1",
         "rede": "instagram", "fb": "pg_1", "peca": "feed-farm", "miniatura": "https://x/a.jpg"},
        {"quando": q(30), "formato": "story", "descricao": "Story", "media_id": "st1", "rede": "instagram"},
        {"quando": q(5), "formato": "reel", "descricao": "Reel", "media_id": "v9", "rede": "facebook",
         "planoB": True, "erroInstagram": "conta restrita"},
    ]


def test_relatorio_junta_metricas_das_duas_redes(monkeypatch):
    _cfg(monkeypatch, "feed")
    agora = datetime(2026, 9, 29, 20, tzinfo=timezone.utc)
    chamadas = []

    def get_ig(c, p):
        chamadas.append(("ig", c))
        return {"like_count": 7, "comments_count": 2, "permalink": "https://instagram.com/p/x"}

    def get_fb(c, p):
        chamadas.append(("fb", c))
        if c == "v9":
            return {"permalink_url": "/reel/9", "likes": {"summary": {"total_count": 3}},
                    "comments": {"summary": {"total_count": 1}}}
        return {"permalink_url": "https://fb.com/1", "reactions": {"summary": {"total_count": 4}},
                "comments": {"summary": {"total_count": 0}}, "shares": {"count": 1}}

    r = run_metricas.montar(_hist(agora), agora, get_ig, get_fb, {})
    feed = r["posts"][0]
    assert feed["ig"]["curtidas"] == 7 and feed["fb"]["curtidas"] == 4
    assert feed["miniatura"] == "https://x/a.jpg"
    # story do Instagram com mais de 23 h nao consulta a API (ja expirou)
    assert ("ig", "st1") not in chamadas
    reel = r["posts"][2]
    assert reel["fb"]["link"] == "https://www.facebook.com/reel/9"
    assert any(a["tipo"] == "plano_b" for a in r["alertas"])
    assert r["canal_hoje"]["feed"] == "instagram+facebook"
    assert r["canal_hoje"]["story"] == "facebook"
    assert r["totais"]["7d"]["ig"]["feed"]["curtidas"] == 7


def test_relatorio_nao_quebra_quando_a_meta_recusa(monkeypatch):
    _cfg(monkeypatch)
    agora = datetime(2026, 9, 29, 20, tzinfo=timezone.utc)
    ruim = lambda c, p: {"error": {"message": "token sem permissao"}}  # noqa: E731
    r = run_metricas.montar(_hist(agora), agora, ruim, ruim, {})
    assert r["posts"][0]["ig"]["erro"].startswith("token")


def test_agenda_aponta_post_que_faltou(monkeypatch):
    _cfg(monkeypatch)
    agora = datetime(2026, 9, 29, 20, tzinfo=timezone.utc)   # terca
    r = run_metricas.montar([], agora)
    assert any("28/09: feed saiu 0 de 1" in a["texto"] for a in r["alertas"])
    hoje = r["agenda"][-1]
    assert hoje["hoje"] and hoje["reel"]["esperado"] == 1
