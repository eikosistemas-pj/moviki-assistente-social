# -*- coding: utf-8 -*-
"""
Memoria do robo entre execucoes.

Fica em arquivos texto em estado/, commitados de volta pelo workflow.

DECISAO CONSCIENTE: nao guardamos isso no Firestore. Escrever no Firestore
exigiria credencial de escrita (service account = escrita total, inclusive
nas colecoes de dinheiro) ou uma regra publica de escrita (qualquer um
corrompe). Arquivo no repo nao cria nenhuma dessas brechas.

Concorrencia: os workflows usam `concurrency: moviki-assistente-social-estado` pra
nunca rodarem dois ao mesmo tempo, e dao `git pull --rebase` antes do push.
"""
import json
from datetime import datetime, timezone

from . import config


def _arquivo(nome):
    config.ESTADO_DIR.mkdir(parents=True, exist_ok=True)
    return config.ESTADO_DIR / nome


def ler_lista(nome):
    p = _arquivo(nome)
    if not p.exists():
        return []
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return []


def gravar_lista(nome, dados):
    _arquivo(nome).write_text(
        json.dumps(dados, ensure_ascii=False, indent=1), encoding="utf-8"
    )


# ------------------------------------------------------------- anti-repeticao
def recentes(formato):
    """Uids/ids ja usados recentemente neste formato."""
    return ler_lista(f"recentes_{formato}.json")


def marcar_usado(formato, chave, janela=None):
    janela = janela or config.JANELA_ANTI_REPETICAO
    lista = recentes(formato)
    lista = [c for c in lista if c != chave]
    lista.insert(0, chave)
    gravar_lista(f"recentes_{formato}.json", lista[:janela])


def escolher(formato, candidatos, chave=lambda x: x):
    """Escolhe o primeiro candidato que nao esta na janela recente.

    Se TODOS ja foram usados, zera a janela e pega o mais antigo — o robo
    nunca fica sem post por falta de opcao nova.
    """
    if not candidatos:
        return None
    usados = recentes(formato)
    for c in candidatos:
        if chave(c) not in usados:
            return c
    ordenados = sorted(candidatos, key=lambda c: usados.index(chave(c))
                       if chave(c) in usados else -1, reverse=True)
    return ordenados[0]


# ------------------------------------------------------------- historico
def registrar(formato, descricao, media_id, extra=None):
    linha = {
        "quando": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "formato": formato,
        "descricao": descricao,
        "media_id": media_id,
    }
    if extra:
        linha.update(extra)
    hist = ler_lista("historico.json")
    hist.insert(0, linha)
    gravar_lista("historico.json", hist[:500])
    return linha
