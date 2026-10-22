# -*- coding: utf-8 -*-
"""
Shorts do canal Moviki Live Shop (22/10/2026).

O QUE FAZ
  Sobe UM Short por rodada no canal do YouTube, com titulo, descricao, capa e
  playlist. A fila mora em conteudo/youtube.json (feita a mao, pensada para a
  busca de "live shop"); esgotada a fila, o robo pega sozinho os videos 9:16
  do Material de apoio e da grade que ainda nao estao no canal.

POR QUE SOBE PRIVADO
  O YouTube obriga: projeto de API nao auditado so consegue enviar video
  PRIVADO. Ate a auditoria sair, o robo sobe privado e a publicacao (tornar
  publico + comentario fixado) e feita na passada semanal. Quando a auditoria
  sair, o Paulo cria o secret YT_VISIBILIDADE=public e o robo passa a publicar
  sozinho. O comentario fixado continua manual: a API nao fixa comentario.

TRAVAS
  - Todo titulo e descricao passa por compliance.garantir(), com reserva limpa.
  - So video que ja passou pelas travas da pagina oficial (material.pecas +
    triagem) ou que esta na grade valida. Nunca video vencido, nem que vence
    em menos de VENCE_EM_DIAS (no YouTube o video fica; nao vale subir o que
    perde o sentido logo depois).
  - Nunca o mesmo video duas vezes: estado/youtube.json guarda cada envio,
    inclusive os 49 que subiram a mao antes do robo.
  - Falha da capa ou da playlist nao derruba o envio (o video ja subiu).
  - Credencial so por GitHub Secrets (YT_CLIENT_ID, YT_CLIENT_SECRET,
    YT_REFRESH_TOKEN). Sem elas, o robo avisa e sai sem erro.

COTA
  Envio 1.600 + capa 50 + playlist 50 = 1.700 unidades por video, de 10.000
  por dia. Um video por rodada fica muito abaixo do teto.
"""
import json
import os
import re
from datetime import date, datetime, timedelta, timezone

from . import compliance, config, estado, grade
from . import util_net as net

MARCA = "2026-10-22-youtube"
ARQUIVO_FILA = "youtube.json"            # conteudo/
ARQUIVO_ESTADO = "youtube.json"          # estado/
VENCE_EM_DIAS = 7
VISIBILIDADES = ("private", "unlisted", "public")
TITULO_MAX = 100
DESCRICAO_MAX = 5000
VIDEO_MAX_BYTES = 256 * 1024 * 1024
CAPA_MAX_BYTES = 2 * 1024 * 1024
CATEGORIA_YT = "27"                      # Educacao (padrao de envio do canal, 22/10/2026)

TOKEN_URL = "https://oauth2.googleapis.com/token"
API = "https://www.googleapis.com/youtube/v3"
UPLOAD = "https://www.googleapis.com/upload/youtube/v3"

RODAPE = ("O que é live shop: https://www.moviki.com.br/live-shop\n"
          "Como fazer a primeira live de vendas: https://www.moviki.com.br/guia/como-fazer-live-de-vendas")
HASHTAGS = "#liveshop #vendaaovivo #moviki"
COMENTARIO_PADRAO = ("Tudo sobre live shop, com o passo a passo: https://www.moviki.com.br/live-shop\n"
                     "Teste grátis de 30 dias, sem cartão.")


# ------------------------------------------------------------------ config
def ligado():
    return all(os.environ.get(k, "").strip() for k in ("YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN"))


def visibilidade():
    """private (padrao) ate a auditoria da API; public depois, pelo secret."""
    v = os.environ.get("YT_VISIBILIDADE", "").strip().lower()
    return v if v in VISIBILIDADES else "private"


def carregar_fila(caminho=None):
    caminho = caminho or (config.CONTEUDO_DIR / ARQUIVO_FILA)
    if not caminho.exists():
        return {"fila": [], "pular": {}, "playlists": {}}
    dados = json.loads(caminho.read_text(encoding="utf-8"))
    dados.setdefault("fila", [])
    dados.setdefault("pular", {})
    dados.setdefault("playlists", {})
    return dados


