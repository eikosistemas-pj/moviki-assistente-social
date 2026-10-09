# -*- coding: utf-8 -*-
"""
Publicador do Instagram (Graph API oficial da Meta).

Fluxo oficial em 2 passos: cria o container de midia, espera o Instagram
baixar a imagem/video, publica.

Chamada "Comente LIVE" (08/10/2026): primeira linha de toda legenda de feed e
reel, ver config.CHAMADA_COMENTE e Instagram.com_chamada.

Hashtags (27/09/2026): no FIM DA LEGENDA, no maximo 5 (limite do Instagram
desde dez/2025). Antes iam 10 no primeiro comentario — acima do limite e
comentario automatico, proibido pela regra permanente da conta nova. O robo
nao comenta nada.

Injecao de dependencia (post_fn/sleep_fn) pra testar sem rede.
"""
import json
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
        self.collab_enviado = []

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
    def com_chamada(texto):
        """Poe a chamada "Comente LIVE" na primeira linha (08/10/2026). A
        primeira linha e o que aparece antes do "mais" no feed e por cima do
        reel. Nao repete se a legenda ja pede o comentario."""
        chamada = config.CHAMADA_COMENTE
        if not chamada or re.search(r"\bcomente\s+live\b", texto or "", flags=re.I):
            return texto
        return f"{chamada}\n\n{texto}" if texto else chamada

    @staticmethod
    def legenda_final(legenda, hashtags=""):
        """Legenda + hashtags no fim, respeitando os limites do Instagram:
        no maximo 5 hashtags no total (contando as que ja estiverem no texto)
        e 2.200 caracteres."""
        texto = (legenda or "").strip()
        texto = Instagram.com_chamada(texto)
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

    # ------------------------------------------------------------- collab
    @staticmethod
    def limpar_colaboradores(colaboradores):
        """Ate 3 usernames validos, sem @ e sem repetir."""
        saida = []
        for c in colaboradores or []:
            u = str(c or "").strip().lstrip("@").lower()
            if re.fullmatch(r"[a-z0-9._]{1,30}", u) and u not in saida:
                saida.append(u)
        return saida[:3]

    def _container(self, params, contexto, colaboradores=None):
        """Cria o container. Com colaboradores (post em parceria, 28/09/2026):
        o convite vai para o criador aceitar no app dele. Se a Meta recusar o
        convite (conta privada, @ trocado), o post sai SEM parceria — o
        calendario nunca fura por causa do collab."""
        self.collab_enviado = []
        colab = self.limpar_colaboradores(colaboradores)
        if colab:
            r = self._post(f"{self.account_id}/media",
                           dict(params, collaborators=json.dumps(colab)))
            if isinstance(r, dict) and "error" not in r and r.get("id"):
                self.collab_enviado = colab
                return r
            msg = (r.get("error") or {}).get("message") if isinstance(r, dict) else r
            print(f"aviso: convite de parceria para @{', @'.join(colab)} recusado ({msg}) -> publicando sem parceria")
        return self._erro(self._post(f"{self.account_id}/media", params), contexto)

    def _criar_e_publicar(self, params, contexto, colaboradores, tentativas, intervalo):
        cont = self._container(params, contexto, colaboradores)
        try:
            self._esperar_pronto(cont["id"], tentativas=tentativas, intervalo=intervalo)
            return self._publicar(cont["id"])
        except Exception as e:  # noqa: BLE001
            if not self.collab_enviado:
                raise
            # A Meta pode aceitar o convite no container e recusar so na
            # publicacao. Uma nova tentativa SEM parceria — collab nunca pode
            # derrubar o post nem contar falha para o freio.
            print(f"aviso: publicacao com parceria falhou ({e}) -> tentando sem parceria")
            self.collab_enviado = []
            cont = self._erro(self._post(f"{self.account_id}/media", params), contexto)
            self._esperar_pronto(cont["id"], tentativas=tentativas, intervalo=intervalo)
            return self._publicar(cont["id"])

    def foto(self, image_url, legenda, hashtags="", colaboradores=None):
        return self._criar_e_publicar(
            {"image_url": image_url, "caption": self.legenda_final(legenda, hashtags)},
            "container foto", colaboradores, 10, 4)

    def reel(self, video_url, legenda, hashtags="", capa_url=None, colaboradores=None):
        params = {"media_type": "REELS", "video_url": video_url,
                  "caption": self.legenda_final(legenda, hashtags)}
        if capa_url:
            params["cover_url"] = capa_url
        return self._criar_e_publicar(params, "container reel", colaboradores, 30, 8)

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
