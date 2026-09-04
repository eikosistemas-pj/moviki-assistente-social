# -*- coding: utf-8 -*-
"""
Leitura da base real do Moviki.

ATE 04/09/2026 este modulo falava direto com a REST API do Firestore usando a
API key publica do app web. Isso morreu com o App Check: para o Firebase,
chamada com a chave publica e chamada de CLIENTE, e cliente sem token de App
Check e recusado assim que o enforcement e ligado. O robo pararia de publicar
e o erro so apareceria dentro de um workflow que ninguem le todo dia.

AGORA: o robo le a vitrine pronta em `config.VITRINE_URL`
(moviki.com.br/api/vitrine). Quem fala com o Firestore e o servidor da Vercel,
com conta de servico SOMENTE LEITURA — chamada de conta de servico passa por
IAM, nao pela chave publica, entao o App Check nao se aplica a ela.

O que mudou na pratica, alem de destravar o enforcement:
  * a lista ja chega FILTRADA pelo opt-in (autorizaDivulgacao) no servidor.
    Quem nao autorizou divulgacao nao sai mais do banco.
  * chega com um conjunto FECHADO de campos: nome, slug, segmento, cor, lat,
    lng, markerLogo, fotos, uid. Nada alem disso.
  * o robo deixou de paginar a base inteira a cada rodada.

O nome do modulo continua `firestore` de proposito: e quem le a base, e quem
importa nao precisa saber por onde. `elegiveis()` continua aqui, sem rede e
com os mesmos testes — ela agora e a SEGUNDA barreira sobre o mesmo filtro,
que e como se defende opt-in.

Este modulo SO LE. Nao existe funcao de escrita aqui de proposito.
"""
from . import config
from . import util_net as net

# Total de negocios na base (todos, nao so os elegiveis) da ultima chamada de
# `listar_negocios`. Fica aqui porque o endpoint devolve o numero de graca, por
# agregacao COUNT, e o diagnostico do robo usa isso para dizer quanto da base
# ja autorizou divulgacao.
ULTIMA_BASE = None


def listar_negocios(limite_paginas=None):
    """Le a vitrine publica e devolve a lista de negocios que autorizaram
    divulgacao.

    O parametro `limite_paginas` so continua na assinatura para nao quebrar
    quem chama; nao ha mais paginacao — o endpoint devolve tudo de uma vez,
    com teto proprio.

    Falha ALTO de proposito: sem base, publicar institucional caladinho todo
    dia seria pior do que quebrar o workflow e avisar.
    """
    global ULTIMA_BASE

    url = (config.VITRINE_URL or "").strip()
    if not url:
        raise RuntimeError("VITRINE_URL nao configurada")

    cabecalhos = {"Accept": "application/json"}
    if config.VITRINE_SECRET:
        cabecalhos["Authorization"] = f"Bearer {config.VITRINE_SECRET}"

    r = net.get(url, headers=cabecalhos)

    # 4xx nao e repetido pelo util_net (erro nosso), entao chega aqui inteiro.
    if r.status_code == 401:
        raise RuntimeError("vitrine: 401 — VITRINE_SECRET ausente ou errado")
    if r.status_code != 200:
        raise RuntimeError(f"vitrine: HTTP {r.status_code}")

    try:
        dados = r.json()
    except Exception as e:  # noqa: BLE001
        raise RuntimeError(f"vitrine: resposta nao e JSON ({e})")

    if not isinstance(dados, dict) or not isinstance(dados.get("negocios"), list):
        raise RuntimeError("vitrine: formato inesperado")

    ULTIMA_BASE = dados.get("base")

    if dados.get("truncado"):
        print("AVISO: a vitrine bateu o teto do endpoint — subir TETO em api/vitrine.js")

    return [n for n in dados["negocios"] if isinstance(n, dict)]


def total_base():
    """Quantos negocios existem na base inteira (None se ainda nao leu)."""
    return ULTIMA_BASE


# --------------------------------------------------------------- elegibilidade
def elegiveis(negocios):
    """Filtra quem pode aparecer num post de vitrine.

    O endpoint ja aplica o filtro de opt-in no servidor. Esta funcao continua
    valendo como segunda barreira: e ela que tem teste, e opt-in e o tipo de
    coisa que se confere duas vezes.

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