def ler_estado():
    e = estado.ler_lista(ARQUIVO_ESTADO)
    e = e if isinstance(e, dict) else {}
    e.setdefault("enviados", {})
    return e


# ------------------------------------------------------------------ texto
def _limpo(t):
    # O YouTube recusa "<" e ">" em titulo e descricao (erro 400 invalidTitle).
    return re.sub(r"[<>]", "", str(t or "")).strip()


def _cortar(t, n):
    t = _limpo(t)
    if len(t) <= n:
        return t
    corte = t[: n - 1].rsplit(" ", 1)[0].rstrip(" |:-,.")
    return corte + "…"


def titulo_auto(titulo):
    base = _limpo(titulo).rstrip(".") or "Venda ao vivo pelo celular"
    return _cortar(f"{base} | Live shop | Moviki", TITULO_MAX)


def descricao_auto(legenda, ramo_link=None):
    t = _limpo(legenda)
    t = re.sub(r"(conhe[çc]a\s+)?(pelo|no)\s+link\s+(d|n)a\s+bio\.?", "", t, flags=re.I)
    t = re.sub(r"link\s+(d|n)a\s+bio\.?", "", t, flags=re.I)
    t = re.sub(r"[ \t]+\n", "\n", t)
    t = re.sub(r"\n{3,}", "\n\n", t).strip()
    rodape = RODAPE if not ramo_link else f"{ramo_link}\n{RODAPE}"
    return f"{t}\n\n{rodape}\n\n{HASHTAGS}".strip()


def reserva_titulo():
    return "Live shop: venda ao vivo pelo celular | Moviki"


def reserva_descricao():
    return ("Com o Moviki, a sua loja abre a live pelo celular, mostra o produto de perto "
            f"e responde no chat na hora.\n\nTeste grátis de 30 dias, sem cartão.\n\n{RODAPE}\n\n{HASHTAGS}")


def textos(item):
    """(titulo, descricao, comentario) ja conferidos pela trava."""
    tit = compliance.garantir(_cortar(item["titulo"], TITULO_MAX), reserva_titulo())
    desc = compliance.garantir(_cortar(item["descricao"], DESCRICAO_MAX), reserva_descricao())
    com = compliance.garantir(_limpo(item.get("comentario") or COMENTARIO_PADRAO), COMENTARIO_PADRAO)
    return tit, desc, com


# ------------------------------------------------------------------ playlist
def playlist_de(pid, cfg, pedida=None):
    pls = cfg.get("playlists") or {}
    if pedida:
        return pls.get(pedida)
    if pid.startswith("ugc-bastidores"):
        return pls.get("bastidores")
    if pid.startswith(("video-comercio-", "video-shopping-")):
        return pls.get("ramo")
    return pls.get("como_vender")


def _link_ramo(pid):
    m = re.match(r"^video-(?:comercio|shopping)-([a-z0-9-]+)$", pid)
    if m:
        return f"Live shop para o seu ramo: https://www.moviki.com.br/live-shop/{m.group(1)}"
    return None


# ------------------------------------------------------------------ candidatos
def _fontes(pecas_material, itens_grade, hoje):
    """{id: {url, capa, titulo, legenda}} — material e grade, sem prefixo."""
    fontes = {}
    for p in pecas_material or []:
        fontes[p["id"]] = {"url": p["url"], "capa": p.get("capa"), "titulo": p.get("titulo", ""),
                           "legenda": p.get("legenda_ig") or "", "valido_ate": None, "origem": "material"}
    for it in itens_grade or []:
        if it.get("formato") != "reel":
            continue
        sit = grade.situacao(it, hoje)
        if sit in ("vencido", "reconferir") or grade.vende_live_bloqueado(it):
            fontes.pop(it["id"], None)      # a grade manda: vencida la, fora aqui
            continue
        fontes[it["id"]] = {"url": it["video"], "capa": it.get("capa"), "titulo": it.get("titulo", ""),
                            "legenda": it.get("legenda", ""), "valido_ate": it.get("valido_ate"),
                            "origem": "grade"}
    return fontes


