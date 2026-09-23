# -*- coding: utf-8 -*-
"""
Banco de imagens e videos do MATERIAL DE APOIO do parceiro como fonte das
redes oficiais.

Criado em 22/09/2026. O robo publica as pecas prontas da aba "Material de
apoio" do painel do parceiro — as mesmas artes, a mesma identidade visual,
ja revisadas antes de subir — nos TRES formatos:

  catalogo tipo 'feed'  -> post de feed
  catalogo tipo 'story' -> story
  catalogo tipo 'video' -> reel (so 9:16 e entre 3 e 90 s)

FONTE UNICA: o catalogo e lido AO VIVO em app.moviki.com.br/material/
catalogo.json. Peca nova que entra na aba do parceiro entra na rotacao do
robo sozinha. Nada e copiado para este repositorio.

O QUE MUDA NA PECA PARA IR A PAGINA OFICIAL
  A arte vai como esta (nao se mexe em peca aprovada). A LEGENDA do catalogo
  e escrita na voz do PARCEIRO ("#publi", "Comece pelo meu link: {link}").
  Na pagina do proprio Moviki isso e errado nos dois pontos:
    - "#publi" marca conteudo comissionado de terceiro (Guia CONAR). Aqui o
      anunciante e a propria marca; a marcacao nao se aplica.
    - "meu link" / {link} apontaria para um parceiro que nao existe.
  Por isso a legenda passa por `legenda_oficial()`. Se sobrar qualquer marca
  de parceiro depois da troca, a peca e DESCARTADA — nunca vai pela metade.
  Story nao tem legenda: vai so a arte.

QUEM FICA DE FORA
  - ids em config.MATERIAL_EXCLUIR (texto de parceiro impresso na arte ou
    falado no video);
  - categoria 'recrutar' e legenda com {link_parceiro};
  - proporcao fora do formato (feed 4:5 a 1,91:1; story e reel 9:16);
  - video fora de 3 a 90 s;
  - peca que vende LIVE (lives, transmissao, "vender ao vivo") enquanto
    config.LIVE_NA_PAGINA estiver desligado — a live esta em beta fechado
    (23/09/2026). Story nao tem legenda e a arte nao passa pela trava de
    texto: por isso o filtro olha id, titulo, legenda, arquivo e dica.
"""
import re

from . import compliance, config
from . import util_net as net

PROPORCAO_FEED = (0.8, 1.91)   # 4:5 ate paisagem maxima do Instagram
PROPORCAO_VERTICAL = (0.5, 0.6)  # 9:16 com folga (0,5625)

_FALA_DE_LIVE = re.compile(
    r"\blives?\b|transmiss|vend\w*\s+ao\s+vivo|venda\s+ao\s+vivo|compr\w*\s+ao\s+vivo"
    r"|ao\s+vivo\s+pel[ao]\s+c[aâ]mera|modo\s+live",
    re.I,
)


def fala_de_live(item):
    """A peca vende a live (beta fechado)? Olha todo texto que acompanha a arte."""
    txt = " ".join(str(item.get(k) or "") for k in ("id", "titulo", "legenda", "texto", "arquivo", "dica"))
    return bool(_FALA_DE_LIVE.search(txt))


_MARCAS_PARCEIRO = re.compile(
    r"\{link_parceiro\}|\{meu_nome\}|\{verificacao\}|\bmeu\s+link\b|#publi\b|\{link\}",
    re.I,
)


# ------------------------------------------------------------------ catalogo
def carregar_catalogo(url=None):
    """Le o catalogo publicado. Falha ALTO: quem chama decide a reserva."""
    url = url or config.MATERIAL_CATALOGO
    r = net.get(url, headers={"Accept": "application/json"})
    if r.status_code != 200:
        raise RuntimeError(f"catalogo do material: HTTP {r.status_code}")
    dados = r.json()
    if not isinstance(dados, dict) or not isinstance(dados.get("itens"), list):
        raise RuntimeError("catalogo do material: formato inesperado")
    return dados


def _proporcao(item):
    try:
        return float(item.get("w")) / float(item.get("h"))
    except (TypeError, ValueError, ZeroDivisionError):
        return 0.0


def _segundos(duracao):
    """'1:07' -> 67.0 ; '27' -> 27.0 ; lixo -> None"""
    t = str(duracao or "").strip()
    if not t:
        return None
    try:
        partes = [float(p) for p in t.split(":")]
    except ValueError:
        return None
    total = 0.0
    for p in partes:
        total = total * 60 + p
    return total


