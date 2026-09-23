# -*- coding: utf-8 -*-
"""
Escolha da peca de cada publicacao — feed, story e reel — entre as fontes.

FONTES (22/09/2026)
  casa     = Material de apoio do parceiro (src/material.py)
             + banco de Reels do repo (conteudo/reels.md), so para reel
  criador  = pecas de influenciador AUTORIZADAS por ele e APROVADAS pelo
             Moviki (src/criadores.py). Desligada ate existir CRIADORES_URL.

MISTURA
  Com peca de criador disponivel, ela fica com CRIADORES_PARTICIPACAO dos
  ultimos 4 posts daquele formato (padrao: metade). O resto sai da casa. Sem
  peca de criador, 100% casa — a brecha fechada nao muda nada no robo.

ROTACAO
  Peca inedita primeiro; depois a usada ha mais tempo. Nunca o mesmo ramo
  (casa) nem o mesmo criador duas vezes seguidas quando houver alternativa.
"""
import io
import re

from PIL import Image, ImageDraw

from . import arte, config, conteudo, criadores, estado, hospedagem, ia, material
from . import util_net as net

JANELA = 500


# ------------------------------------------------------------------ banco de reels
def banco_reels():
    """Reels do conteudo/reels.md (asset de release), no formato comum."""
    caminho = config.CONTEUDO_DIR / "reels.md"
    if not caminho.exists():
        return []
    texto = conteudo.sem_comentarios(caminho.read_text(encoding="utf-8"))
    saida = []
    for bloco in re.split(r"^##\s+", texto, flags=re.M)[1:]:
        linhas = bloco.strip().splitlines()
        if not linhas:
            continue
        r = {"id": linhas[0].strip()}
        for linha in linhas[1:]:
            m = re.match(r"^\s*(\w+)\s*:\s*(.+)$", linha)
            if m and m.group(1).lower() in ("tipo", "url", "capa", "titulo", "angulo"):
                r[m.group(1).lower()] = m.group(2).strip()
        url = r.get("url", "")
        if not url.startswith("https://") or "<owner>" in url:
            continue
        saida.append({
            "id": f"banco:{r['id']}", "origem": "banco", "formato": "reel", "midia": "video",
            "url": url, "capa": r.get("capa") if str(r.get("capa", "")).startswith("https://") else None,
            "titulo": r.get("titulo", r["id"]), "angulo": r.get("angulo", ""),
            "tipo_pauta": r.get("tipo", "educativo"), "categoria": "geral",
            "legenda_ig": None, "legenda_fb": None, "criador": None,
        })
    return saida


# ------------------------------------------------------------------ fontes
def candidatas(formato):
    """{'casa': [...], 'criador': [...]} para o formato. Fonte que falha nao
    derruba as outras."""
    casa, cria = [], []
    try:
        casa = material.pecas(material.carregar_catalogo(), formato)
    except Exception as e:  # noqa: BLE001
        print(f"AVISO: material de apoio indisponivel ({e})")
    if formato == "reel":
        casa += banco_reels()
    if criadores.ativa():
        try:
            cria = criadores.pecas(criadores.carregar(), formato)
        except Exception as e:  # noqa: BLE001
            print(f"AVISO: pecas de criadores indisponiveis ({e}) -> so material")
    print(f"{formato}: {len(casa)} pecas da casa | {len(cria)} de criadores")
    return {"casa": casa, "criador": cria}


def _ultimas_origens(formato, n=4):
    ult = [h for h in estado.ler_lista("historico.json") if h.get("formato") == formato]
    return [h.get("origem", "casa") for h in ult[:n]]


def escolher_origem(formato, grupos, historico_origens=None):
    if not grupos["criador"]:
        return "casa"
    if not grupos["casa"]:
        return "criador"
    ult = _ultimas_origens(formato) if historico_origens is None else historico_origens
    fatia = (ult.count("criador") / len(ult)) if ult else 0.0
    return "criador" if fatia < config.CRIADORES_PARTICIPACAO else "casa"


