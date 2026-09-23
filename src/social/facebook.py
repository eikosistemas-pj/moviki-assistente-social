# -*- coding: utf-8 -*-
"""
Publicacao na Pagina do Facebook.

Dois papeis:
  - no modo normal, e' o ESPELHO do post do Instagram (best-effort);
  - no modo SO_FACEBOOK, e' o canal principal.

TOKEN DE PAGINA (24/08/2026): publicar em /{page-id}/photos exige um
*Page Access Token*, nao o token do usuario do sistema. Com o token errado a
Meta responde:

    (#200) The permission(s) publish_actions are not available.
           It has been deprecated.

...que nao tem nada a ver com o problema real — `publish_actions` morreu em
2018 e nao e' o que estamos pedindo. E' so a mensagem generica da Meta pra
"esse token nao publica em Pagina".

O token de Pagina se obtem a partir do token do usuario do sistema:

    GET /{page-id}?fields=access_token

Como o usuario do sistema `moviki-social` tem acesso total a Pagina, o token
devolvido NAO expira. Por isso o robo faz essa troca sozinho, uma vez por
execucao, e o secret continua sendo o token do usuario do sistema — nada
muda do lado de quem configura.
"""
import os
import time

from .. import config
from .. import util_net as net

# Upload de video "hospedado" da Meta: em vez de mandar os bytes, o robo
# entrega a URL publica no cabecalho file_url e a Meta baixa sozinha.
RUPLOAD = "https://rupload.facebook.com/video-upload"


