# -*- coding: utf-8 -*-
"""
Compositor de arte (Pillow) — PADRAO MOVIKI.

MUDANCA DE 22/09/2026 (padronizacao do feed):
  Ate aqui o robo escrevia por cima de fotos do banco assets/fundos e
  pintava etiqueta e link na COR DO LOJISTA. Resultado no ar: cada post de
  um jeito (laranja, verde, ciano), fundo sem relacao com o negocio (loja
  de suplemento sobre foto de vendedor de carrinho) e texto brigando com o
  rosto da pessoa na foto.

  Agora TODA arte composta pelo robo sai na identidade do Material de apoio
  do parceiro: azul-marinho, mapa neon, pinos ciano, botao verde, logo do
  Moviki no topo. A cor do lojista nao entra mais — quem aparece e o
  lojista (logo, nome, ramo, cidade, link), a moldura e sempre do Moviki.

  O banco assets/fundos foi APOSENTADO. O fundo e desenhado em codigo:
  nunca sai torto, nunca traz marca de terceiro, nunca repete foto de
  pessoa, e custa zero.

DECISAO QUE CONTINUA: nenhuma imagem e gerada por IA na hora de publicar.
As pecas prontas vem do Material de apoio (src/material.py), revisadas antes
de subir; o que o robo compoe aqui usa so dados reais do negocio.
"""
import io
import math
import os
import random

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

from . import config

FEED = (1080, 1350)      # 4:5 — o mesmo formato da maioria das pecas do material
QUADRADO = (1080, 1080)
STORY = (1080, 1920)

# ------------------------------------------------------------------ paleta
# Amostrada das pecas do Material de apoio (moviki-app/material/feed).
MARINHO_TOPO = (4, 24, 72)
MARINHO_BASE = (0, 6, 28)
RUA = (18, 70, 170)
CIANO = (2, 225, 255)
AZUL = (30, 144, 255)
VERDE = (0, 217, 104)
TINTA = (3, 16, 48)          # texto escuro sobre ciano/verde
BRANCO = (255, 255, 255)
CINZA_AZUL = (170, 195, 235)


# ------------------------------------------------------------------ utilidades
def _fonte(caminho, tamanho):
    try:
        return ImageFont.truetype(str(caminho), tamanho)
    except Exception:
        return ImageFont.load_default()


def _largura(draw, texto, fonte):
    x0, _, x1, _ = draw.textbbox((0, 0), texto, font=fonte)
    return x1 - x0


def _quebrar(draw, texto, fonte, largura_max):
    """Quebra por palavra respeitando a largura em pixels."""
    palavras = (texto or "").split()
    if not palavras:
        return []
    linhas, atual = [], palavras[0]
    for p in palavras[1:]:
        teste = f"{atual} {p}"
        if _largura(draw, teste, fonte) <= largura_max:
            atual = teste
        else:
            linhas.append(atual)
            atual = p
    linhas.append(atual)
    return linhas


def _caber(draw, texto, caminho, largura_max, maior, menor, max_linhas):
    """Maior fonte em que o texto cabe em `max_linhas` sem palavra estourando."""
    tam = maior
    while tam >= menor:
        f = _fonte(caminho, tam)
        linhas = _quebrar(draw, texto, f, largura_max)
        if len(linhas) <= max_linhas and all(_largura(draw, l, f) <= largura_max for l in linhas):
            return f, linhas
        tam -= 4
    f = _fonte(caminho, menor)
    return f, _quebrar(draw, texto, f, largura_max)[:max_linhas]


