# -*- coding: utf-8 -*-
"""
Publicador do Instagram (Graph API oficial da Meta).

Fluxo oficial em 2 passos: cria o container de midia, espera o Instagram
baixar a imagem/video, publica. Hashtags vao no PRIMEIRO COMENTARIO — a
legenda fica limpa e o alcance e o mesmo.

Injecao de dependencia (post_fn/sleep_fn) pra testar sem rede.
"""
import time

from .. import config
from .. import util_net as net


class Instagram:
    plataforma = "instagram"

    def __init__(self, account_id=None, token=None, post_fn=None,
                 get_fn=None, sleep_fn=time.sleep):
        self.account_id = account_id or config.IG_ACCOUNT_ID
        self.token = token or config.PAGE_ACCESS_TOKEN
        self._post_fn = post_fn
        self._get_fn = get_fn
        self._sleep = sleep_fn

    # ------------------------------------------------------------- baixo nivel
    def _post(self, caminho, params):
        if self._post_fn is not None:
            return self._post_fn(caminho, params)
        params = dict(params, access_token=self.token)
        return net.post(f"{config.GRAPH}/{caminho}", params=params).json()

    def _get(self, caminho, params):
        if self._get_fn is not None:
            return self._get_fn(caminho, params)
        params = dict(params, access_token=self.token)
        return net.get(f"{config.GRAPH}/{caminho}", params=params).json()

    def _erro(self, resposta, contexto):
        if "error" in resposta:
            raise RuntimeError(f"{contexto}: {resposta['error'].get('message')}")
        return resposta

    # ------------------------------------------------------------- espera
    def _esperar_pronto(self, container_id, tentativas=20, intervalo=6):
        """Video/Reel demora pra processar. Publicar antes da hora falha.

        Consulta status_code ate FINISHED. Foto normalmente ja volta pronta,
        mas a espera vale pra ela tambem (custa 1 chamada).
        """
        for _ in range(tentativas):
            r = self._get(container_id, {"fields": "status_code,status"})
            estado = r.get("status_code")
            if estado == "FINISHED":
                return True
            if estado in ("ERROR", "EXPIRED"):
                raise RuntimeError(f"container {estado}: {r.get('status')}")
            self._sleep(intervalo)
        raise RuntimeError("container nao ficou pronto a tempo")

    # ------------------------------------------------------------- publicacao
    def _publicar(self, container_id, hashtags):
        pub = self._erro(
            self._post(f"{self.account_id}/media_publish", {"creation_id": container_id}),
            "publicar",
        )
        media_id = pub["id"]
        if hashtags:
            # comentario e best-effort: se falhar, o post ja esta no ar
            try:
                self._post(f"{media_id}/comments", {"message": hashtags})
            except Exception as e:  # noqa: BLE001
                print(f"aviso: hashtags no comentario falharam: {e}")
        return media_id

    def foto(self, image_url, legenda, hashtags=""):
        cont = self._erro(
            self._post(f"{self.account_id}/media",
                       {"image_url": image_url, "caption": legenda}),
            "container foto",
        )
        self._esperar_pronto(cont["id"], tentativas=10, intervalo=4)
        return self._publicar(cont["id"], hashtags)

    def reel(self, video_url, legenda, hashtags="", capa_url=None):
        params = {"media_type": "REELS", "video_url": video_url, "caption": legenda}
        if capa_url:
            params["cover_url"] = capa_url
        cont = self._erro(self._post(f"{self.account_id}/media", params), "container reel")
        self._esperar_pronto(cont["id"], tentativas=30, intervalo=8)
        return self._publicar(cont["id"], hashtags)

    def story(self, image_url):
        cont = self._erro(
            self._post(f"{self.account_id}/media",
                       {"image_url": image_url, "media_type": "STORIES"}),
            "container story",
        )
        self._esperar_pronto(cont["id"], tentativas=10, intervalo=4)
        return self._publicar(cont["id"], "")

    # ------------------------------------------------------------- diagnostico
    def validar_token(self):
        """Confere se o token ainda alcanca a conta. Usado pelo workflow
        semanal de verificacao — token de pagina expira e derruba tudo em
        silencio se ninguem olhar."""
        r = self._get(self.account_id, {"fields": "username,followers_count"})
        return self._erro(r, "validar token")