def _estado(formato):
    return f"pecas_{formato}"


def escolher(lista, recentes):
    """Inedita primeiro; senao a mais antiga. Evita repetir ramo/criador."""
    if not lista:
        return None
    ultima = next((p for p in lista if recentes and p["id"] == recentes[0]), None)

    def idade(p):
        return len(recentes) + 1 if p["id"] not in recentes else recentes.index(p["id"])

    def repete(p):
        if not ultima:
            return False
        if p["origem"] == "criador" and ultima["origem"] == "criador":
            return (p["criador"] or {}).get("uid") == (ultima["criador"] or {}).get("uid")
        return p.get("categoria") not in (None, "geral") and p.get("categoria") == ultima.get("categoria")

    ordem = sorted(lista, key=idade, reverse=True)
    for p in ordem:
        if not repete(p):
            return p
    return ordem[0]


def escolher_peca(formato, forcar_origem=None):
    grupos = candidatas(formato)
    origem = forcar_origem or escolher_origem(formato, grupos)
    lista = grupos.get(origem) or []
    if not lista and not forcar_origem:
        origem = "casa" if origem == "criador" else "criador"
        lista = grupos.get(origem) or []
    peca = escolher(lista, estado.recentes(_estado(formato)))
    if peca:
        print(f"{formato}: peca {peca['id']} ({peca['origem']}, {peca.get('categoria')})")
    return peca


def marcar(peca, media_id, rede, extra=None):
    estado.marcar_usado(_estado(peca["formato"]), peca["id"], janela=JANELA)
    dados = {"origem": "criador" if peca["origem"] == "criador" else "casa",
             "peca": peca["id"], "rede": rede}
    if peca.get("criador"):
        dados["criador"] = peca["criador"].get("uid")
    if extra:
        dados.update(extra)
    estado.registrar(peca["formato"], peca.get("titulo") or peca["id"], media_id, dados)


# ------------------------------------------------------------------ legendas
def legendas(peca, hashtags_tipo="conversao"):
    """(legenda_ig, legenda_fb). Banco de reels escreve pela IA na hora."""
    if peca.get("legenda_ig") and peca.get("legenda_fb"):
        return peca["legenda_ig"], peca["legenda_fb"]
    titulo = peca.get("titulo", "")
    res_ig = f"{titulo}\n\nO Moviki mostra onde os negócios estão agora.\nConheça pelo link da bio."
    res_fb = f"{titulo}\n\nO Moviki mostra onde os negócios estão agora.\nConheça em moviki.com.br"
    ig = ia.escrever(
        f"Escreva a legenda de um Reel do Moviki.\n\nAssunto do video: {titulo}\n"
        f"Angulo: {peca.get('angulo', '')}\n\nPrimeira linha precisa segurar a atencao "
        f"de quem esta rolando o feed. Feche com chamada pra acao mandando pro link da bio.",
        res_ig,
    )
    fb = re.sub(r"(pelo|no)\s+link\s+(d|n)a\s+bio\.?", "em moviki.com.br", ig, flags=re.I)
    fb = re.sub(r"link\s+(d|n)a\s+bio\.?", "moviki.com.br", fb, flags=re.I)
    from . import compliance
    return ig, compliance.garantir(fb, res_fb)


# ------------------------------------------------------------------ midia
def _baixar_imagem(url):
    r = net.get(url, timeout=40)
    if r.status_code != 200 or len(r.content) < 5000:
        raise RuntimeError(f"imagem: HTTP {r.status_code}")
    img = Image.open(io.BytesIO(r.content))
    img.load()
    img = img.convert("RGB")
    if img.width > 1440:
        img = img.resize((1440, int(img.height * 1440 / img.width)), Image.LANCZOS)
    return img


