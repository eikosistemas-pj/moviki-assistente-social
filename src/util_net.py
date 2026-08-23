# -*- coding: utf-8 -*-
"""
Rede com repeticao. Toda chamada externa do robo passa por aqui.

Existe porque o GitHub Actions roda sem ninguem olhando: uma falha de rede
transitoria nao pode derrubar a publicacao do dia inteiro.
"""
import time

import requests

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
    raise RuntimeError(f"rede falhou apos {TENTATIVAS} tentativas: {erro}")


def get(url, **kw):
    kw.setdefault("timeout", 30)
    return _tentar(requests.get, url, **kw)


def post(url, **kw):
    kw.setdefault("timeout", 60)
    return _tentar(requests.post, url, **kw)