def url_absoluta(arquivo):
    arq = str(arquivo or "").lstrip("/")
    return arq if arq.startswith("https://") else f"{config.MATERIAL_BASE}/{arq}"


# ------------------------------------------------------------------ legenda
def legenda_oficial(texto, canal="instagram"):
    """Converte a legenda do parceiro na voz da pagina oficial.

    Devolve None se nao der pra converter com seguranca.
    """
    t = (texto or "").strip()
    t = re.sub(r"^#publi\b[\s:.\-–—]*", "", t, flags=re.I)

    destino = "em moviki.com.br" if canal == "facebook" else "pelo link da bio."
    t = re.sub(r"pelo\s+meu\s+link\s*:?\s*\{link\}\.?", destino, t, flags=re.I)
    t = t.replace("{link}", "moviki.com.br")

    t = re.sub(r"[ \t]+\n", "\n", t)
    t = re.sub(r"\n{3,}", "\n\n", t).strip()
    if not t or _MARCAS_PARCEIRO.search(t):
        return None
    return t


def reserva(titulo, canal="instagram"):
    fim = "Conheça em moviki.com.br" if canal == "facebook" else "Conheça pelo link da bio."
    t = (titulo or "Seu negócio no mapa, na hora").strip().rstrip(".")
    return f"{t}.\n\n{fim}"


# ------------------------------------------------------------------ pecas
def _formato_do_item(item):
    tipo = item.get("tipo")
    prop = _proporcao(item)
    if tipo == "feed":
        return "feed" if PROPORCAO_FEED[0] <= prop <= PROPORCAO_FEED[1] else None
    if tipo == "story":
        return "story" if PROPORCAO_VERTICAL[0] <= prop <= PROPORCAO_VERTICAL[1] else None
    if tipo == "video":
        if not (PROPORCAO_VERTICAL[0] <= prop <= PROPORCAO_VERTICAL[1]):
            return None
        seg = _segundos(item.get("duracao"))
        if seg is None or not (config.REEL_DURACAO_MIN <= seg <= config.REEL_DURACAO_MAX):
            return None
        return "reel"
    return None


def pecas(catalogo, formato, excluir=None):
    """Pecas do catalogo que podem ir para a pagina oficial, no formato pedido,
    ja no formato comum do robo (ver src/pecas.py)."""
    excluir = config.MATERIAL_EXCLUIR if excluir is None else excluir
    saida = []
    for it in (catalogo or {}).get("itens", []):
        if not isinstance(it, dict) or not it.get("id") or not it.get("arquivo"):
            continue
        if it["id"] in excluir or it.get("categoria") == "recrutar":
            continue
        if not config.LIVE_NA_PAGINA and fala_de_live(it):
            continue
        if _formato_do_item(it) != formato:
            continue
        arq = str(it["arquivo"]).lower()
        midia = "video" if formato == "reel" else "imagem"
        if midia == "imagem" and not arq.endswith((".jpg", ".jpeg", ".png")):
            continue
        if midia == "video" and not arq.endswith(".mp4"):
            continue

        leg_ig = leg_fb = None
        if formato in ("feed", "reel"):
            bruta = it.get("legenda") or ""
            if not bruta or "{link_parceiro}" in bruta:
                continue
            leg_ig = legenda_oficial(bruta, "instagram")
            leg_fb = legenda_oficial(bruta, "facebook")
            if leg_ig is None or leg_fb is None:
                continue
            leg_ig = compliance.garantir(leg_ig, reserva(it.get("titulo"), "instagram"))
            leg_fb = compliance.garantir(leg_fb, reserva(it.get("titulo"), "facebook"))

        saida.append({
            "id": it["id"],
            "origem": "material",
            "formato": formato,
            "midia": midia,
            "url": url_absoluta(it["arquivo"]),
            "capa": url_absoluta(it["capa"]) if (formato == "reel" and it.get("capa")
                                                 and str(it["capa"]).lower().endswith((".jpg", ".jpeg"))) else None,
            "titulo": it.get("titulo", ""),
            "categoria": it.get("categoria", "geral"),
            "legenda_ig": leg_ig,
            "legenda_fb": leg_fb,
            "criador": None,
            "duracao": _segundos(it.get("duracao")),
            "w": it.get("w"), "h": it.get("h"),
        })
    return saida
