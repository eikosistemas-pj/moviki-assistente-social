# -*- coding: utf-8 -*-
"""
Grade de STORIES (17/10/2026) — escolha, montagem e publicacao.

ANTES (22/09 a 16/10/2026)
  2 rodadas por dia, cada uma soltava a arte do dia + o story estatico
  "Responda LIVE". Resultado: a mesma cartela 2x por dia, tudo parado e sem
  som, e as 2 unicas pecas de criador revezando a cada 2 dias.

AGORA
  - 5 rodadas por dia (.github/workflows/story.yml).
  - TIPO alterna pelo historico: depois de VIDEO vem ARTE e vice-versa.
      VIDEO = corte de 9-20 s de um video do Material de apoio ou do acervo
              da grade (so os que ja estrearam como reel), cortado na pausa
              da fala; cada rodada usa o proximo corte do mesmo video.
      ARTE  = arte 9:16 do Material de apoio (ou de criador), animada com
              zoom lento + trilha baixa.
  - Nunca o mesmo ramo em seguida, quando houver alternativa.
  - CHAMADA "Responda LIVE": faixa discreta por cima do proprio story, nos
    ultimos ~4 s, logo acima da caixa "Enviar mensagem"; so nos stories de
    VIDEO (a arte ja tem o proprio botao), entao sai um sim, outro nao (so no
    Instagram). Responder LIVE cai no direct e dispara o Funil
    LIVE do ManyChat (gatilho de resposta de story). Acabou a tela cheia.
  - Peca de CRIADOR: so volta depois de CRIADOR_QUARENTENA_DIAS.
  - Facebook recebe a mesma montagem SEM a chamada (o ManyChat so esta
    ligado no Instagram).
  - Videos montados sobem como asset temporario do Release `stories` e sao
    apagados dois dias depois (video nao entra no repositorio).

NUNCA QUEBRA
  Montagem falhou -> publica a peca original (arte parada), como antes.
"""
from datetime import datetime, timedelta, timezone

from . import cartela, config, estado, grade, material, pecas, story_video, triagem
from . import util_net as net

TAG = "stories"


class MontagemFalhou(RuntimeError):
    """O corte de video nao saiu: quem chamou cai numa arte."""

GUARDAR_DIAS = 2
CRIADOR_QUARENTENA_DIAS = 7
EST_VIDEO = "pecas_storyvideo"
EST_TRILHA = "trilhas_story"
EST_CORTES = "story_cortes.json"


# ------------------------------------------------------------------ historico
def _stories(hist=None):
    hist = estado.ler_lista("historico.json") if hist is None else hist
    return [h for h in hist if h.get("formato") == "story"]


def proximo_tipo(hist=None):
    """'video' ou 'arte', alternando com o ultimo story publicado."""
    st = _stories(hist)
    if not st:
        return "video"
    return "arte" if st[0].get("tipo") == "video" else "video"


def precisa_cta(tipo):
    """Chamada so no story de VIDEO (a faixa cobriria o rodape da arte, que
    ja tem o proprio botao). Como video e arte alternam, sai um sim, outro nao."""
    return bool(config.CARTELA_STORY) and tipo == "video"


def ultimo_ramo(hist=None):
    st = _stories(hist)
    return st[0].get("ramo") if st else None


def _publicada_ha(pid, dias, hist=None, agora=None):
    agora = agora or datetime.now(timezone.utc)
    for h in _stories(hist):
        if h.get("peca") != pid:
            continue
        try:
            return agora - datetime.fromisoformat(h["quando"]) < timedelta(days=dias)
        except (KeyError, ValueError, TypeError):
            return False
    return False


def sem_repetir_ramo(lista, ramo):
    if not ramo or ramo == "geral":
        return lista
    outras = [p for p in lista if p.get("categoria") != ramo]
    return outras or lista


