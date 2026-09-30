# -*- coding: utf-8 -*-
"""
Grade editorial de videos (30/09/2026).

POR QUE EXISTE
  Ate aqui o reel saia por sorteio entre os videos do Material de apoio. Com a
  producao de video crescendo (series de live, ramos, criador), o Paulo precisa
  dizer QUAL video sai em QUAL dia, e o robo precisa garantir que video com
  prazo (dado de terceiro, campanha de data) nunca va ao ar vencido.

ONDE MORA
  conteudo/grade.json  -> a grade (editada por quem produz o video)
  video                -> asset da release `acervo` deste repo (fora do git)
  capa                 -> conteudo/acervo-capas/<id>.jpg (raw do GitHub:
                          a Meta aceita e o painel do dono mostra)

COMO O ROBO USA
  1. Video AGENDADO para hoje (campo `dias`) sai primeiro, antes de qualquer
     sorteio e antes da fatia dos criadores.
  2. Fora do dia agendado, o video entra no rodizio normal (pecas.escolher)
     junto com o Material de apoio, respeitando `repetir_apos_dias`.
  3. Fora da janela (`a_partir_de` .. `valido_ate`) ou com `reconferir_em`
     vencido, o video NAO sai. Nunca. O relatorio avisa antes.

FALHA FECHADA
  Item com campo invalido (URL fora do padrao, data mal escrita, canal
  desconhecido) fica FORA e vira alerta grave no relatorio. Grade quebrada nao
  derruba o reel: o robo segue com o Material de apoio.
"""
import json
import re
from datetime import date, datetime, timedelta

from . import compliance, config, estado
from . import util_net as net

ARQUIVO = "grade.json"
PREFIXO = "grade:"
FORMATOS = ("reel",)                       # por enquanto so video 9:16 no reel
CANAIS = ("instagram", "facebook")         # onde o robo publica
REPETIR_PADRAO = 45                        # dias entre duas saidas do mesmo video
URL_VIDEO = re.compile(r"^https://github\.com/eikosistemas-pj/moviki-assistente-social/releases/download/acervo/[a-z0-9-]+\.mp4$")
URL_CAPA = re.compile(r"^https://raw\.githubusercontent\.com/eikosistemas-pj/moviki-assistente-social/main/conteudo/acervo-capas/[a-z0-9-]+\.jpg$")
ID_OK = re.compile(r"^[a-z0-9][a-z0-9-]{2,79}$")


def _data(v):
    if v in (None, ""):
        return None
    return date.fromisoformat(str(v))


def carregar(caminho=None):
    """Le conteudo/grade.json. Arquivo ausente = grade vazia (nao e erro)."""
    caminho = caminho or (config.CONTEUDO_DIR / ARQUIVO)
    if not caminho.exists():
        return {"itens": []}
    return json.loads(caminho.read_text(encoding="utf-8"))


def validar(item):
    """Lista de problemas do item (vazia = ok)."""
    erros = []
    iid = str(item.get("id") or "")
    if not ID_OK.match(iid):
        erros.append("id invalido")
    if item.get("formato") not in FORMATOS:
        erros.append(f"formato {item.get('formato')!r} fora de {FORMATOS}")
    if not URL_VIDEO.match(str(item.get("video") or "")):
        erros.append("video fora da release acervo")
    if item.get("capa") and not URL_CAPA.match(str(item["capa"])):
        erros.append("capa fora de conteudo/acervo-capas")
    if not str(item.get("titulo") or "").strip():
        erros.append("sem titulo")
    if not str(item.get("legenda") or "").strip():
        erros.append("sem legenda")
    canais = item.get("canais") or []
    if not canais or any(c not in CANAIS for c in canais):
        erros.append(f"canais {canais!r} (aceitos: {CANAIS})")
    for campo in ("a_partir_de", "valido_ate", "reconferir_em"):
        try:
            _data(item.get(campo))
        except ValueError:
            erros.append(f"{campo} mal escrito")
    for d in item.get("dias") or []:
        try:
            _data(d)
        except ValueError:
            erros.append(f"dia {d!r} mal escrito")
    try:
        ini, fim = _data(item.get("a_partir_de")), _data(item.get("valido_ate"))
        if ini and fim and fim < ini:
            erros.append("valido_ate antes de a_partir_de")
        if not fim:
            erros.append("sem valido_ate (todo video tem prazo de revisao)")
    except ValueError:
        pass
    return erros