def _centro(draw, y, texto, fonte, cor, largura):
    w = _largura(draw, texto, fonte)
    draw.text(((largura - w) // 2, y), texto, font=fonte, fill=cor)


# ------------------------------------------------------------------ fundo
def _pino(draw, cx, cy, h, cor):
    """Pino de mapa (gota invertida) com furo no meio."""
    r = h * 0.36
    draw.ellipse((cx - r, cy - h, cx + r, cy - h + 2 * r), fill=cor)
    draw.polygon([(cx - r * 0.82, cy - h + r * 1.45), (cx + r * 0.82, cy - h + r * 1.45), (cx, cy)], fill=cor)
    f = r * 0.42
    draw.ellipse((cx - f, cy - h + r - f, cx + f, cy - h + r + f), fill=MARINHO_BASE)


def fundo_padrao(tamanho=FEED, semente=None):
    """Fundo da identidade Moviki: degrade marinho + ruas neon + pinos.

    Deterministico pela semente: o mesmo negocio/pauta sempre ganha o mesmo
    mapa (identidade), negocios diferentes ganham mapas diferentes.
    """
    l, a = tamanho
    rnd = random.Random(str(semente) if semente is not None else "moviki")

    base = Image.new("RGB", (l, a))
    d = ImageDraw.Draw(base)
    for y in range(a):
        t = y / max(1, a - 1)
        d.line([(0, y), (l, y)], fill=tuple(int(MARINHO_TOPO[i] + (MARINHO_BASE[i] - MARINHO_TOPO[i]) * t) for i in range(3)))

    # ruas: grade torta + avenidas diagonais, desenhadas numa camada que
    # ganha brilho (blur) e depois volta nitida por cima.
    ruas = Image.new("RGB", (l, a), (0, 0, 0))
    r = ImageDraw.Draw(ruas)
    ang = rnd.uniform(-0.35, 0.35)
    passo = rnd.randint(130, 170)
    for k in range(-6, 14):
        x0 = k * passo + rnd.randint(-20, 20)
        r.line([(x0, 0), (x0 + math.tan(ang) * a, a)], fill=RUA, width=rnd.choice((2, 2, 3)))
    for k in range(-2, 12):
        y0 = k * passo + rnd.randint(-20, 20)
        r.line([(0, y0), (l, y0 - math.tan(ang) * l * 0.6)], fill=RUA, width=rnd.choice((2, 2, 3)))
    for _ in range(3):
        x0, y0 = rnd.randint(-200, l), rnd.choice((-50, a + 50))
        x1, y1 = rnd.randint(0, l + 200), a + 50 if y0 < 0 else -50
        r.line([(x0, y0), (x1, y1)], fill=AZUL, width=5)

    brilho = ruas.filter(ImageFilter.GaussianBlur(6))
    base = _somar(base, brilho, 0.6)
    base = _somar(base, ruas, 0.3)

    # pinos espalhados, longe do miolo onde vai o conteudo
    pinos = Image.new("RGB", (l, a), (0, 0, 0))
    p = ImageDraw.Draw(pinos)
    for _ in range(7):
        for _tentativa in range(20):
            cx, cy = rnd.randint(40, l - 40), rnd.randint(260, a - 380)
            if cx < l * 0.2 or cx > l * 0.8:
                break
        _pino(p, cx, cy, rnd.randint(34, 56), rnd.choice((CIANO, AZUL, CIANO)))
    base = _somar(base, pinos.filter(ImageFilter.GaussianBlur(10)), 0.8)
    base = _somar(base, pinos, 0.55)

    # vinheta: escurece bordas e o rodape pra leitura
    mascara = Image.new("L", (l, a), 0)
    m = ImageDraw.Draw(mascara)
    for i in range(0, 60):
        m.rectangle((i * 4, i * 4, l - i * 4, a - i * 4), outline=int(255 * (1 - i / 60) * 0.8), width=4)
    base = Image.composite(Image.new("RGB", (l, a), MARINHO_BASE), base, mascara.filter(ImageFilter.GaussianBlur(40)))

    # faixas de leitura: topo (logo + frase) e miolo (nome/titulo) mais
    # escuros, pra rua neon nunca cruzar letra fina.
    sombra = Image.new("L", (l, a), 0)
    s = ImageDraw.Draw(sombra)
    s.rectangle((0, 0, l, 215), fill=190)
    s.rounded_rectangle((40, int(a * 0.20), l - 40, int(a * 0.80)), radius=80, fill=120)
    base = Image.composite(Image.new("RGB", (l, a), MARINHO_BASE), base, sombra.filter(ImageFilter.GaussianBlur(50)))
    return base


def _somar(base, camada, forca):
    """Mistura aditiva (luz somando), limitada a 255."""
    return ImageChops.add(base, camada.point(lambda v: int(v * forca)))


def _brilho_circular(base, centro, raio, cor, forca=0.55):
    l, a = base.size
    camada = Image.new("RGB", (l, a), (0, 0, 0))
    ImageDraw.Draw(camada).ellipse(
        (centro[0] - raio, centro[1] - raio, centro[0] + raio, centro[1] + raio), fill=cor)
    return _somar(base, camada.filter(ImageFilter.GaussianBlur(raio // 2)), forca)


# ------------------------------------------------------------------ pecas
def _cabecalho(base, etiqueta=""):
    """Logo do Moviki + frase da marca a esquerda; etiqueta ciano a direita."""
    l, _ = base.size
    d = ImageDraw.Draw(base)
    margem = 72
    try:
        logo = Image.open(config.LOGO_PATH).convert("RGBA")
        alt = 78
        logo = logo.resize((max(1, int(logo.width * alt / logo.height)), alt), Image.LANCZOS)
        base.paste(logo, (margem, 66), logo)
    except Exception:  # noqa: BLE001
        d.text((margem, 66), "moviki", font=_fonte(config.FONTE_FORTE, 64), fill=BRANCO)
    f = _fonte(config.FONTE_FORTE, 22)
    d.text((margem + 4, 160), "O mapa inteligente dos negócios em movimento.", font=f, fill=CINZA_AZUL)

    if etiqueta:
        f_tag = _fonte(config.FONTE_FORTE, 28)
        tag = etiqueta.upper()
        tw = _largura(d, tag, f_tag)
        x1 = l - margem
        x0 = x1 - tw - 52
        d.rounded_rectangle((x0, 78, x1, 136), radius=29, fill=CIANO)
        d.text((x0 + 26, 91), tag, font=f_tag, fill=TINTA)


def _botao(base, y, texto, largura_max=860):
    """Botao verde da identidade (mesmo do 'CADASTRE-SE GRATIS' do material)."""
    l, _ = base.size
    d = ImageDraw.Draw(base)
    f, linhas = _caber(d, texto.upper(), config.FONTE_FORTE, largura_max - 180, 40, 26, 1)
    w = _largura(d, linhas[0], f)
    icone = 64
    total = icone + 22 + w
    x0 = (l - total) // 2 - 40
    x1 = x0 + total + 80
    base_glow = Image.new("RGB", base.size, (0, 0, 0))
    ImageDraw.Draw(base_glow).rounded_rectangle((x0, y, x1, y + 104), radius=52, fill=VERDE)
    novo = _somar(base, base_glow.filter(ImageFilter.GaussianBlur(18)), 0.45)
    base.paste(novo)
    d = ImageDraw.Draw(base)
    d.rounded_rectangle((x0, y, x1, y + 104), radius=52, fill=VERDE)
    cx, cy = x0 + 40 + icone // 2, y + 52
    d.ellipse((cx - icone // 2, cy - icone // 2, cx + icone // 2, cy + icone // 2), fill=TINTA)
    _pino(d, cx, cy + 20, 40, VERDE)
    x_txt = x0 + 40 + icone + 22
    bbox = d.textbbox((0, 0), linhas[0], font=f)
    d.text((x_txt, y + 52 - (bbox[1] + bbox[3]) // 2), linhas[0], font=f, fill=TINTA)


def _rodape(base, texto="No mapa em tempo real  •  Página própria  •  Contato pelo WhatsApp"):
    l, a = base.size
    d = ImageDraw.Draw(base)
    d.line([(72, a - 118), (l - 72, a - 118)], fill=(28, 60, 130), width=2)
    f, linhas = _caber(d, texto, config.FONTE_FORTE, l - 144, 26, 18, 1)
    _centro(d, a - 80, linhas[0], f, CINZA_AZUL, l)


def _circulo(img, diametro):
    """Recorta a imagem num circulo (logo do lojista), cobrindo o quadro."""
    img = img.convert("RGB")
    escala = max(diametro / img.width, diametro / img.height)
    img = img.resize((max(1, int(img.width * escala)), max(1, int(img.height * escala))), Image.LANCZOS)
    esq, topo = (img.width - diametro) // 2, (img.height - diametro) // 2
    img = img.crop((esq, topo, esq + diametro, topo + diametro))
    mascara = Image.new("L", (diametro, diametro), 0)
    ImageDraw.Draw(mascara).ellipse((0, 0, diametro - 1, diametro - 1), fill=255)
    saida = Image.new("RGBA", (diametro, diametro), (0, 0, 0, 0))
    saida.paste(img, (0, 0), mascara)
    return saida


_LIGACOES = {"e", "de", "da", "do", "das", "dos", "a", "o", "the", "&"}


def _iniciais(nome):
    partes = [p for p in (nome or "").replace("&", " ").split()
              if p[:1].isalnum() and p.lower() not in _LIGACOES]
    if not partes:
        return "M"
    if len(partes) == 1:
        return partes[0][:2].upper()
    return (partes[0][0] + partes[1][0]).upper()


def _selo_negocio(base, logo_bytes, nome, centro, diametro):
    """Logo real do lojista num circulo com anel ciano brilhante.
    Sem logo: circulo azul com as iniciais — nunca imagem inventada."""
    cx, cy = centro
    raio = diametro // 2
    anel = 12
    base.paste(_brilho_circular(base, centro, raio + 40, CIANO, 0.5))
    d = ImageDraw.Draw(base)
    d.ellipse((cx - raio - anel, cy - raio - anel, cx + raio + anel, cy + raio + anel), fill=CIANO)

    logo = None
    if logo_bytes:
        try:
            logo = Image.open(io.BytesIO(logo_bytes))
            logo.load()
        except Exception:  # noqa: BLE001
            logo = None
    if logo is not None:
        circ = _circulo(logo, diametro)
        base.paste(circ, (cx - raio, cy - raio), circ)
        return True

    d.ellipse((cx - raio, cy - raio, cx + raio, cy + raio), fill=(10, 50, 140))
    f = _fonte(config.FONTE_TITULO, int(diametro * 0.42))
    txt = _iniciais(nome)
    bbox = d.textbbox((0, 0), txt, font=f)
    d.text((cx - (bbox[0] + bbox[2]) // 2, cy - (bbox[1] + bbox[3]) // 2), txt, font=f, fill=BRANCO)
    return False


# ------------------------------------------------------------------ cards
def card_vitrine(negocio, logo_bytes=None, cidade="", chamada="", tamanho=FEED, semente=None):
    """Post que divulga UM negocio real cadastrado no Moviki, no padrao Moviki.

    negocio: dict vindo da vitrine (nome, slug, segmento_rotulo...).
    A cor do lojista NAO e usada de proposito: a moldura e sempre da marca.
    """
    base = fundo_padrao(tamanho, semente)
    l, a = base.size
    _cabecalho(base, chamada or "ESTÁ NO MOVIKI")
    d = ImageDraw.Draw(base)
    larg = l - 150

    nome = (negocio.get("nome") or "Negócio").strip()
    # Nome em UMA linha sempre que couber grande; duas linhas so se precisar,
    # e ai o selo encolhe pra o bloco nunca encostar no botao.
    f_nome, linhas = _caber(d, nome.upper(), config.FONTE_TITULO, larg, 112, 80, 1)
    if _largura(d, linhas[0], f_nome) > larg or len(_quebrar(d, nome.upper(), f_nome, larg)) > 1:
        f_nome, linhas = _caber(d, nome.upper(), config.FONTE_TITULO, larg, 96, 56, 2)
    diam, cy = (380, 470) if len(linhas) == 1 else (300, 420)
    _selo_negocio(base, logo_bytes, nome, (l // 2, cy), diam)
    d = ImageDraw.Draw(base)

    y = cy + diam // 2 + 52
    for linha in linhas:
        _centro(d, y, linha, f_nome, BRANCO, l)
        y += int(f_nome.size * 1.04)

    sub = "  •  ".join(x for x in [negocio.get("segmento_rotulo", ""), cidade] if x)
    if sub:
        f_sub, ls = _caber(d, sub.upper(), config.FONTE_FORTE, larg, 32, 22, 1)
        # folga pro cedilha/acento do Anton, que desce abaixo da linha
        _centro(d, y + int(f_nome.size * 0.16) + 22, ls[0], f_sub, CIANO, l)

    slug = (negocio.get("slug") or "").strip()
    y_btn = a - 330
    _botao(base, y_btn, "Veja se está aberto agora")
    if slug:
        d = ImageDraw.Draw(base)
        f_link, ls = _caber(d, f"moviki.com.br/{slug}", config.FONTE_FORTE, larg, 42, 26, 1)
        _centro(d, y_btn + 128, ls[0], f_link, BRANCO, l)

    _rodape(base)
    return base


def card_institucional(titulo, subtitulo="", etiqueta="", tamanho=FEED, semente=None,
                       botao="Conheça em moviki.com.br"):
    """Post sobre o proprio Moviki (pautas de conteudo/pautas.md), no padrao Moviki.

    Usado na sexta (pauta de parceiro) e como reserva quando o catalogo do
    Material de apoio nao responde — o calendario nunca fura.
    """
    base = fundo_padrao(tamanho, semente)
    l, a = base.size
    _cabecalho(base, etiqueta)
    d = ImageDraw.Draw(base)
    margem = 80
    larg = l - margem * 2

    f_tit, linhas = _caber(d, titulo.upper(), config.FONTE_TITULO, larg, 118, 60, 5)
    alt_tit = len(linhas) * int(f_tit.size * 1.06)
    f_sub = _fonte(config.FONTE_FORTE, 38)
    l_sub = _quebrar(d, subtitulo, f_sub, larg)[:3] if subtitulo else []
    alt_sub = (len(l_sub) * (f_sub.size + 12) + 40) if l_sub else 0

    y = 250 + max(0, (a - 250 - 400 - alt_tit - alt_sub) // 2)
    for i, linha in enumerate(linhas):
        cor = CIANO if (i == len(linhas) - 1 and len(linhas) > 1) else BRANCO
        d.text((margem, y), linha, font=f_tit, fill=cor)
        y += int(f_tit.size * 1.06)
    if l_sub:
        y += 40
        for linha in l_sub:
            d.text((margem, y), linha, font=f_sub, fill=(225, 236, 252))
            y += f_sub.size + 12

    _botao(base, a - 300, botao)
    _rodape(base)
    return base


# ------------------------------------------------------------------ saida
def salvar(img, caminho, qualidade=90):
    """Salva otimizado. O Instagram aceita ate 8MB; a gente fica MUITO abaixo."""
    caminho = str(caminho)
    os.makedirs(os.path.dirname(caminho) or ".", exist_ok=True)
    if caminho.lower().endswith((".jpg", ".jpeg")):
        img.convert("RGB").save(caminho, "JPEG", quality=qualidade, optimize=True)
    else:
        img.save(caminho, "PNG", optimize=True)
    return caminho