def _selo_credito(img, texto):
    """Chip discreto com o credito do criador, acima da area de resposta do story."""
    d = ImageDraw.Draw(img)
    f = arte._fonte(config.FONTE_FORTE, int(img.width * 0.03))
    w = arte._largura(d, texto, f)
    x0 = (img.width - w) // 2 - 28
    y0 = int(img.height * 0.82)
    d.rounded_rectangle((x0, y0, x0 + w + 56, y0 + f.size + 30), radius=(f.size + 30) // 2,
                        fill=(3, 16, 48))
    d.text((x0 + 28, y0 + 12), texto, font=f, fill=(255, 255, 255))
    return img


def url_publica(peca):
    """URL que a Meta consegue baixar, no formato que ela aceita.

    - video: vai direto (a Meta baixa do endereco de origem).
    - story do material em JPG: vai direto (app.moviki.com.br e publico).
    - o resto (feed de qualquer fonte, story de criador): baixa, confere,
      regrava em JPEG — o Instagram so aceita JPEG — e hospeda em publicado/.
      Story de criador ganha o selo de credito.
    """
    if peca["midia"] == "video":
        return peca["url"]
    if (peca["formato"] == "story" and peca["origem"] == "material"
            and peca["url"].lower().endswith((".jpg", ".jpeg"))):
        return peca["url"]
    img = _baixar_imagem(peca["url"])
    if peca["formato"] == "story" and peca.get("credito"):
        img = _selo_credito(img, peca["credito"].split(" ", 1)[-1])
    caminho = arte.salvar(img, f"/tmp/{peca['formato']}-{peca['origem']}.jpg")
    if config.DRY_RUN:
        print(f"DRY_RUN: arte preparada em {caminho} (nao hospedada)")
        return caminho
    return hospedagem.publicar_arquivo(caminho, prefixo=f"{peca['formato']}-{peca['origem']}")


def imagem_local(peca):
    """Imagem RGB da peca (usada pelo feed, que ja tem o proprio fluxo de hospedagem)."""
    return _baixar_imagem(peca["url"])


# ------------------------------------------------------------------ publicacao
def publicar(peca, hashtags=""):
    """Publica story ou reel no canal certo e registra. Devolve o id.

    SO_FACEBOOK ligado -> Pagina do Facebook e o canal (falha derruba).
    Desligado          -> Instagram principal; Facebook espelho best-effort;
                          Instagram falhou -> Facebook como plano B.
    """
    from .social.facebook import Facebook, espelhar_formato
    from .social.instagram import Instagram

    formato, midia = peca["formato"], peca["midia"]
    leg_ig = leg_fb = ""
    if formato == "reel":
        leg_ig, leg_fb = legendas(peca)
    url = url_publica(peca)

    print(f"--- {formato} | {peca['origem']} | {peca['id']} ---")
    print(f"midia: {url}")
    if formato == "reel":
        print("--- legenda (Facebook) ---" if config.SO_FACEBOOK else "--- legenda ---")
        print(leg_fb if config.SO_FACEBOOK else leg_ig)
        print("--------------------------")

    if config.DRY_RUN:
        print("DRY_RUN ligado -> nada foi publicado.")
        return None

    def no_facebook():
        fb = Facebook()
        if formato == "reel":
            return fb.reel(url, leg_fb)
        return fb.story_video(url) if midia == "video" else fb.story_foto(url)

    if config.SO_FACEBOOK:
        mid = no_facebook()
        marcar(peca, mid, "facebook")
        print(f"OK -> Facebook | {formato} | {peca['id']} | id: {mid}")
        return mid

    try:
        ig = Instagram()
        if formato == "reel":
            mid = ig.reel(url, leg_ig, hashtags, capa_url=peca.get("capa"))
        else:
            mid = ig.story_video(url) if midia == "video" else ig.story(url)
    except Exception as e:  # noqa: BLE001
        print(f"AVISO: Instagram falhou ({e}) -> publicando no Facebook.")
        mid = no_facebook()
        marcar(peca, mid, "facebook", {"planoB": True})
        return mid

    marcar(peca, mid, "instagram")
    print(f"OK -> Instagram | {formato} | {peca['id']} | id: {mid}")
    espelhar_formato(formato, midia, url, leg_fb)
    return mid
