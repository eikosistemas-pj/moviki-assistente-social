# -*- coding: utf-8 -*-
"""
Chamada do Messenger na legenda do Facebook (12/11/2026).

A legenda da Pagina saia sem chamada nenhuma: o "Comente LIVE" e so do
Instagram. Agora toda foto e todo reel da Pagina fecham com o link do
Messenger que abre o Funil LIVE do ManyChat.
"""
from src import compliance, config
from src.social.facebook import Facebook


class Graph:
    def __init__(self):
        self.chamadas = []

    def post(self, caminho, params):
        self.chamadas.append((caminho, dict(params)))
        fase = params.get("upload_phase")
        if caminho.endswith("/video_reels") and fase == "start":
            return {"video_id": "v1", "upload_url": "https://rupload.facebook.com/video-upload/v25.0/v1"}
        if caminho.endswith("/video_reels") and fase == "finish":
            return {"success": True}
        if caminho.endswith("/photos"):
            return {"id": "foto1", "post_id": "post1"}
        return {"error": {"message": "rota inesperada"}}


def _fb(g):
    return Facebook(page_id="PAG", token="t", post_fn=g.post, get_fn=lambda c, p: {"access_token": "tp"},
                    upload_fn=lambda d, c: {"success": True}, sleep_fn=lambda s: None)


def test_chamada_vai_no_fim_e_o_gancho_continua_na_primeira_linha():
    leg = Facebook.com_chamada("Gancho do post.\n\nTexto.")
    assert leg.splitlines()[0] == "Gancho do post."
    assert leg.splitlines()[-1] == config.CHAMADA_FACEBOOK


def test_chamada_e_link_do_messenger_e_nao_pede_comentario():
    assert "https://m.me/" in config.CHAMADA_FACEBOOK and "ref=live" in config.CHAMADA_FACEBOOK
    assert "comente" not in config.CHAMADA_FACEBOOK.lower()
    assert compliance.violacoes(config.CHAMADA_FACEBOOK) == []


def test_nao_repete_quando_a_legenda_ja_tem_link_do_messenger():
    leg = "Texto. Fala com a gente: https://m.me/moviki.oficial?ref=live"
    assert Facebook.com_chamada(leg) == leg


def test_legenda_vazia_vira_so_a_chamada():
    assert Facebook.com_chamada("") == config.CHAMADA_FACEBOOK
    assert Facebook.com_chamada(None) == config.CHAMADA_FACEBOOK


def test_desligada_nao_mexe_na_legenda(monkeypatch):
    monkeypatch.setattr(config, "CHAMADA_FACEBOOK", "")
    assert Facebook.com_chamada("Texto.") == "Texto."


def test_foto_publica_com_a_chamada():
    g = Graph()
    assert _fb(g).foto("https://x/a.jpg", "Legenda da foto.") == "post1"
    assert g.chamadas[0][1]["caption"] == f"Legenda da foto.\n\n{config.CHAMADA_FACEBOOK}"


def test_reel_publica_com_a_chamada():
    g = Graph()
    assert _fb(g).reel("https://x/v.mp4", "Legenda do reel.") == "v1"
    assert g.chamadas[1][1]["description"] == f"Legenda do reel.\n\n{config.CHAMADA_FACEBOOK}"
