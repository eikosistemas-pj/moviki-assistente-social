# -*- coding: utf-8 -*-
"""
Leitura da base real do Moviki (Firestore) pela REST API.

Por que REST e nao Admin SDK: as regras do projeto ja dao
`allow read: if true` em /negocios, entao uma chamada NAO autenticada le
normalmente. Isso evita colocar chave de service account (escrita total,
inclusive nas colecoes de dinheiro) num GitHub Secret.

Este modulo SO LE. Nao existe funcao de escrita aqui de proposito.
"""
from . import config
from . import util_net as net


# --------------------------------------------------------------- decodificacao
def _valor(v):
    """Converte um valor tipado do Firestore REST em valor Python."""
    if not isinstance(v, dict):
        return v
    if "stringValue" in v:
        return v["stringValue"]
    if "booleanValue" in v:
        return v["booleanValue"]
    if "integerValue" in v:
        return int(v["integerValue"])
    if "doubleValue" in v:
        return float(v["doubleValue"])
    if "timestampValue" in v:
        return v["timestampValue"]
    if "nullValue" in v:
        return None
    if "arrayValue" in v:
        return [_valor(x) for x in v["arrayValue"].get("values", [])]
    if "mapValue" in v:
        return {k: _valor(x) for k, x in v["mapValue"].get("fields", {}).items()}
    return None


def _doc(d):
    """Documento REST -> dict simples, com o id no campo 'uid'."""
    campos = {k: _valor(v) for k, v in (d.get("fields") or {}).items()}
    campos["uid"] = (d.get("name") or "").rsplit("/", 1)[-1]
    return campos


# --------------------------------------------------------------- consultas
def listar_negocios(limite_paginas=20):
    """Le TODOS os documentos de /negocios, paginando.

    Devolve lista de dicts. Sem filtro aqui de proposito: o filtro de
    autorizacao acontece em `elegiveis()`, que e testavel sem rede.
    """
    if not config.FIREBASE_PROJECT_ID:
        raise RuntimeError("FIREBASE_PROJECT_ID nao configurado")

    saida, token = [], None
    for _ in range(limite_paginas):
        params = {"pageSize": 300}
        if config.FIREBASE_API_KEY:
            params["key"] = config.FIREBASE_API_KEY
        if token:
            params["pageToken"] = token
        r = net.get(f"{config.FIRESTORE_BASE}/negocios", params=params)
        dados = r.json()
        if "error" in dados:
            raise RuntimeError(f"Firestore: {dados['error'].get('message')}")
        saida.extend(_doc(d) for d in dados.get("documents", []))
        token = dados.get("nextPageToken")
        if not token:
            break
    return saida


# --------------------------------------------------------------- elegibilidade
def elegiveis(negocios):
    """Filtra quem pode aparecer num post de vitrine.

    Regras (todas obrigatorias, e nesta ordem):
      1. autorizaDivulgacao == True  -> OPT-IN EXPLICITO. Sem isso, fora.
         Divulgar negocio de terceiro sem consentimento e problema de LGPD
         e de confianca; o campo e a prova do aceite.
      2. tem nome
      3. tem slug (senao o post nao tem link pra onde mandar a pessoa)
      4. tem alguma imagem propria (markerLogo ou fotos) OU segmento
         definido — senao nao da pra montar uma arte que preste.
    """
    saida = []
    for n in negocios or []:
        if n.get("autorizaDivulgacao") is not True:
            continue
        if not (n.get("nome") or "").strip():
            continue
        if not (n.get("slug") or "").strip():
            continue
        tem_visual = bool(n.get("markerLogo")) or bool(n.get("fotos"))
        if not (tem_visual or n.get("segmento")):
            continue
        saida.append(n)
    return saida


def link_publico(negocio):
    slug = (negocio.get("slug") or "").strip()
    return f"{config.SITE}/{slug}" if slug else config.SITE
