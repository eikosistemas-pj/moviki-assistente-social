# -*- coding: utf-8 -*-
"""
Relatorio das redes para o painel do dono (28/09/2026).

Roda 2x por dia (metricas.yml) e grava estado/redes.json:
  - saude das duas contas (seguidores, cota de publicacao do Instagram);
  - canal de cada formato HOJE (rampa por data + freio);
  - os posts dos ultimos 30 dias com miniatura, link, curtidas e comentarios
    no Instagram e na Pagina;
  - agenda dos ultimos 7 dias: quantos posts eram esperados x quantos sairam;
  - alertas (plano B, freio, dia com post faltando, token sem permissao).

Quem le: o painel do dono (secao Redes sociais) e o agente diario.

POR QUE AQUI E NAO NO PAINEL: o token da Meta so existe nos secrets do
Actions. O navegador do dono nunca recebe token — le um JSON publico sem
nenhum segredo dentro. Curtida e comentario ja sao publicos nas redes.

Nunca publica nada e nunca quebra: metrica que falha vira "—" no painel.
"""
import json
import re
from collections import Counter
from datetime import datetime, timedelta, timezone

from src import config, estado, freio, material
from src import util_net as net

DIAS_POSTS = 30
DIAS_AGENDA = 7
FUSO = config.FUSO_BR


# ---------------------------------------------------------------- Graph API
def _graph_get(caminho, params, token):
    try:
        r = net.get(f"{config.GRAPH}/{caminho}", params=dict(params, access_token=token), timeout=25)
        return r.json()
    except Exception as e:  # noqa: BLE001
        return {"error": {"message": net.sem_segredo(e)}}


def _erro(r):
    if not isinstance(r, dict):
        return "resposta invalida"
    e = r.get("error")
    return (e.get("message") or "erro") if isinstance(e, dict) else None


def _total(r, campo):
    try:
        return int(((r.get(campo) or {}).get("summary") or {}).get("total_count"))
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------- por post
def metricas_instagram(media_id, get):
    r = get(media_id, {"fields": "like_count,comments_count,permalink,media_product_type"})
    err = _erro(r)
    if err:
        return {"id": media_id, "erro": err[:160]}
    return {"id": media_id, "link": r.get("permalink"), "curtidas": r.get("like_count"),
            "comentarios": r.get("comments_count")}


def metricas_facebook(post_id, formato, get):
    if formato == "story":
        # Story da Pagina nao expoe curtida/comentario pela API.
        return {"id": post_id}
    if formato == "reel":
        r = get(post_id, {"fields": "permalink_url,likes.summary(true).limit(0),"
                                    "comments.summary(true).limit(0)"})
        err = _erro(r)
        if err:
            return {"id": post_id, "erro": err[:160]}
        link = r.get("permalink_url") or ""
        if link.startswith("/"):
            link = "https://www.facebook.com" + link
        return {"id": post_id, "link": link or None,
                "curtidas": _total(r, "likes"), "comentarios": _total(r, "comments")}
    r = get(post_id, {"fields": "permalink_url,reactions.summary(total_count).limit(0),"
                                "comments.summary(total_count).limit(0),shares"})
    err = _erro(r)
    if err:
        return {"id": post_id, "erro": err[:160]}
    return {"id": post_id, "link": r.get("permalink_url"), "curtidas": _total(r, "reactions"),
            "comentarios": _total(r, "comments"),
            "compartilhamentos": (r.get("shares") or {}).get("count", 0)}


# ---------------------------------------------------------------- miniatura
def _indice_catalogo():
    try:
        cat = material.carregar_catalogo()
    except Exception:  # noqa: BLE001
        return {}
    idx = {}
    for it in cat.get("itens", []):
        if not isinstance(it, dict) or not it.get("id"):
            continue
        arq = str(it.get("arquivo") or "")
        capa = str(it.get("capa") or "")
        img = capa if arq.lower().endswith(".mp4") else arq
        if img and img.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
            idx[it["id"]] = {"mini": material.url_absoluta(img), "titulo": it.get("titulo", ""),
                             "ramo": it.get("categoria", "")}
    return idx


def _indice_publicado(pasta=None):
    """Arte que o proprio robo hospedou em publicado/ ({prefixo}-{AAAAmmdd-HHMMSS}.jpg,
    horario UTC). Serve de miniatura para os posts que foram ao ar antes de o
    historico guardar a miniatura (card de pauta, vitrine, story de criador)."""
    pasta = pasta or (config.RAIZ / "publicado")
    idx = []
    try:
        nomes = [p.name for p in pasta.iterdir() if p.suffix.lower() in (".jpg", ".jpeg", ".png")]
    except OSError:
        return idx
    for nome in nomes:
        m = re.match(r"^(feed|story|reel)-.*?(\d{8}-\d{6})\.(jpe?g|png)$", nome, re.I)
        if not m:
            continue
        try:
            t = datetime.strptime(m.group(2), "%Y%m%d-%H%M%S").replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        idx.append((m.group(1).lower(), t, f"{config.RAW_BASE}/{nome}"))
    return idx


