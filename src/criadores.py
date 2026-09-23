# -*- coding: utf-8 -*-
"""
Pecas dos INFLUENCIADORES (criadores) como fonte das redes oficiais.

"Brecha" deixada em 22/09/2026, antes de o painel do criador existir. O
contrato que o endpoint do site precisa cumprir esta em
conteudo/CRIADORES-CONTRATO.md. Enquanto o secret CRIADORES_URL nao existir,
esta fonte devolve lista vazia e o robo segue so com o Material de apoio.

AS DUAS CHAVES — nenhuma peca vai ao ar com uma so:
  1. o CRIADOR autorizou a republicacao nas redes do Moviki (botao no painel,
     com a versao do termo e a data);
  2. o MOVIKI aprovou a peca (o dono, no painel do dono).
  O endpoint ja so devolve o que tem as duas; este modulo confere de novo.
  Opt-in e aprovacao se conferem duas vezes — e o mesmo desenho da vitrine.

REVOGACAO: se o criador tirar a autorizacao, a peca some do endpoint e o
robo nunca mais a escolhe. O que ja foi publicado nao e apagado sozinho
(retirada de post antigo e manual, a pedido — esta no termo).

VALIDADE: a autorizacao vence (padrao do termo: 12 meses). Vencida, fica fora
mesmo que o endpoint a devolva por engano.

CREDITO: toda peca de criador sai com "Conteúdo de @arroba" na legenda.
"""
import re
from datetime import datetime, timezone

from . import compliance, config, material
from . import util_net as net

FORMATOS = ("feed", "story", "reel")
MIDIAS = ("imagem", "video")
_ARROBA = re.compile(r"^@?([A-Za-z0-9._]{1,30})$")


# ------------------------------------------------------------------ leitura
def ativa():
    return bool(config.CRIADORES_URL)


def carregar(url=None):
    """Le as pecas liberadas. Fonte desligada -> []. Falha de rede -> erro
    (quem chama cai no Material de apoio e avisa no log)."""
    url = (url if url is not None else config.CRIADORES_URL).strip()
    if not url:
        return []
    cab = {"Accept": "application/json"}
    if config.CRIADORES_SECRET:
        cab["Authorization"] = f"Bearer {config.CRIADORES_SECRET}"
    r = net.get(url, headers=cab)
    if r.status_code == 401:
        raise RuntimeError("criadores: 401 — CRIADORES_SECRET ausente ou errado")
    if r.status_code != 200:
        raise RuntimeError(f"criadores: HTTP {r.status_code}")
    dados = r.json()
    if not isinstance(dados, dict) or not isinstance(dados.get("itens"), list):
        raise RuntimeError("criadores: formato inesperado")
    return [i for i in dados["itens"] if isinstance(i, dict)]


# ------------------------------------------------------------------ validacao
def _data(txt):
    try:
        d = datetime.fromisoformat(str(txt).replace("Z", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def arroba(item):
    m = _ARROBA.match(str(((item.get("criador") or {}).get("arroba")) or "").strip())
    return f"@{m.group(1)}" if m else ""


def valida(item, agora=None):
    """Motivo da recusa, ou '' se a peca pode ir ao ar."""
    agora = agora or datetime.now(timezone.utc)
    if not item.get("id"):
        return "sem id"
    if item.get("formato") not in FORMATOS:
        return "formato invalido"
    if item.get("midia") not in MIDIAS:
        return "midia invalida"
    if item.get("formato") == "feed" and item.get("midia") != "imagem":
        return "feed de criador so com imagem (video vai como reel)"
    if item.get("formato") == "reel" and item.get("midia") != "video":
        return "reel precisa ser video"
    if not str(item.get("url", "")).startswith("https://"):
        return "url nao e https"

    aut = item.get("autorizacao") or {}
    if aut.get("autorizado") is not True or not aut.get("versao_termo") or not _data(aut.get("em")):
        return "sem autorizacao do criador"
    if aut.get("revogada_em"):
        return "autorizacao revogada"
    vence = _data(aut.get("expira_em"))
    if vence is None or vence <= agora:
        return "autorizacao vencida ou sem validade"

    apr = item.get("aprovacao") or {}
    if apr.get("aprovada") is not True or not _data(apr.get("em")):
        return "sem aprovacao do Moviki"

    if not ((item.get("criador") or {}).get("uid")):
        return "sem criador"
    if not arroba(item) and not ((item.get("criador") or {}).get("nome")):
        return "sem nome nem @ para o credito"

    if item.get("midia") == "video":
        try:
            seg = float(item.get("duracao"))
        except (TypeError, ValueError):
            return "video sem duracao"
        if not (config.REEL_DURACAO_MIN <= seg <= config.REEL_DURACAO_MAX):
            return "video fora de 3 a 90 s"
    try:
        prop = float(item.get("w")) / float(item.get("h"))
    except (TypeError, ValueError, ZeroDivisionError):
        return "sem largura/altura"
    if item["formato"] == "feed" and not (0.8 <= prop <= 1.91):
        return "proporcao fora do feed"
    if item["formato"] in ("story", "reel") and not (0.5 <= prop <= 0.6):
        return "proporcao fora do 9:16"
    return ""


# ------------------------------------------------------------------ legenda
def credito(item):
    quem = arroba(item) or ((item.get("criador") or {}).get("nome") or "").strip()
    icone = "\U0001f3ac" if item.get("midia") == "video" else "\U0001f4f8"
    return f"{icone} Conteúdo de {quem}"


def _legendas(item):
    """Legenda na voz da marca + credito. A do criador passa pela mesma
    conversao do material e pela trava. Violou QUALQUER camada, sai a
    reserva inteira — texto de terceiro nao e "suavizado" pelo robo, porque
    a frase reescrita iria ao ar como se fosse dele."""
    titulo = (item.get("titulo") or "Negócio no mapa, na hora").strip()
    bruta = item.get("legenda") or ""
    saida = {}
    for canal in ("instagram", "facebook"):
        res = material.reserva(titulo, canal)
        if compliance.violacoes(res):          # titulo do criador sujo -> reserva neutra
            res = material.reserva(None, canal)
        conv = material.legenda_oficial(bruta, canal) if bruta else None
        texto = conv if (conv and not compliance.violacoes(conv)) else compliance.garantir(res, res)
        saida[canal] = f"{texto}\n\n{credito(item)}"
    return saida["instagram"], saida["facebook"]


# ------------------------------------------------------------------ pecas
def pecas(itens, formato, agora=None):
    """Pecas liberadas no formato pedido, ja no formato comum do robo."""
    saida = []
    for it in itens or []:
        if it.get("formato") != formato:
            continue
        motivo = valida(it, agora)
        if motivo:
            print(f"criadores: {it.get('id', '?')} fora ({motivo})")
            continue
        leg_ig = leg_fb = None
        if formato in ("feed", "reel"):
            leg_ig, leg_fb = _legendas(it)
        cri = it.get("criador") or {}
        saida.append({
            "id": f"c:{it['id']}",
            "origem": "criador",
            "formato": formato,
            "midia": it["midia"],
            "url": it["url"],
            "capa": it.get("capa") if str(it.get("capa", "")).startswith("https://") else None,
            "titulo": it.get("titulo", ""),
            "categoria": it.get("categoria") or "geral",
            "legenda_ig": leg_ig,
            "legenda_fb": leg_fb,
            "criador": {"uid": cri.get("uid"), "nome": cri.get("nome", ""), "arroba": arroba(it)},
            "credito": credito(it),
            "duracao": it.get("duracao"),
            "w": it.get("w"), "h": it.get("h"),
        })
    return saida