def situacao(item, hoje):
    """'ok' | 'antes' | 'vencido' | 'reconferir' — so para item valido."""
    ini, fim, rec = _data(item.get("a_partir_de")), _data(item.get("valido_ate")), _data(item.get("reconferir_em"))
    if rec and hoje >= rec:
        return "reconferir"
    if fim and hoje > fim:
        return "vencido"
    if ini and hoje < ini:
        return "antes"
    return "ok"


def vende_live_bloqueado(item):
    return bool(item.get("vende_live")) and not config.LIVE_NA_PAGINA


def ultima_saida(pid, hist=None):
    """Data (BR) da ultima publicacao desta peca, pelo historico."""
    hist = estado.ler_lista("historico.json") if hist is None else hist
    for linha in hist:
        if linha.get("peca") == pid:
            try:
                return datetime.fromisoformat(linha["quando"]).astimezone(config.FUSO_BR).date()
            except (KeyError, ValueError, TypeError):
                return None
    return None


def no_ar(url):
    """O arquivo existe na release? (a Meta baixa daqui; 404 derrubaria o post
    no Instagram E no Facebook). Falha de rede = trata como fora."""
    try:
        r = net.get(url, stream=True, timeout=30, allow_redirects=True)
        ok = r.status_code == 200
        r.close()
        return ok
    except Exception as e:  # noqa: BLE001
        print(f"grade: nao consegui conferir {url} ({e})")
        return False


def _legendas(item):
    ig = str(item["legenda"]).strip()
    fb = re.sub(r"(pelo|no)\s+link\s+(d|n)a\s+bio\.?", "em moviki.com.br", ig, flags=re.I)
    fb = re.sub(r"link\s+(d|n)a\s+bio\.?", "moviki.com.br", fb, flags=re.I)
    titulo = str(item["titulo"]).strip().rstrip(".")
    return (compliance.garantir(ig, f"{titulo}.\n\nConheça pelo link da bio."),
            compliance.garantir(fb, f"{titulo}.\n\nConheça em moviki.com.br"))


def peca(item):
    """Item da grade no formato comum das pecas (src/pecas.py)."""
    ig, fb = _legendas(item)
    return {
        "id": PREFIXO + item["id"], "origem": "grade", "formato": item["formato"], "midia": "video",
        "url": item["video"], "capa": item.get("capa") or None,
        "titulo": item["titulo"], "angulo": "", "tipo_pauta": item.get("tipo_pauta") or "conversao",
        "categoria": item.get("ramo") or "geral", "pilar": item.get("pilar") or "",
        "legenda_ig": ig, "legenda_fb": fb, "criador": None,
        "agendado": list(item.get("dias") or []),
    }


def validos(dados=None):
    """(itens_validos, problemas) — problemas = [(id, [erros])]."""
    dados = carregar() if dados is None else dados
    ok, ruins = [], []
    for it in dados.get("itens") or []:
        e = validar(it)
        (ruins.append((it.get("id") or "?", e)) if e else ok.append(it))
    return ok, ruins


def agendada_hoje(formato, hoje=None, dados=None, hist=None, conferir=no_ar):
    """Peca agendada para hoje neste formato que ainda nao saiu hoje. None se nao houver.
    `conferir(url)` confirma que o video esta na release antes de mandar para a Meta."""
    hoje = hoje or config.hoje_br()
    itens, _ = validos(dados)
    for it in itens:
        if it["formato"] != formato or hoje.isoformat() not in (it.get("dias") or []):
            continue
        if situacao(it, hoje) != "ok" or vende_live_bloqueado(it):
            print(f"grade: {it['id']} agendado para hoje mas {situacao(it, hoje)} -> nao sai")
            continue
        if ultima_saida(PREFIXO + it["id"], hist) == hoje:
            continue
        if conferir and not conferir(it["video"]):
            print(f"grade: {it['id']} agendado para hoje mas o video NAO esta na release acervo -> sorteio normal")
            continue
        return peca(it)
    return None


def rodizio(formato, hoje=None, dados=None, hist=None, conferir=no_ar):
    """Pecas da grade que podem entrar no rodizio hoje (fora do dia agendado)."""
    hoje = hoje or config.hoje_br()
    itens, _ = validos(dados)
    saida = []
    for it in itens:
        if it["formato"] != formato or it.get("so_agendado"):
            continue
        if situacao(it, hoje) != "ok" or vende_live_bloqueado(it):
            continue
        # agendado no futuro proximo: guarda para o dia marcado
        if any(hoje < _data(d) <= hoje + timedelta(days=14) for d in (it.get("dias") or [])):
            continue
        ult = ultima_saida(PREFIXO + it["id"], hist)
        if ult and (hoje - ult).days < int(it.get("repetir_apos_dias") or REPETIR_PADRAO):
            continue
        if conferir and not conferir(it["video"]):
            continue
        saida.append(peca(it))
    return saida