# ------------------------------------------------------------------ fontes
def videos_da_casa():
    """Videos verticais que podem virar story: Material de apoio + acervo da
    grade que ja estreou como reel (nunca estragar a estreia)."""
    saida = []
    try:
        for p in triagem.filtrar(material.pecas(material.carregar_catalogo(), "reel")):
            if (p.get("duracao") or 0) < story_video.VIDEO_MIN:
                continue
            if p.get("w") and p.get("h") and p["h"] < p["w"]:
                continue
            saida.append(dict(p, id="video:" + p["id"], fonte_id=p["id"], formato="story"))
    except Exception as e:  # noqa: BLE001
        print(f"AVISO: material de apoio indisponivel ({e})")
    try:
        hoje = config.hoje_br()
        itens, _ = grade.validos()
        for it in itens:
            if it.get("formato") != "reel" or not it.get("video"):
                continue
            if grade.situacao(it, hoje) != "ok" or grade.vende_live_bloqueado(it):
                continue
            if not grade.ultima_saida(grade.PREFIXO + it["id"]):
                continue
            p = grade.peca(it)
            saida.append(dict(p, id="video:grade:" + it["id"], fonte_id=p["id"], formato="story",
                              origem="grade"))
    except Exception as e:  # noqa: BLE001
        print(f"AVISO: grade indisponivel ({e})")
    return saida


def _filtrar_criadores(grupos, hist=None):
    grupos["criador"] = [p for p in grupos.get("criador") or []
                         if not _publicada_ha(p["id"], CRIADOR_QUARENTENA_DIAS, hist)]
    return grupos


def _ultima_vez(pid, hist=None):
    for h in _stories(hist):
        if h.get("peca") == pid:
            try:
                return datetime.fromisoformat(h["quando"])
            except (KeyError, ValueError, TypeError):
                return None
    return None


def fixa_da_vez(lista, hist=None, agora=None):
    """Arte FIXA do story (config.STORY_FIXAS, 18/10/2026) que ja passou do
    intervalo desde a ultima vez. Inedita conta como vencida. Com mais de uma,
    vai a que esta ha mais tempo sem sair."""
    vencidas = [p for p in lista
                if p.get("id") in config.STORY_FIXAS
                and not _publicada_ha(p["id"], config.STORY_FIXAS[p["id"]], hist, agora)]
    if not vencidas:
        return None
    antiga = datetime.min.replace(tzinfo=timezone.utc)
    return min(vencidas, key=lambda p: _ultima_vez(p["id"], hist) or antiga)


def escolher_arte(forcar_origem=None, hist=None):
    grupos = _filtrar_criadores(pecas.candidatas("story"), hist)
    origem = forcar_origem or pecas.escolher_origem("story", grupos)
    if forcar_origem != "criador":
        fixa = fixa_da_vez(grupos.get("casa") or [], hist)
        if fixa:
            print(f"story: arte fixa {fixa['id']} (a cada {config.STORY_FIXAS[fixa['id']]} dias)")
            return fixa
    lista = grupos.get(origem) or []
    if not lista and not forcar_origem:
        origem = "casa" if origem == "criador" else "criador"
        lista = grupos.get(origem) or []
    lista = sem_repetir_ramo(lista, ultimo_ramo(hist))
    return pecas.escolher(lista, estado.recentes(pecas._estado("story")))


def escolher_video(hist=None):
    lista = sem_repetir_ramo(videos_da_casa(), ultimo_ramo(hist))
    print(f"story video: {len(lista)} videos candidatos")
    return pecas.escolher(lista, estado.recentes(EST_VIDEO))