def _mini_publicado(idx, formato, quando):
    """Arte hospedada ate 20 min ANTES do post (o upload vem antes da publicacao)."""
    melhor = None
    for fmt, t, url in idx:
        if fmt != formato:
            continue
        dif = (quando - t).total_seconds()
        if -120 <= dif <= 1200 and (melhor is None or abs(dif) < melhor[0]):
            melhor = (abs(dif), url)
    return melhor[1] if melhor else ""


# ---------------------------------------------------------------- agenda
def esperado(formato, dia):
    """Posts que o calendario manda sair nesse dia (data de Brasilia)."""
    wd = dia.weekday()  # 0 = segunda
    if formato == "feed":
        return 1 if wd <= 4 else 0
    if formato == "story":
        return 2
    if formato == "reel":
        return 1 if wd in (1, 5) else 0
    return 0


def _quando(linha):
    try:
        return datetime.fromisoformat(linha["quando"])
    except (KeyError, ValueError, TypeError):
        return None


def montar(hist, agora, get_ig=None, get_fb=None, catalogo=None, contas=None, publicado=None):
    """Monta o relatorio. get_ig/get_fb = funcoes (caminho, params) -> dict."""
    catalogo = catalogo or {}
    hoje = agora.astimezone(FUSO).date()
    limite = agora - timedelta(days=DIAS_POSTS)
    posts, alertas = [], []

    for linha in hist:
        q = _quando(linha)
        if not q or q < limite:
            continue
        formato = linha.get("formato", "feed")
        rede = linha.get("rede", "facebook")
        cat = catalogo.get(linha.get("peca") or "", {})
        p = {
            "quando": linha["quando"],
            "formato": formato,
            "origem": linha.get("origem") or ("casa" if linha.get("subtipo") != "vitrine" else "vitrine"),
            "subtipo": linha.get("subtipo"),
            "titulo": linha.get("descricao") or cat.get("titulo") or "",
            "peca": linha.get("peca"),
            "ramo": linha.get("ramo") or cat.get("ramo") or "",
            "miniatura": linha.get("miniatura") or cat.get("mini")
                         or _mini_publicado(publicado or [], formato, q) or "",
            "rede": rede,
            "planoB": bool(linha.get("planoB")),
            "erroInstagram": linha.get("erroInstagram"),
        }
        idade_h = (agora - q).total_seconds() / 3600
        if rede == "instagram":
            # Story do Instagram some da API em 24 h — nem tenta depois disso.
            if get_ig and not (formato == "story" and idade_h > 23):
                p["ig"] = metricas_instagram(linha.get("media_id"), get_ig)
            else:
                p["ig"] = {"id": linha.get("media_id")}
            fb_id = linha.get("fb")
            if fb_id:
                p["fb"] = metricas_facebook(fb_id, formato, get_fb) if get_fb else {"id": fb_id}
        else:
            mid = linha.get("media_id")
            p["fb"] = metricas_facebook(mid, formato, get_fb) if (get_fb and mid) else {"id": mid}
        posts.append(p)

    # --------------------------------------------------------- agenda 7 dias
    feitos = Counter()
    for p in posts:
        d = datetime.fromisoformat(p["quando"]).astimezone(FUSO).date()
        feitos[(d.isoformat(), p["formato"])] += 1
    agenda = []
    for n in range(DIAS_AGENDA, -1, -1):
        dia = hoje - timedelta(days=n)
        linha = {"dia": dia.isoformat(), "hoje": n == 0}
        for f in ("feed", "story", "reel"):
            linha[f] = {"esperado": esperado(f, dia), "feito": feitos[(dia.isoformat(), f)]}
        agenda.append(linha)
        # Dia fechado (ontem e anteontem) com post faltando vira alerta. Hoje
        # nao: o calendario ainda esta rodando. Mais antigo que isso fica so na
        # tabela — alerta velho repetido todo dia vira ruido.
        if 1 <= n <= 2:
            for f in ("feed", "story", "reel"):
                e, x = linha[f]["esperado"], linha[f]["feito"]
                if x < e:
                    alertas.append({"nivel": "atencao", "tipo": "faltou_post",
                                    "texto": f"{dia.strftime('%d/%m')}: {f} saiu {x} de {e}."})

    # --------------------------------------------------------- plano B / freio
    semana = agora - timedelta(days=DIAS_AGENDA)
    for p in posts:
        if p["planoB"] and datetime.fromisoformat(p["quando"]) >= semana:
            alertas.append({"nivel": "grave", "tipo": "plano_b",
                            "texto": f"{datetime.fromisoformat(p['quando']).astimezone(FUSO).strftime('%d/%m %H:%M')}: "
                                     f"Instagram falhou no {p['formato']} — saiu só no Facebook. "
                                     f"{(p.get('erroInstagram') or '')[:120]}"})
    fr = freio.ler()
    fim = freio.ativo(agora)
    if fim:
        alertas.append({"nivel": "grave", "tipo": "freio",
                        "texto": f"Freio do Instagram ligado até {fim.astimezone(FUSO).strftime('%d/%m %H:%M')}: "
                                 f"tudo sai só no Facebook até lá."})

    # --------------------------------------------------------- contas
    contas = contas or {}
    for rede, c in contas.items():
        if c.get("erro"):
            alertas.append({"nivel": "grave", "tipo": "conta",
                            "texto": f"{rede}: {c['erro'][:160]}"})

    # --------------------------------------------------------- canal hoje
    rampa = {f: (d.isoformat() if d else None) for f, d in config.rampa_ig().items()}
    canal = {}
    for f in ("feed", "story", "reel"):
        ig = config.instagram_ligado(f, hoje) and not fim
        canal[f] = "instagram+facebook" if ig else "facebook"

    # --------------------------------------------------------- totais
    def somar(dias):
        corte = agora - timedelta(days=dias)
        tot = {}
        for p in posts:
            if datetime.fromisoformat(p["quando"]) < corte:
                continue
            for rede in ("ig", "fb"):
                m = p.get(rede)
                if not m:
                    continue
                t = tot.setdefault(rede, {}).setdefault(p["formato"], {"posts": 0, "curtidas": 0, "comentarios": 0})
                t["posts"] += 1
                t["curtidas"] += int(m.get("curtidas") or 0)
                t["comentarios"] += int(m.get("comentarios") or 0)
        return tot

    return {
        "gerado": agora.isoformat(timespec="seconds"),
        "versao": config.VERSAO,
        "contas": contas,
        "canal_hoje": canal,
        "rampa": rampa,
        "so_facebook": config.SO_FACEBOOK,
        "freio": {"ativo_ate": fim.isoformat(timespec="seconds") if fim else None,
                  "falhas_seguidas": int(fr.get("falhas") or 0),
                  "ultima_falha": fr.get("ultima_falha"),
                  "ultimo_acionamento": fr.get("acionado_em")},
        "agenda": agenda,
        "totais": {"7d": somar(7), "30d": somar(30)},
        "alertas": alertas,
        "posts": posts,
    }


