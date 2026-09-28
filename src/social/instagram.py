# -*- coding: utf-8 -*-
"""
Publicador do Instagram (Graph API oficial da Meta).

Fluxo oficial em 2 passos: cria o container de midia, espera o Instagram
baixar a imagem/video, publica.

Hashtags (27/09/2026): no FIM DA LEGENDA, no maximo 5 (limite do Instagram
desde dez/2025). Antes iam 10 no primeiro comentario — acima do limite e
comentario automatico, proibido pela regra permanente da conta nova. O robo
nao comenta nada.

Injecao de dependencia (post_fn/sleep_fn) pra testar sem rede.
"""
import re
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
    def _publicar(self, container_id):
        pub = self._erro(
            self._post(f"{self.account_id}/media_publish", {"creation_id": container_id}),
            "publicar",
        )
        return pub["id"]

    @staticmethod
    def legenda_final(legenda, hashtags=""):
        """Legenda + hashtags no fim, respeitando os limites do Instagram:
        no maximo 5 hashtags no total (contando as que ja estiverem no texto)
        e 2.200 caracteres."""
        texto = (legenda or "").strip()
        ja = re.findall(r"#\w+", texto)
        vaga = max(0, config.HASHTAGS_MAX - len(ja))
        novas = [t for t in (hashtags or "").split() if t.startswith("#") and t not in ja][:vaga]
        rodape = " ".join(novas)
        teto = 2200 - (len(rodape) + 2 if rodape else 0)
        if len(texto) > teto:
            texto = texto[: teto - 1].rstrip() + "…"
        if rodape:
            texto = f"{texto}\n\n{rodape}" if texto else rodape
        return texto

    def foto(self, image_url, legenda, hashtags=""):
        cont = self._erro(
            self._post(f"{self.account_id}/media",
                       {"image_url": image_url, "caption": self.legenda_final(legenda, hashtags)}),
            "container foto",
        )
        self._esperar_pronto(cont["id"], tentativas=10, intervalo=4)
        return self._publicar(cont["id"])

    def reel(self, video_url, legenda, hashtags="", capa_url=None):
        params = {"media_type": "REELS", "video_url": video_url,
                  "caption": self.legenda_final(legenda, hashtags)}
        if capa_url:
            params["cover_url"] = capa_url
        cont = self._erro(self._post(f"{self.account_id}/media", params), "container reel")
        self._esperar_pronto(cont["id"], tentativas=30, intervalo=8)
        return self._publicar(cont["id"])

    def story(self, image_url):
        cont = self._erro(
            self._post(f"{self.account_id}/media",
                       {"image_url": image_url, "media_type": "STORIES"}),
            "container story",
        )
        self._esperar_pronto(cont["id"], tentativas=10, intervalo=4)
        return self._publicar(cont["id"])

    def story_video(self, video_url):
        """Story em video (22/09/2026). Mesmo fluxo do reel, sem legenda."""
        cont = self._erro(
            self._post(f"{self.account_id}/media",
                       {"video_url": video_url, "media_type": "STORIES"}),
            "container story video",
        )
        self._esperar_pronto(cont["id"], tentativas=30, intervalo=8)
        return self._publicar(cont["id"])

    # ------------------------------------------------------------- diagnostico
    def cota_publicacao(self):
        """Quantos posts a conta ja publicou nas ultimas 24 h pela API e o teto.
        So responde se o token tiver instagram_content_publish — e por isso
        serve de prova de que o robo CONSEGUE publicar, nao so ler."""
        r = self._erro(
            self._get(f"{self.account_id}/content_publishing_limit",
                      {"fields": "config,quota_usage"}),
            "cota de publicacao",
        )
        d = (r.get("data") or [{}])[0]
        return int(d.get("quota_usage") or 0), int((d.get("config") or {}).get("quota_total") or 0)

    def validar_token(self):
        """Confere se o token ainda alcanca a conta. Usado pelo workflow
        semanal de verificacao — token de pagina expira e derruba tudo em
        silencio se ninguem olhar."""
        r = self._get(self.account_id, {"fields": "username,followers_count"})
        return self._erro(r, "validar token")
