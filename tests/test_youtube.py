# -*- coding: utf-8 -*-
"""Shorts do YouTube (22/10/2026)."""
import json
from datetime import date

import pytest

from src import compliance, config, util_net, youtube

HOJE = date(2026, 10, 22)
URL_G = "https://firebasestorage.googleapis.com/v0/b/moviki-app.firebasestorage.app/o/material%2F{}.mp4?alt=media"


def _peca(pid, legenda="Mostre o produto ao vivo.\n\nConheça pelo link da bio."):
    return {"id": pid, "url": f"https://x/{pid}.mp4", "capa": None, "titulo": f"Titulo {pid}",
            "legenda_ig": legenda}


def _grade(pid, **kw):
    it = {"id": pid, "formato": "reel", "video": URL_G.format(pid), "titulo": f"Grade {pid}",
          "legenda": "Legenda da grade.\n\nConheça pelo link da bio.", "canais": ["instagram"],
          "a_partir_de": "2026-10-01", "valido_ate": "2027-01-01"}
    it.update(kw)
    return it


CFG = {"playlists": {"ramo": "PLR", "bastidores": "PLB", "como_vender": "PLC"},
       "pular": {"ugc-bastidores-bf-x": "duplicado"},
       "fila": [{"id": "bf-b", "titulo": "Feito a mao", "descricao": "Desc a mao", "comentario": "Com"}]}


def test_fila_primeiro_e_depois_o_resto_em_ordem():
    c = youtube.candidatos(CFG, [_peca("video-comercio-moda")], [_grade("bf-a"), _grade("bf-b")], {}, HOJE)
    assert [x["id"] for x in c] == ["bf-b", "bf-a", "video-comercio-moda"]
    assert c[0]["fila"] and c[0]["titulo"] == "Feito a mao" and c[0]["playlist"] == "PLC"
    assert c[2]["playlist"] == "PLR"
    assert "https://www.moviki.com.br/live-shop/moda" in c[2]["descricao"]


def test_nunca_repete_nem_sobe_o_que_esta_em_pular():
    c = youtube.candidatos(CFG, [_peca("ugc-bastidores-bf-x"), _peca("video-comercio-moda")],
                           [_grade("bf-b")], {"video-comercio-moda": {"yt": "abc"}}, HOJE)
    assert [x["id"] for x in c] == ["bf-b"]


def test_vencido_ou_vencendo_fica_fora():
    itens = [_grade("bf-vencido", valido_ate="2026-10-20"),
             _grade("bf-vence-logo", valido_ate="2026-10-25"),
             _grade("bf-ok", valido_ate="2026-11-30")]
    c = youtube.candidatos({}, [], itens, {}, HOJE)
    assert [x["id"] for x in c] == ["bf-ok"]


def test_grade_vencida_tira_tambem_a_copia_do_material():
    c = youtube.candidatos({}, [_peca("bf-a")], [_grade("bf-a", valido_ate="2026-10-01")], {}, HOJE)
    assert c == []


def test_peca_da_fila_sem_video_disponivel_e_pulada():
    assert youtube.candidatos(CFG, [], [], {}, HOJE) == []


def test_playlist_por_tipo():
    assert youtube.playlist_de("ugc-bastidores-moda", CFG) == "PLB"
    assert youtube.playlist_de("video-shopping-pet", CFG) == "PLR"
    assert youtube.playlist_de("bf-pix", CFG) == "PLC"
    assert youtube.playlist_de("bf-pix", CFG, "bastidores") == "PLB"


def test_descricao_troca_link_da_bio_pelo_site():
    d = youtube.descricao_auto("Venda ao vivo.\n\nConheça pelo link da bio.")
    assert "link da bio" not in d.lower()
    assert "https://www.moviki.com.br/live-shop" in d and "#liveshop" in d


def test_titulo_cabe_no_limite_e_sem_sinal_de_menor_maior():
    t = youtube.titulo_auto("<b>" + "palavra " * 30)
    assert len(t) <= youtube.TITULO_MAX and "<" not in t and ">" not in t


def test_textos_passam_pela_trava():
    tit, desc, com = youtube.textos({"titulo": "Renda extra garantida com live", "descricao": "Ganhe R$ 5000 por mes",
                                     "comentario": None})
    assert not compliance.violacoes(tit) and not compliance.violacoes(desc) and not compliance.violacoes(com)