class Facebook:
    plataforma = "facebook"

    def __init__(self, page_id=None, token=None, post_fn=None, get_fn=None,
                 upload_fn=None, sleep_fn=time.sleep):
        self.page_id = page_id or config.FACEBOOK_PAGE_ID
        self.token = token or config.PAGE_ACCESS_TOKEN
        self._post_fn = post_fn
        self._get_fn = get_fn
        self._upload_fn = upload_fn
        self._sleep = sleep_fn
        self._token_pagina = None

    # ------------------------------------------------------------- token
    def token_pagina(self):
        """Troca o token do usuario do sistema pelo token da Pagina.

        Se a troca falhar, devolve o token original — o secret PODE ja ser um
        token de Pagina, e nesse caso publica direto. Falhar aqui nao pode
        impedir a tentativa.
        """
        if self._token_pagina:
            return self._token_pagina
        try:
            r = self._get(self.page_id, {"fields": "access_token"})
            tok = r.get("access_token")
            if tok:
                # 23/09/2026 (seguranca): o token da Pagina nao e um secret do
                # GitHub, entao o Actions nao o esconde sozinho. Mascara aqui,
                # antes de qualquer print ou erro que possa carrega-lo.
                if os.environ.get("GITHUB_ACTIONS") == "true":
                    print(f"::add-mask::{tok}")
                self._token_pagina = tok
                return tok
            erro = (r.get("error") or {}).get("message")
            if erro:
                print(f"aviso: nao consegui o token da Pagina ({erro}) -> tentando com o token atual")
        except Exception as e:  # noqa: BLE001
            print(f"aviso: nao consegui o token da Pagina ({net.sem_segredo(e)}) -> tentando com o token atual")
        self._token_pagina = self.token
        return self._token_pagina

    # --------------------------------------------------------- baixo nivel
    def _get(self, caminho, params):
        if self._get_fn is not None:
            return self._get_fn(caminho, params)
        params = dict(params, access_token=self.token)
        return net.get(f"{config.GRAPH}/{caminho}", params=params).json()

    def _post(self, caminho, params):
        if self._post_fn is not None:
            return self._post_fn(caminho, params)
        params = dict(params, access_token=self.token_pagina())
        return net.post(f"{config.GRAPH}/{caminho}", params=params).json()

    def _ok(self, r, contexto):
        if not isinstance(r, dict) or "error" in r:
            msg = (r or {}).get("error", {}).get("message") if isinstance(r, dict) else r
            raise RuntimeError(f"facebook {contexto}: {msg}")
        return r

    def _pagina(self):
        if not self.page_id:
            raise RuntimeError("FACEBOOK_PAGE_ID nao configurado")
        return self.page_id

    def _versao(self):
        return config.GRAPH.rstrip("/").rsplit("/", 1)[-1]   # "v25.0"

    def _enviar_video(self, video_id, video_url, upload_url=None):
        """Manda a Meta buscar o video na URL publica (upload hospedado)."""
        destino = upload_url or f"{RUPLOAD}/{self._versao()}/{video_id}"
        cab = {"Authorization": f"OAuth {self.token_pagina()}", "file_url": video_url}
        if self._upload_fn is not None:
            r = self._upload_fn(destino, cab)
        else:
            r = net.post(destino, headers=cab, timeout=180).json()
        if not (isinstance(r, dict) and r.get("success")):
            raise RuntimeError(f"facebook upload de video: {r}")

    # -------------------------------------------------------------- acoes
    def foto(self, image_url, legenda):
        r = self._ok(self._post(f"{self._pagina()}/photos",
                                {"url": image_url, "caption": legenda}), "foto")
        return r.get("post_id") or r.get("id")

    def reel(self, video_url, descricao):
        """Reel na Pagina (22/09/2026). Antes o robo dizia que Reel era
        exclusivo do Instagram e, com SO_FACEBOOK ligado, nao publicava nada
        toda terca e sabado. A Pagina aceita Reel pela API: inicia, a Meta
        baixa o video da URL, publica.  Limite da Meta: 3 a 90 s, 9:16."""
        pag = self._pagina()
        ini = self._ok(self._post(f"{pag}/video_reels", {"upload_phase": "start"}), "reel start")
        video_id = ini.get("video_id")
        if not video_id:
            raise RuntimeError(f"facebook reel start sem video_id: {ini}")
        self._enviar_video(video_id, video_url, ini.get("upload_url"))
        fim = self._ok(self._post(f"{pag}/video_reels", {
            "upload_phase": "finish", "video_id": video_id,
            "video_state": "PUBLISHED", "description": descricao,
        }), "reel finish")
        if not fim.get("success"):
            raise RuntimeError(f"facebook reel finish: {fim}")
        return video_id

    def story_foto(self, image_url):
        """Story de imagem: sobe a foto SEM publicar no feed e vira story."""
        pag = self._pagina()
        foto = self._ok(self._post(f"{pag}/photos", {"url": image_url, "published": "false"}),
                        "story foto (upload)")
        r = self._ok(self._post(f"{pag}/photo_stories", {"photo_id": foto.get("id")}), "story foto")
        return r.get("post_id") or foto.get("id")

    def story_video(self, video_url):
        pag = self._pagina()
        ini = self._ok(self._post(f"{pag}/video_stories", {"upload_phase": "start"}), "story video start")
        video_id = ini.get("video_id")
        if not video_id:
            raise RuntimeError(f"facebook story video start sem video_id: {ini}")
        self._enviar_video(video_id, video_url, ini.get("upload_url"))
        r = self._ok(self._post(f"{pag}/video_stories", {"upload_phase": "finish", "video_id": video_id}),
                     "story video finish")
        return r.get("post_id") or video_id


def espelhar_formato(formato, midia, url, legenda=""):
    """Espelho best-effort de story/reel publicado no Instagram. Nunca levanta."""
    try:
        fb = Facebook()
        if formato == "reel":
            fid = fb.reel(url, legenda)
        elif midia == "video":
            fid = fb.story_video(url)
        else:
            fid = fb.story_foto(url)
        print(f"OK -> espelhado no Facebook ({formato}) | id: {fid}")
        return fid
    except Exception as e:  # noqa: BLE001
        print(f"aviso: nao espelhou {formato} no Facebook (Instagram ja publicou): {e}")
        return None


def espelhar(image_url, legenda):
    """Best-effort. Devolve o id ou None; nunca levanta excecao."""
    try:
        fb_id = Facebook().foto(image_url, legenda)
        print(f"OK -> espelhado no Facebook | id: {fb_id}")
        return fb_id
    except Exception as e:  # noqa: BLE001
        print(f"aviso: nao espelhou no Facebook (Instagram ja publicou): {e}")
        return None