# ---------------------------------------------------------------- contas
def ler_contas(get_ig, get_fb):
    contas = {}
    if config.IG_ACCOUNT_ID and not config.SO_FACEBOOK:
        r = get_ig(config.IG_ACCOUNT_ID, {"fields": "username,followers_count,media_count"})
        if _erro(r):
            contas["instagram"] = {"erro": _erro(r)}
        else:
            c = {"usuario": r.get("username"), "seguidores": r.get("followers_count"),
                 "posts": r.get("media_count")}
            q = get_ig(f"{config.IG_ACCOUNT_ID}/content_publishing_limit", {"fields": "config,quota_usage"})
            if _erro(q):
                c["cota_erro"] = _erro(q)[:160]
            else:
                d = (q.get("data") or [{}])[0]
                c["cota_usada"] = d.get("quota_usage")
                c["cota_total"] = (d.get("config") or {}).get("quota_total")
            contas["instagram"] = c
    if config.FACEBOOK_PAGE_ID:
        r = get_fb(config.FACEBOOK_PAGE_ID, {"fields": "name,fan_count,followers_count"})
        if _erro(r):
            contas["facebook"] = {"erro": _erro(r)}
        else:
            contas["facebook"] = {"nome": r.get("name"), "curtidas_pagina": r.get("fan_count"),
                                  "seguidores": r.get("followers_count")}
    return contas


def main():
    print(f"moviki-assistente-social {config.VERSAO} — relatorio das redes")
    from src.social.facebook import Facebook

    tok = config.PAGE_ACCESS_TOKEN
    get_ig = get_fb = None
    if tok:
        get_ig = lambda c, p: _graph_get(c, p, tok)            # noqa: E731
        tok_pag = Facebook().token_pagina()
        get_fb = lambda c, p: _graph_get(c, p, tok_pag)        # noqa: E731
    contas = ler_contas(get_ig, get_fb) if tok else {}

    rel = montar(estado.ler_lista("historico.json"), datetime.now(timezone.utc),
                 get_ig, get_fb, _indice_catalogo(), contas, _indice_publicado())
    estado.gravar_lista("redes.json", rel)
    print(f"{len(rel['posts'])} posts em {DIAS_POSTS} dias | canal hoje: {rel['canal_hoje']}")
    for a in rel["alertas"]:
        print(f"[{a['nivel']}] {a['texto']}")
    print("OK -> estado/redes.json")


if __name__ == "__main__":
    main()