# ------------------------------------------------------------------ cortes
def _cortes_estado():
    p = config.ESTADO_DIR / EST_CORTES
    if not p.exists():
        return {}
    try:
        import json
        d = json.loads(p.read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except Exception:  # noqa: BLE001
        return {}


def _gravar_cortes(d):
    import json
    config.ESTADO_DIR.mkdir(parents=True, exist_ok=True)
    (config.ESTADO_DIR / EST_CORTES).write_text(json.dumps(d, ensure_ascii=False, indent=1),
                                               encoding="utf-8")


def proximo_corte(pid, total):
    """Indice do corte desta vez (gira pelos cortes do video)."""
    if total <= 0:
        return 0
    return int(_cortes_estado().get(pid, 0)) % total


def avancar_corte(pid, usado, total):
    d = _cortes_estado()
    d[pid] = (usado + 1) % max(total, 1)
    _gravar_cortes(d)


# ------------------------------------------------------------------ release
def _url_final(url):
    """O Release responde com redirecionamento; a Meta recebe o endereco final."""
    try:
        import requests
        r = requests.get(url, allow_redirects=False, timeout=30)
        if r.status_code in (301, 302, 303, 307, 308) and r.headers.get("Location", "").startswith("https://"):
            return r.headers["Location"]
    except Exception:  # noqa: BLE001
        pass
    return url


def hospedar(caminho, nome):
    h = cartela._cabecalhos()
    rid = cartela._release_id(h, TAG)
    return cartela._subir(h, rid, caminho, nome)["browser_download_url"]


def limpar_release(agora=None):
    """Apaga stories montados com mais de GUARDAR_DIAS (a Meta ja copiou)."""
    agora = agora or datetime.now(timezone.utc)
    try:
        h = cartela._cabecalhos()
        rid = cartela._release_id(h, TAG)
        for a in cartela._assets(h, rid):
            try:
                criado = datetime.fromisoformat(a["created_at"].replace("Z", "+00:00"))
            except (KeyError, ValueError):
                continue
            if agora - criado > timedelta(days=GUARDAR_DIAS):
                cartela.apagar(a.get("id"))
    except Exception as e:  # noqa: BLE001
        print(f"story: limpeza do release adiada ({net.sem_segredo(e)})")


# ------------------------------------------------------------------ montagem
def _baixar(url, destino):
    r = net.get(url, timeout=180)
    if r.status_code != 200 or len(r.content) < 10000:
        raise RuntimeError(f"download: HTTP {r.status_code}")
    with open(destino, "wb") as f:
        f.write(r.content)
    return destino


def montar(peca, cta, hist=None):
    """Monta as versoes do story. Devolve dict com 'ig' e 'fb' (caminhos
    locais), 'trilha', 'corte' e 'tipo'. Levanta excecao se falhar."""
    exe = cartela._ffmpeg()
    if not exe:
        raise RuntimeError("ffmpeg indisponivel")
    pasta = story_video.pasta_temp()
    trilha = story_video.escolher_trilha(estado.recentes(EST_TRILHA))
    info = {"trilha": trilha.stem if trilha else None}
    cta_img = story_video.salvar_cta(f"{config.hoje_br().isoformat()}-{peca['id']}", pasta) if cta else None

    if peca.get("tipo") == "video":
        fonte = _baixar(peca["url"], str(pasta / "fonte.mp4"))
        an = story_video.analisar(fonte, exe)
        if not an["cortes"]:
            raise RuntimeError("video curto demais")
        i = proximo_corte(peca["id"], len(an["cortes"]))
        ini, fim = an["cortes"][i]
        info.update(tipo="video", corte=f"{ini:.1f}-{fim:.1f}", corte_i=i, cortes=len(an["cortes"]))
        base = dict(video=fonte, ini=ini, fim=fim, trilha=trilha, fundo=an["fundo"], audio=an["audio"], exe=exe)
    else:
        img = pecas._baixar_imagem(peca["url"])
        if peca.get("credito"):
            img = pecas._selo_credito(img, peca["credito"].split(" ", 1)[-1])
        caminho = story_video.arte.salvar(img, str(pasta / "arte.jpg"))
        info.update(tipo="arte")
        base = dict(imagem=caminho, trilha=trilha, exe=exe)

    info["fb"] = story_video.montar(str(pasta / "story-fb.mp4"), cta=None, **base)
    info["ig"] = story_video.montar(str(pasta / "story-ig.mp4"), cta=cta_img, **base) if cta else info["fb"]
    print(f"story: montado {info['tipo']} | trilha {info['trilha']} | corte {info.get('corte', '-')}"
          f" | chamada {'sim' if cta else 'nao'}")
    return info


# ------------------------------------------------------------------ fluxo
def escolher(forcar_origem=None, hist=None):
    """(peca, tipo). Grade agendada para hoje vence tudo."""
    if forcar_origem != "criador":
        try:
            ag = grade.agendada_hoje("story")
        except Exception as e:  # noqa: BLE001
            ag = None
            print(f"AVISO: grade indisponivel ({e})")
        if ag:
            return dict(ag, tipo="video" if ag.get("midia") == "video" else "arte")
    tipo = "arte" if forcar_origem == "criador" else proximo_tipo(hist)
    if tipo == "video":
        p = escolher_video(hist)
        if p:
            return dict(p, tipo="video")
        print("story: sem video disponivel -> arte")
    p = escolher_arte(forcar_origem, hist)
    return dict(p, tipo="arte") if p else None


def publicar(peca, hist=None):
    """Publica o story montado (ou o original, se a montagem falhar)."""
    from . import freio
    from .social.facebook import Facebook, espelhar_formato
    from .social.instagram import Instagram

    cta = precisa_cta(peca.get("tipo"))
    try:
        info = montar(peca, cta, hist)
    except Exception as e:  # noqa: BLE001
        print(f"story: montagem falhou ({net.sem_segredo(e)}) -> peca original")
        info = None
    if info is None:
        if peca.get("tipo") == "video":
            raise MontagemFalhou(peca["id"])
        return pecas.publicar(dict(peca, formato="story"))

    extra = {"tipo": info["tipo"], "cta": cta, "trilha": info["trilha"]}
    if info.get("corte"):
        extra["corte"] = info["corte"]
    if config.DRY_RUN:
        print(f"DRY_RUN: Instagram {info['ig']} | Facebook {info['fb']}")
        print("DRY_RUN ligado -> nada foi publicado.")
        return None

    carimbo = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    nome = story_video.nome_seguro(peca["id"])
    url_fb = hospedar(info["fb"], f"story-{carimbo}-{nome}-fb.mp4")
    url_ig = url_fb if info["ig"] == info["fb"] else hospedar(info["ig"], f"story-{carimbo}-{nome}.mp4")
    # Capa .webp (padrao das capas do material desde 26/09) nao serve de capa do
    # Instagram, mas serve de miniatura no painel: sem ela o story de video
    # aparecia "Sem miniatura".
    mini = {"miniatura": peca.get("capa") or peca.get("capa_triagem")
            or (peca["url"] if info["tipo"] == "arte" else "")}
    no_ig = freio.no_instagram("story")

    def _final():
        if info["tipo"] == "video":
            avancar_corte(peca["id"], info["corte_i"], info["cortes"])
        if info["trilha"]:
            estado.marcar_usado(EST_TRILHA, info["trilha"], janela=20)
        if info["tipo"] == "video":
            estado.marcar_usado(EST_VIDEO, peca["id"], janela=pecas.JANELA)

    if not no_ig:
        mid = Facebook().story_video(_url_final(url_fb))
        pecas.marcar(peca, mid, "facebook", dict(mini, **extra, cta=False))
        _final()
        return mid
    try:
        mid = Instagram(ia=peca.get("origem") != "criador").story_video(_url_final(url_ig))
    except Exception as e:  # noqa: BLE001
        print(f"AVISO: Instagram falhou ({e}) -> publicando no Facebook.")
        mid = Facebook().story_video(_url_final(url_fb))
        pecas.marcar(peca, mid, "facebook", dict(mini, **extra, cta=False, planoB=True,
                                                 erroInstagram=str(e)[:200]))
        freio.falhou("story", e)
        pecas.alarme_instagram("story", e)
        _final()
        return mid
    freio.sucesso()
    print(f"OK -> Instagram | story {info['tipo']} | {peca['id']} | id: {mid}")
    fid = espelhar_formato("story", "video", _url_final(url_fb))
    pecas.marcar(peca, mid, "instagram", dict(mini, **extra, **({"fb": fid} if fid else {})))
    _final()
    return mid


def rodar(forcar_origem=None):
    hist = estado.ler_lista("historico.json")
    peca = escolher(forcar_origem, hist)
    if not peca:
        print("nenhum story publicavel agora -> nada a publicar.")
        return None
    print(f"story: {peca['tipo']} | {peca['id']} ({peca.get('origem')}, {peca.get('categoria')})")
    try:
        mid = publicar(dict(peca, formato="story"), hist)
    except MontagemFalhou:
        arte_p = escolher_arte(forcar_origem, hist)
        if not arte_p:
            print("story: corte falhou e nao ha arte -> nada a publicar.")
            return None
        print(f"story: corte falhou -> arte {arte_p['id']}")
        mid = publicar(dict(arte_p, formato="story", tipo="arte"), hist)
    if not config.DRY_RUN:
        limpar_release()
    return mid

