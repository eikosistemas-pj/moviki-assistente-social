# -*- coding: utf-8 -*-
"""
Rede com repeticao. Toda chamada externa do robo passa por aqui.

Existe porque o GitHub Actions roda sem ninguem olhando: uma falha de rede
transitoria nao pode derrubar a publicacao do dia inteiro.
"""
import re
import time

import requests

# 23/09/2026 (seguranca): o repositorio e PUBLICO e o log do Actions tambem.
# Erro de rede do requests traz a URL inteira — com access_token=... junto.
# Tudo que vira mensagem de erro passa por aqui antes.
_SEGREDOS = re.compile(r"(access_token=|input_token=|client_secret=)[^&\s'\"]+|((?:Bearer|OAuth)\s+)[A-Za-z0-9._\-|]+", re.I)


def sem_segredo(texto):
    return _SEGREDOS.sub(lambda m: (m.group(1) or m.group(2) or "") + "***", str(texto))

TENTATIVAS = 3
ESPERA_BASE = 2  # segundos; dobra a cada tentativa


def _tentar(func, *a, **kw):
    erro = None
    for n in range(TENTATIVAS):
        try:
            r = func(*a, **kw)
            # 5xx e 429 valem nova tentativa; 4xx nao (erro nosso, repetir nao resolve)
            if r.status_code >= 500 or r.status_code == 429:
                raise requests.HTTPError(f"HTTP {r.status_code}")
            return r
        except Exception as e:  # noqa: BLE001 - queremos capturar qualquer falha de rede
            erro = e
            if n < TENTATIVAS - 1:
                time.sleep(ESPERA_BASE * (2 ** n))
    raise RuntimeError(f"rede falhou apos {TENTATIVAS} tentativas: {sem_segredo(erro)}")


def get(url, **kw):
    kw.setdefault("timeout", 30)
    return _tentar(requests.get, url, **kw)


def post(url, **kw):
    kw.setdefault("timeout", 60)
    return _tentar(requests.post, url, **kw)


def put(url, **kw):
    """A API de conteudo do GitHub (criar/atualizar arquivo) so aceita PUT.
    Chamar o mesmo endereco com POST devolve 404 Not Found — erro que parece
    'repo inexistente' e manda a gente cacar permissao que nao e' o problema.
    """
    kw.setdefault("timeout", 60)
    return _tentar(requests.put, url, **kw)