def test_fila_do_repositorio_esta_limpa_e_valida():
    cfg = youtube.carregar_fila()
    ids = [q["id"] for q in cfg["fila"]]
    assert len(ids) == len(set(ids))
    for q in cfg["fila"]:
        for campo in ("titulo", "descricao", "comentario"):
            assert not compliance.violacoes(q[campo]), (q["id"], campo, compliance.violacoes(q[campo]))
        assert len(q["titulo"]) <= youtube.TITULO_MAX, q["id"]
        assert "<" not in q["titulo"] + q["descricao"] and ">" not in q["titulo"] + q["descricao"]
        assert "trial" not in (q["titulo"] + q["descricao"] + q["comentario"]).lower()
        assert "tiktok" not in (q["titulo"] + q["descricao"] + q["comentario"]).lower()
        assert q.get("playlist") in cfg["playlists"], q["id"]
    assert not set(ids) & set(cfg["pular"])


def test_estado_inicial_tem_os_videos_ja_publicados():
    est = json.loads((config.ESTADO_DIR / "youtube.json").read_text(encoding="utf-8"))
    assert len(est["enviados"]) >= 49
    assert all(v.get("yt") for v in est["enviados"].values())


def test_visibilidade_padrao_e_privada(monkeypatch):
    monkeypatch.delenv("YT_VISIBILIDADE", raising=False)
    assert youtube.visibilidade() == "private"
    monkeypatch.setenv("YT_VISIBILIDADE", "PUBLIC")
    assert youtube.visibilidade() == "public"
    monkeypatch.setenv("YT_VISIBILIDADE", "qualquer")
    assert youtube.visibilidade() == "private"


def test_desligado_sem_os_tres_secrets(monkeypatch):
    for k in ("YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN"):
        monkeypatch.setenv(k, "x")
    assert youtube.ligado()
    monkeypatch.setenv("YT_REFRESH_TOKEN", " ")
    assert not youtube.ligado()


def test_credenciais_do_google_somem_do_log():
    msg = util_net.sem_segredo("erro refresh_token=1//0gABC-def&client_secret=GOCSPX-zz token ya29.a0AfH6x-y")
    for s in ("0gABC", "GOCSPX-zz", "a0AfH6x"):
        assert s not in msg


# ------------------------------------------------------------------ envio (rede falsa)
class R:
    def __init__(self, status=200, corpo=None, headers=None, content=b""):
        self.status_code, self._corpo, self.headers, self.content = status, corpo, headers or {}, content

    def json(self):
        return self._corpo


MP4 = b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 64


def _rede(falha_capa=False):
    chamadas = []

    def get(url, **kw):
        chamadas.append(("GET", url))
        return R(content=MP4 if url.endswith(".mp4") else b"\xff\xd8jpeg")

    def post(url, **kw):
        chamadas.append(("POST", url, kw.get("json")))
        if "uploadType=resumable" in url:
            return R(headers={"Location": "https://upload/sessao"})
        if "thumbnails" in url and falha_capa:
            return R(403, {"error": {"errors": [{"reason": "forbidden"}], "message": "no"}})
        return R(corpo={"id": "pi"})

    def put(url, **kw):
        chamadas.append(("PUT", url, len(kw.get("data") or b"")))
        return R(corpo={"id": "VID123"})
    return chamadas, get, post, put


ITEM = {"id": "bf-pix", "url": "https://x/bf-pix.mp4", "capa": "https://x/c.jpg", "titulo": "T", "descricao": "D",
        "comentario": "C", "playlist": "PLC", "origem": "grade"}


def test_envio_completo_privado_com_capa_e_playlist():
    ch, get, post, put = _rede()
    reg = youtube.publicar(ITEM, "tok", "private", get, post, put)
    assert reg["yt"] == "VID123" and reg["capa"] and reg["na_playlist"] and reg["visibilidade"] == "private"
    abrir = [c for c in ch if c[0] == "POST" and "resumable" in c[1]][0]
    assert abrir[2]["status"]["privacyStatus"] == "private"
    assert abrir[2]["status"]["selfDeclaredMadeForKids"] is False
    assert any(c[0] == "PUT" and c[2] == len(MP4) for c in ch)


def test_capa_recusada_nao_derruba_o_envio():
    ch, get, post, put = _rede(falha_capa=True)
    reg = youtube.publicar(ITEM, "tok", "private", get, post, put)
    assert reg["yt"] == "VID123" and not reg["capa"] and reg["na_playlist"]


def test_arquivo_que_nao_e_mp4_nao_sobe():
    ch, get, post, put = _rede()

    def get_html(url, **kw):
        return R(content=b"<html>erro</html>" * 10)
    with pytest.raises(RuntimeError):
        youtube.publicar(ITEM, "tok", "private", get_html, post, put)
    assert not any(c[0] == "PUT" for c in ch)
