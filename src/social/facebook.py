# -*- coding: utf-8 -*-
"""
Espelho no Facebook (Pagina). Mesma arte, mesma legenda.

O Instagram e prioridade: se o Facebook falhar, o post do Instagram ja esta
no ar e o robo so registra aviso. Nunca derruba o ciclo por causa do espelho.
"""
from .. import config
from .. import util_net as net


class Facebook:
    plataforma = "facebook"

    def __init__(self, page_id=None, token=None, post_fn=None):
        self.page_id = page_id or config.FACEBOOK_PAGE_ID
        self.token = token or config.PAGE_ACCESS_TOKEN
        self._post_fn = post_fn

    def _post(self, caminho, params):
        if self._post_fn is not None:
            return self._post_fn(caminho, params)
        params = dict(params, access_token=self.token)
        return net.post(f"{config.GRAPH}/{caminho}", params=params).json()

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
