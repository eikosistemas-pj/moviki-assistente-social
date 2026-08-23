# -*- coding: utf-8 -*-
"""
Leitura das pautas institucionais (conteudo/pautas.md).

Substitui o RAG do agente original DE PROPOSITO. La o vault tinha centenas
de notas pessoais e a busca semantica se pagava. Aqui a base de conhecimento
sao ~12 pautas curadas: ChromaDB seria ~200MB de dependencia instalados a
cada execucao do Actions pra escolher entre 12 itens. Leitura direta resolve
melhor, mais rapido e sem custo.

Editar pautas.md muda o que o robo fala. Nao precisa tocar em codigo.
"""
import re

from . import config

CAMPOS = ("tipo", "etiqueta", "titulo", "subtitulo", "angulo")

COMENTARIO = re.compile(r"<!--.*?-->", re.S)


def sem_comentarios(texto):
    """Remove blocos <!-- ... --> antes de parsear.

    Existe porque bloco comentado em markdown NAO pode virar post. Sem
    isso, um modelo deixado comentado no arquivo era lido como pauta real
    e ia ao ar — pego em teste de dry-run.
    """
    return COMENTARIO.sub("", texto or "")


def carregar(caminho=None):
    """Le pautas.md e devolve lista de dicts."""
    caminho = caminho or (config.CONTEUDO_DIR / "pautas.md")
    if not caminho.exists():
        return []

    texto = sem_comentarios(caminho.read_text(encoding="utf-8"))
    # tudo depois do separador de abertura; blocos comecam em '## '
    partes = re.split(r"^##\s+", texto, flags=re.M)[1:]

    pautas = []
    for bloco in partes:
        linhas = bloco.strip().splitlines()
        if not linhas:
            continue
        pauta = {"id": linhas[0].strip()}
        for linha in linhas[1:]:
            m = re.match(r"^\s*(\w+)\s*:\s*(.+)$", linha)
            if m and m.group(1).lower() in CAMPOS:
                pauta[m.group(1).lower()] = m.group(2).strip()
        if pauta.get("titulo"):
            pauta.setdefault("tipo", "educativo")
            pauta.setdefault("etiqueta", "")
            pauta.setdefault("subtitulo", "")
            pauta.setdefault("angulo", pauta["titulo"])
            pautas.append(pauta)
    return pautas


def por_tipo(pautas, tipo):
    return [p for p in pautas if p.get("tipo") == tipo]


def hashtags(tipo="educativo"):
    """Blocos fixos de hashtag. Vao no primeiro comentario, nunca na legenda."""
    base = "#moviki #negocioitinerante #foodtruck #carrinhodelanche #feiralivre"
    extras = {
        "educativo": "#empreendedorismo #negociodrua #vendasderua #trabalhoautonomo",
        "conversao": "#empreendedor #donodenegocio #comerciolocal #microempreendedor",
        "parceiro": "#programadeparceiros #indicacao #rendaporindicacao #marketingdeindicacao",
        "bastidor": "#comerciolocal #ruas #trabalhador #brasil",
        "vitrine": "#comerciolocal #apoieonegociolocal #ondecomer #pertodemim",
    }
    return f"{base} {extras.get(tipo, extras['educativo'])}"