def relatorio(hoje, dados=None, hist=None, dia_de=None, dias=14, conferir=no_ar):
    """Bloco `grade` do estado/redes.json + alertas. dia_de(formato, dia) = posts esperados."""
    alertas = []
    try:
        dados = carregar() if dados is None else dados
    except (ValueError, OSError) as e:
        return {"erro": f"grade.json ilegivel: {str(e)[:120]}", "proximos": [], "acervo": 0}, [
            {"nivel": "grave", "tipo": "grade", "texto": "conteudo/grade.json ilegível: nenhum vídeo da grade sai até corrigir."}]
    itens, ruins = validos(dados)
    for iid, erros in ruins:
        alertas.append({"nivel": "grave", "tipo": "grade",
                        "texto": f"Grade: o vídeo {iid} está fora por erro de cadastro ({'; '.join(erros)[:160]})."})
    proximos, vencendo = [], []
    for it in itens:
        sit = situacao(it, hoje)
        fim, rec = _data(it.get("valido_ate")), _data(it.get("reconferir_em"))
        if sit == "reconferir":
            alertas.append({"nivel": "grave", "tipo": "grade",
                            "texto": f"Grade: {it['titulo']} passou da data de reconferir ({rec.strftime('%d/%m')}) e parou de sair. Reconfira o vídeo ou tire da grade."})
        elif sit == "vencido":
            pass  # venceu = saiu da grade; nao e alarme, so some
        else:
            datas = [x for x in (fim, rec) if x]
            limite = min(datas) if datas else None
            if limite and 0 <= (limite - hoje).days <= 7:
                vencendo.append({"id": it["id"], "titulo": it["titulo"], "ate": limite.isoformat()})
                alertas.append({"nivel": "atencao", "tipo": "grade",
                                "texto": f"Grade: {it['titulo']} sai de circulação em {limite.strftime('%d/%m')}. Renove ou deixe vencer."})
        for d in it.get("dias") or []:
            dia = _data(d)
            if not (hoje <= dia < hoje + timedelta(days=dias)):
                continue
            s = situacao(it, dia)
            bloq = vende_live_bloqueado(it)
            sem_slot = bool(dia_de) and dia_de(it["formato"], dia) == 0
            proximos.append({"dia": dia.isoformat(), "hoje": dia == hoje, "id": it["id"], "titulo": it["titulo"],
                             "formato": it["formato"], "pilar": it.get("pilar") or "", "capa": it.get("capa") or "",
                             "sai": s == "ok" and not bloq and not sem_slot,
                             "motivo": ("sem " + it["formato"] + " nesse dia") if sem_slot else
                                       ("live fora da página" if bloq else ("" if s == "ok" else s))})
            if not sem_slot and s == "ok" and not bloq and conferir and not conferir(it["video"]):
                proximos[-1].update(sai=False, motivo="vídeo não está na release acervo")
                alertas.append({"nivel": "grave", "tipo": "grade",
                                "texto": f"Grade: {it['titulo']} está marcado para {dia.strftime('%d/%m')}, mas o vídeo não está na release acervo do GitHub. Suba o arquivo {it['id']}.mp4."})
            if sem_slot:
                alertas.append({"nivel": "grave", "tipo": "grade",
                                "texto": f"Grade: {it['titulo']} está marcado para {dia.strftime('%d/%m')}, dia sem {it['formato']} no calendário. Não vai sair."})
            elif s != "ok":
                alertas.append({"nivel": "grave", "tipo": "grade",
                                "texto": f"Grade: {it['titulo']} está marcado para {dia.strftime('%d/%m')}, mas estará {s} nesse dia. Não vai sair."})
    proximos.sort(key=lambda x: x["dia"])
    vigentes = [it for it in itens if situacao(it, hoje) == "ok"]
    return {"versao": dados.get("versao", ""), "acervo": len(itens), "no_ar": len(vigentes), "com_erro": len(ruins),
            "proximos": proximos, "vencendo": vencendo}, alertas
