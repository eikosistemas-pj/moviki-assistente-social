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


# Hashtags por ramo (27/09/2026). O material hoje cobre farmacia, shopping,
# pet, moda... e todo post saia com #foodtruck #carrinhodelanche — hashtag
# errada entrega o post pra quem nao e publico. Cada ramo tem 4 proprias;
# a 5a e sempre #moviki (limite do Instagram: 5 por post).
HASHTAGS_RAMO = {
    "alimentacao": "#delivery #lanchonete #restaurante #comerciolocal",
    "artesanato": "#artesanato #feitoamao #empreendedora #comerciolocal",
    "beleza": "#salaodebeleza #esteticista #manicure #empreendedora",
    "automotivo": "#oficinamecanica #lavajato #motopecas #comerciolocal",
    "eletronicos": "#assistenciatecnica #celular #acessorios #comerciolocal",
    "farmacia": "#farmacia #drogaria #saude #comerciolocal",
    "feira": "#foodtruck #feiralivre #vendasderua #delivery",
    "eventos": "#fotografo #eventos #festa #empreendedor",
    "infantil": "#lojainfantil #brinquedos #modainfantil #comerciolocal",
    "joalheria": "#joalheria #joias #semijoias #acessorios",
    "otica": "#otica #oculos #oculosdegrau #oculosdesol",
    "shopping": "#lojista #varejo #liveshop #vendasonline",
    "moda": "#lojaderoupa #modafeminina #lojista #vendasonline",
    "naturais": "#produtosnaturais #vidasaudavel #lojadenaturais #comerciolocal",
    "papelaria": "#papelaria #voltasaulas #lojista #comerciolocal",
    "pet": "#petshop #banhoetosa #pet #comerciolocal",
    "servicos": "#prestadordeservicos #autonomo #reparos #empreendedor",
    "geral": "#pequenonegocio #empreendedor #comerciolocal #vendasonline",
    "panfletos": "#pequenonegocio #empreendedor #comerciolocal #marketinglocal",
}
HASHTAGS_TIPO = {
    "educativo": "#empreendedorismo #pequenonegocio #comerciolocal #dicasdenegocio",
    "conversao": "#pequenonegocio #empreendedor #comerciolocal #vendasonline",
    "parceiro": "#programadeparceiros #indicacao #empreendedor #pequenonegocio",
    "bastidor": "#empreendedor #comerciolocal #pequenonegocio #brasil",
    "vitrine": "#comerciolocal #apoieonegociolocal #pertodemim #pequenonegocio",
}


def data_comemorativa(categoria=None, hoje=None):
    """Hashtag da data comemorativa em vigor para o ramo, ou ''.
    Le conteudo/datas-comemorativas.json; arquivo com defeito = sem data."""
    import json
    hoje = hoje or config.hoje_br()
    try:
        dados = json.loads((config.CONTEUDO_DIR / "datas-comemorativas.json").read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return ""
    md = hoje.strftime("%m-%d")
    iso = hoje.isoformat()
    for d in dados.get("datas", []):
        ini, fim, tag = str(d.get("inicio", "")), str(d.get("fim", "")), str(d.get("tag", ""))
        if not tag.startswith("#") or not ini or not fim:
            continue
        ramos = d.get("ramos") or ["*"]
        if "*" not in ramos and (categoria or "") not in ramos:
            continue
        if len(ini) == 10:                       # AAAA-MM-DD: so naquele ano
            dentro = ini <= iso <= fim
        elif ini <= fim:                         # MM-DD dentro do ano
            dentro = ini <= md <= fim
        else:                                    # MM-DD que vira o ano (dez -> jan)
            dentro = md >= ini or md <= fim
        if dentro:
            return tag.lower()
    return ""


def hashtags(tipo="educativo", categoria=None, hoje=None):
    """No maximo 5 hashtags (limite do Instagram). Vao no FIM DA LEGENDA do
    Instagram — nunca em comentario automatico. Ramo da peca manda; sem ramo
    conhecido, vale o tipo de pauta. Em data comemorativa (conteudo/
    datas-comemorativas.json) a tag da data entra em 2o lugar e a ultima do
    ramo sai."""
    extras = HASHTAGS_RAMO.get(categoria or "") or HASHTAGS_TIPO.get(tipo) or HASHTAGS_TIPO["educativo"]
    tags = []
    for t in ("#moviki " + extras).split():
        if t not in tags:
            tags.append(t)
    data = data_comemorativa(categoria, hoje)
    if data and data not in tags:
        tags.insert(1, data)
    return " ".join(tags[: config.HASHTAGS_MAX])
