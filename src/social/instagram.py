# -*- coding: utf-8 -*-
"""
Publicador do Instagram (Graph API oficial da Meta).

Fluxo oficial em 2 passos: cria o container de midia, espera o Instagram
baixar a imagem/video, publica.

Corrida da Meta (15/10/2026, marca 2026-10-15-republicar): se o media_publish
responder "Media ID is not available" com o container pronto, o robo espera,
confere o container e tenta UMA vez mais antes de cair no plano B. Ver
Instagram._publicar.

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
from datetime import datetime, timedelta, timezone

from .. import config
from .. import util_net as net

# Erro de corrida da Meta no media_publish (12/10/2026): container FINISHED e
# mesmo assim "Media ID is not available". Uma segunda tentativa resolve.
_CORRIDA = re.compile(r"media id is not available|not ready to be published|media is not ready", re.I)
ESPERA_REPUBLICAR = 20  # segundos antes de conferir o container de novo


class Instagram:
    plataforma = "instagram"

    def __init__(self, account_id=None, token=None, post_fn=None,
                 get_fn=None, sleep_fn=time.sleep, ia=False):
        # 17/10/2026: rotulo "Informacoes de IA" da Meta (parametro
        # is_ai_generated, changelog de 22/06/2026, todas as versoes). Liga em
        # todo conteudo da casa feito com IA (pessoas e cenas realistas);
        # nunca em peca de criador real. Desliga geral com ROTULO_IA=0.
        self.ia = bool(ia) and config.ROTULO_IA
        self.account_id = account_id or config.IG_ACCOUNT_ID
        self.token = token or config.PAGE_ACCESS_TOKEN
        self._post_fn = post_fn
        self._get_fn = get_fn
        self._sleep = sleep_fn
        self.collab_enviado = []

    # ------------------------------------------------------------- baixo nivel
    def _post(self, caminho, params):
        rotular = (self.ia and str(caminho).endswith("/media")
                   and any(k in params for k in ("image_url", "video_url", "media_type")))
        if rotular:
            params = dict(params, is_ai_generated="true")
        r = self._post_cru(caminho, params)
        if rotular and isinstance(r, dict) and "is_ai_generated" in str(r.get("error") or ""):
            # A Meta recusou o rotulo: o post nao pode cair por causa dele.
            print("aviso: a Meta recusou o rotulo de IA -> publicando sem ele")
            params = {k: v for k, v in params.items() if k != "is_ai_generated"}
            r = self._post_cru(caminho, params)
        return r

    def _post_cru(self, caminho, params):
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
    @staticmethod
    def _corrida_da_meta(resposta):
        """True so para o erro de corrida da Meta: o container ja disse
        FINISHED, mas o media_publish responde "Media ID is not available"
        (codigo 9007 / subcodigo 2207027). Nao e recusa de conteudo nem de
        conta — e a Meta atrasada do lado dela (incidente de 12/10/2026)."""
        if not isinstance(resposta, dict) or "error" not in resposta:
            return False
        err = resposta.get("error") or {}
        return (err.get("code") == 9007 or err.get("error_subcode") == 2207027
                or bool(_CORRIDA.search(str(err.get("message") or ""))))

    def _achar_publicado(self, lista, desde):
        """O container ja esta PUBLISHED: devolve o id do post que acabou de
        entrar na conta (feed/reel em /media, story em /stories)."""
        r = self._get(f"{self.account_id}/{lista}", {"fields": "id,timestamp", "limit": 5})
        for item in (r.get("data") or []) if isinstance(r, dict) else []:
            try:
                quando = datetime.strptime(item.get("timestamp") or "", "%Y-%m-%dT%H:%M:%S%z")
            except ValueError:
                continue
            if item.get("id") and quando >= desde - timedelta(minutes=2):
                return item["id"]
        return None

    def _publicar(self, container_id, lista="media"):
        """media_publish. Desde 15/10/2026 (marca 2026-10-15-republicar):
        no erro de corrida da Meta, espera, confere o container e tenta
        publicar UMA vez mais — nunca em laco (regra do freio: conta nova nao
        insiste depois de recusa). Container ja PUBLISHED = o post entrou;
        pega o id em vez de publicar de novo (sem post duplicado). Qualquer
        outro erro estoura como antes e cai no plano B."""
        desde = datetime.now(timezone.utc)
        caminho = f"{self.account_id}/media_publish"
        r = self._post(caminho, {"creation_id": container_id})
        if self._corrida_da_meta(r):
            print(f"aviso: Meta respondeu antes da hora ({(r['error'] or {}).get('message')}) "
                  f"-> esperando {ESPERA_REPUBLICAR}s e conferindo o container")
            self._sleep(ESPERA_REPUBLICAR)
            estado = (self._get(container_id, {"fields": "status_code"}) or {}).get("status_code")
            if estado == "PUBLISHED":
                mid = self._achar_publicado(lista, desde)
                if mid:
                    print("aviso: o post ja tinha entrado no Instagram -> sem publicar de novo")
                    return mid
                raise RuntimeError("publicar: a Meta diz que publicou, mas o post nao apareceu na conta")
            if estado == "FINISHED":
                print("aviso: container pronto -> segunda e ultima tentativa de publicar")
                r = self._post(caminho, {"creation_id": container_id})
        pub = self._erro(r, "publicar")
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
        return self._publicar(cont["id"], lista="stories")

    def story_video(self, video_url):
        """Story em video (22/09/2026). Mesmo fluxo do reel, sem legenda."""
        cont = self._erro(
            self._post(f"{self.account_id}/media",
                       {"video_url": video_url, "media_type": "STORIES"}),
            "container story video",
        )
        self._esperar_pronto(cont["id"], tentativas=30, intervalo=8)
        return self._publicar(cont["id"], lista="stories")

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