def _vence_logo(valido_ate, hoje):
    if not valido_ate:
        return False
    try:
        return date.fromisoformat(str(valido_ate)) < hoje + timedelta(days=VENCE_EM_DIAS)
    except ValueError:
        return True


def candidatos(cfg, pecas_material, itens_grade, enviados, hoje):
    """Lista na ordem de envio: fila feita a mao primeiro, depois o resto."""
    fontes = _fontes(pecas_material, itens_grade, hoje)
    pular = set((cfg.get("pular") or {}).keys())
    feitos = set(enviados or {})
    saida, vistos = [], set()

    def pode(pid):
        f = fontes.get(pid)
        return (f and pid not in feitos and pid not in pular and pid not in vistos
                and not _vence_logo(f.get("valido_ate"), hoje))

    for q in cfg.get("fila") or []:
        pid = q.get("id")
        if not pid or not pode(pid):
            continue
        f = fontes[pid]
        saida.append({"id": pid, "url": f["url"], "capa": f.get("capa"), "origem": f["origem"],
                      "titulo": q.get("titulo") or titulo_auto(f["titulo"]),
                      "descricao": q.get("descricao") or descricao_auto(f["legenda"], _link_ramo(pid)),
                      "comentario": q.get("comentario"),
                      "playlist": playlist_de(pid, cfg, q.get("playlist")), "fila": True})
        vistos.add(pid)

    for pid in sorted(fontes):
        if not pode(pid):
            continue
        f = fontes[pid]
        if not f["legenda"]:
            continue
        saida.append({"id": pid, "url": f["url"], "capa": f.get("capa"), "origem": f["origem"],
                      "titulo": titulo_auto(f["titulo"]),
                      "descricao": descricao_auto(f["legenda"], _link_ramo(pid)),
                      "comentario": None, "playlist": playlist_de(pid, cfg), "fila": False})
        vistos.add(pid)
    return saida


# ------------------------------------------------------------------ API
def _erro_api(r):
    try:
        e = r.json().get("error") or {}
        motivo = ((e.get("errors") or [{}])[0]).get("reason") or e.get("status") or ""
        return net.sem_segredo(f"HTTP {r.status_code} {motivo} {str(e.get('message', ''))[:160]}")
    except Exception:  # noqa: BLE001
        return f"HTTP {r.status_code}"


def token(post=net.post):
    r = post(TOKEN_URL, data={
        "client_id": os.environ["YT_CLIENT_ID"].strip(),
        "client_secret": os.environ["YT_CLIENT_SECRET"].strip(),
        "refresh_token": os.environ["YT_REFRESH_TOKEN"].strip(),
        "grant_type": "refresh_token",
    })
    if r.status_code != 200:
        # invalid_grant = token revogado ou vencido (tela de consentimento em
        # "Teste" vence o token em 7 dias): refazer o passo a passo do token.
        raise RuntimeError(f"youtube: token recusado ({_erro_api(r)})")
    return r.json()["access_token"]


def _baixar(url, limite, get=net.get):
    r = get(url, timeout=120)
    if r.status_code != 200:
        raise RuntimeError(f"download HTTP {r.status_code}")
    dados = r.content
    if not dados or len(dados) > limite:
        raise RuntimeError(f"arquivo com {len(dados or b'')} bytes (limite {limite})")
    return dados


def eh_mp4(dados):
    return len(dados) > 12 and dados[4:8] == b"ftyp"


