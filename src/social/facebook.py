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
from .. import config
from .. import util_net as net


class Facebook:
    plataforma = "facebook"

    def __init__(self, page_id=None, token=None, post_fn=None, get_fn=None):
        self.page_id = page_id or config.FACEBOOK_PAGE_ID
        self.token = token or config.PAGE_ACCESS_TOKEN
        self._post_fn = post_fn
        self._get_fn = get_fn
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
                self._token_pagina = tok
                return tok
            erro = (r.get("error") or {}).get("message")
            if erro:
                print(f"aviso: nao consegui o token da Pagina ({erro}) -> tentando com o token atual")
        except Exception as e:  # noqa: BLE001
            print(f"aviso: nao consegui o token da Pagina ({e}) -> tentando com o token atual")
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

    # -------------------------------------------------------------- acoes
    def foto(self, image_url, legenda):
        if not self.page_id:
            raise RuntimeError("FACEBOOK_PAGE_ID nao configurado")
        r = self._post(f"{self.page_id}/photos", {"url": image_url, "caption": legenda})
        if "error" in r:
            raise RuntimeError(f"facebook: {r['error'].get('message')}")
        return r.get("post_id") or r.get("id")


def espelhar(image_url, legenda):
    """Best-effort. Devolve o id ou None; nunca levanta excecao."""
    try:
        fb_id = Facebook().foto(image_url, legenda)
        print(f"OK -> espelhado no Facebook | id: {fb_id}")
        return fb_id
    except Exception as e:  # noqa: BLE001
        print(f"aviso: nao espelhou no Facebook (Instagram ja publicou): {e}")
        return None
