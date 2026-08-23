# -*- coding: utf-8 -*-
"""
Hospedagem publica da arte.

O Instagram so aceita `image_url`/`video_url` publicos: ele BAIXA o arquivo
na hora de criar o container e copia pro CDN dele. Depois disso a URL de
origem pode sumir — por isso a limpeza semanal pode apagar sem medo.

Como: sobe o arquivo pela API de conteudo do GitHub (commit imediato) e
devolve a URL raw. Isso resolve o problema de ordem — a imagem precisa estar
publica ANTES de o post ser criado, e o commit do fim do workflow seria
tarde demais.

Sem fornecedor externo, sem chave nova: usa o GITHUB_TOKEN que o proprio
Actions injeta.
"""
import base64
import time
from datetime import datetime, timezone

from . import config
from . import util_net as net

API = "https://api.github.com"


def _token():
    import os
    return os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN") or ""


def _nome_unico(prefixo, extensao):
    carimbo = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return f"{prefixo}-{carimbo}.{extensao.lstrip('.')}"


def _confirmar_publico(url, tentativas=10, intervalo=3):
    """Espera o raw responder 200. O CDN do GitHub leva alguns segundos."""
    for _ in range(tentativas):
        try:
            r = net.get(url, timeout=15)
            if r.status_code == 200 and len(r.content) > 1000:
                return True
        except Exception:  # noqa: BLE001
            pass
        time.sleep(intervalo)
    return False


def publicar_arquivo(caminho_local, prefixo="post"):
    """Sobe o arquivo pro repo e devolve a URL publica raw."""
    token = _token()
    if not token:
        raise RuntimeError(
            "GITHUB_TOKEN ausente — sem ele nao da pra hospedar a arte. "
            "No workflow, declare `permissions: contents: write`."
        )

    caminho_local = str(caminho_local)
    extensao = caminho_local.rsplit(".", 1)[-1]
    nome = _nome_unico(prefixo, extensao)
    destino = f"publicado/{nome}"

    with open(caminho_local, "rb") as f:
        conteudo = base64.b64encode(f.read()).decode()

    r = net.post(
        f"{API}/repos/{config.GH_REPO}/contents/{destino}",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        json={
            "message": f"arte: {nome}",
            "content": conteudo,
            "branch": config.GH_BRANCH,
        },
    )
    dados = r.json()
    if r.status_code not in (200, 201):
        raise RuntimeError(f"upload falhou ({r.status_code}): {dados.get('message')}")

    url = f"{config.RAW_BASE}/{nome}"
    if not _confirmar_publico(url):
        raise RuntimeError(f"arte subiu mas a URL nao ficou publica a tempo: {url}")
    return url


def listar_publicados():
    """Lista os arquivos em publicado/ com a data no nome (pra limpeza)."""
    token = _token()
    r = net.get(
        f"{API}/repos/{config.GH_REPO}/contents/publicado",
        headers={"Authorization": f"Bearer {token}",
                 "Accept": "application/vnd.github+json"},
    )
    if r.status_code == 404:
        return []
    dados = r.json()
    return dados if isinstance(dados, list) else []


def apagar(caminho, sha):
    import requests
    token = _token()
    r = requests.delete(
        f"{API}/repos/{config.GH_REPO}/contents/{caminho}",
        headers={"Authorization": f"Bearer {token}",
                 "Accept": "application/vnd.github+json",
                 "X-GitHub-Api-Version": "2022-11-28"},
        json={"message": f"limpeza: {caminho}", "sha": sha,
              "branch": config.GH_BRANCH},
        timeout=30,
    )
    return r.status_code in (200, 201)