def corpo_video(tit, desc, visib, ia=True):
    status = {"privacyStatus": visib, "selfDeclaredMadeForKids": False, "embeddable": True,
              "license": "youtube"}
    if ia:
        # Mesma regra do rotulo "Informacoes de IA" da Meta (ROTULO_IA): cena
        # ilustrativa da casa e declarada como conteudo sintetico.
        status["containsSyntheticMedia"] = True
    return {
        "snippet": {"title": tit, "description": desc, "categoryId": CATEGORIA_YT,
                    "defaultLanguage": "pt-BR", "defaultAudioLanguage": "pt-BR",
                    "tags": ["live shop", "venda ao vivo", "live de vendas", "Moviki"]},
        "status": status,
    }


def enviar_video(tok, dados, corpo, post=net.post, put=net.put):
    """Envio resumavel em uma parte so. Devolve o id do video."""
    cab = {"Authorization": f"Bearer {tok}", "Content-Type": "application/json; charset=UTF-8",
           "X-Upload-Content-Type": "video/mp4", "X-Upload-Content-Length": str(len(dados))}
    r = post(f"{UPLOAD}/videos?uploadType=resumable&part=snippet,status", headers=cab, json=corpo)
    if r.status_code != 200 or not r.headers.get("Location"):
        raise RuntimeError(f"youtube: abrir envio falhou ({_erro_api(r)})")
    r2 = put(r.headers["Location"], data=dados, timeout=600,
             headers={"Authorization": f"Bearer {tok}", "Content-Type": "video/mp4"})
    if r2.status_code not in (200, 201):
        raise RuntimeError(f"youtube: envio do video falhou ({_erro_api(r2)})")
    vid = (r2.json() or {}).get("id")
    if not vid:
        raise RuntimeError("youtube: envio sem id de video")
    return vid


def por_capa(tok, vid, dados, post=net.post):
    r = post(f"{UPLOAD}/thumbnails/set?videoId={vid}", data=dados,
             headers={"Authorization": f"Bearer {tok}", "Content-Type": "image/jpeg"})
    if r.status_code != 200:
        raise RuntimeError(_erro_api(r))


def por_na_playlist(tok, vid, playlist, post=net.post):
    r = post(f"{API}/playlistItems?part=snippet", headers={"Authorization": f"Bearer {tok}"},
             json={"snippet": {"playlistId": playlist, "resourceId": {"kind": "youtube#video", "videoId": vid}}})
    if r.status_code != 200:
        raise RuntimeError(_erro_api(r))


# ------------------------------------------------------------------ rodada
def publicar(item, tok, visib=None, get=net.get, post=net.post, put=net.put):
    """Sobe o item. Devolve o registro para o estado."""
    visib = visib or visibilidade()
    tit, desc, com = textos(item)
    video = _baixar(item["url"], VIDEO_MAX_BYTES, get)
    if not eh_mp4(video):
        raise RuntimeError("youtube: o arquivo nao e MP4")
    vid = enviar_video(tok, video, corpo_video(tit, desc, visib, ia=config.ROTULO_IA), post, put)
    print(f"youtube: {item['id']} enviado como {visib} -> {vid}")
    reg = {"yt": vid, "quando": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "visibilidade": visib, "titulo": tit, "comentario": com, "playlist": item.get("playlist"),
           "origem": item.get("origem"), "capa": False, "na_playlist": False, "robo": MARCA}
    if item.get("capa"):
        try:
            por_capa(tok, vid, _baixar(item["capa"], CAPA_MAX_BYTES, get), post)
            reg["capa"] = True
        except Exception as e:  # noqa: BLE001
            print(f"aviso: capa nao entrou ({net.sem_segredo(e)}) -> o video segue com a capa automatica")
    if item.get("playlist"):
        try:
            por_na_playlist(tok, vid, item["playlist"], post)
            reg["na_playlist"] = True
        except Exception as e:  # noqa: BLE001
            print(f"aviso: playlist nao entrou ({net.sem_segredo(e)}) -> por a mao na passada semanal")
    return reg


def registrar(est, pid, reg):
    est["enviados"][pid] = reg
    estado.gravar_lista(ARQUIVO_ESTADO, est)
