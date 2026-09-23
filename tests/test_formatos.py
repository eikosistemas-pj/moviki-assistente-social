# -*- coding: utf-8 -*-
"""
Story e Reel na Pagina do Facebook e story em video no Instagram
(22/09/2026), com Graph API falsa. Confere a SEQUENCIA de chamadas — a
integracao real so se prova na primeira publicacao de verdade.
"""
from src.social.facebook import Facebook
from src.social.instagram import Instagram


class GraphFb:
    def __init__(self):
        self.chamadas, self.uploads = [], []

    def post(self, caminho, params):
        self.chamadas.append((caminho, dict(params)))
        fase = params.get("upload_phase")
        if caminho.endswith("/video_reels") and fase == "start":
            return {"video_id": "v1", "upload_url": "https://rupload.facebook.com/video-upload/v25.0/v1"}
        if caminho.endswith("/video_reels") and fase == "finish":
            return {"success": True}
        if caminho.endswith("/video_stories") and fase == "start":
            return {"video_id": "v2"}
        if caminho.endswith("/video_stories") and fase == "finish":
            return {"success": True, "post_id": "p2"}
        if caminho.endswith("/photos"):
            return {"id": "foto9"}
        if caminho.endswith("/photo_stories"):
            return {"success": True, "post_id": "p9"}
        return {"error": {"message": "rota inesperada"}}

    def upload(self, destino, cab):
        self.uploads.append((destino, cab))
        return {"success": True}


def _fb(g):
    return Facebook(page_id="PAG", token="t", post_fn=g.post, get_fn=lambda c, p: {"access_token": "tp"},
                    upload_fn=g.upload, sleep_fn=lambda s: None)


def test_reel_no_facebook_inicia_manda_url_e_publica():
    g = GraphFb()
    assert _fb(g).reel("https://x/v.mp4", "legenda") == "v1"
    assert [c[1].get("upload_phase") for c in g.chamadas] == ["start", "finish"]
    assert g.chamadas[1][1]["video_state"] == "PUBLISHED"
    assert g.chamadas[1][1]["description"] == "legenda"
    destino, cab = g.uploads[0]
    assert cab["file_url"] == "https://x/v.mp4" and cab["Authorization"] == "OAuth tp"


def test_story_de_foto_sobe_sem_publicar_no_feed():
    g = GraphFb()
    assert _fb(g).story_foto("https://x/s.jpg") == "p9"
    assert g.chamadas[0] == ("PAG/photos", {"url": "https://x/s.jpg", "published": "false"})
    assert g.chamadas[1] == ("PAG/photo_stories", {"photo_id": "foto9"})


def test_story_de_video_usa_upload_hospedado():
    g = GraphFb()
    assert _fb(g).story_video("https://x/s.mp4") == "p2"
    assert g.uploads[0][0].endswith("/v25.0/v2")


def test_story_video_no_instagram():
    feitas = []

    def post(c, p):
        feitas.append((c, p))
        return {"id": "cont"} if c.endswith("/media") else {"id": "m1"}

    ig = Instagram(account_id="1", token="t", post_fn=post,
                   get_fn=lambda c, p: {"status_code": "FINISHED"}, sleep_fn=lambda s: None)
    assert ig.story_video("https://x/s.mp4") == "m1"
    assert feitas[0][1] == {"video_url": "https://x/s.mp4", "media_type": "STORIES"}
