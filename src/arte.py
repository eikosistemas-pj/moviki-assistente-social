# -*- coding: utf-8 -*-
"""
Compositor de arte (Pillow).

DECISAO DE ARQUITETURA: a arte final NAO e gerada por IA na hora de
publicar. O robo compoe: pega um fundo aprovado do banco de criativos
(assets/fundos, gerado no Kairogen e revisado antes de entrar no repo) e
escreve por cima os dados REAIS do negocio (nome, segmento, cidade, link)
mais a logo real do lojista.

Por que assim:
  - imagem de IA gerada sem revisao pode ir ao ar torta as 10h da manha;
  - o post de vitrine precisa da logo/foto REAL do lojista, senao nao e
    prova social, e so ilustracao generica;
  - fundo gerado 1x e reusado centenas de vezes custa quase nada;
  - identidade visual fica consistente, nao vira roleta.
"""
import io
import os
import random
import textwrap

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from . import config

FEED = (1080, 1080)
STORY = (1080, 1920)


# ------------------------------------------------------------------ utilidades
def _fonte(caminho, tamanho):
    try:
        return ImageFont.truetype(str(caminho), tamanho)
    except Exception:
        return ImageFont.load_default()


def _hex(cor, padrao="#00f2fe"):
    c = (cor or "").strip()
    if len(c) == 7 and c.startswith("#"):
        try:
            int(c[1:], 16)
            return c
        except ValueError:
            pass
    return padrao


def _rgb(cor):
    c = _hex(cor).lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


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


def _ajustar_fonte(draw, texto, caminho, largura_max, tamanho_ini, tamanho_min=28):
    """Diminui a fonte ate o texto caber em no maximo 2 linhas."""
    tam = tamanho_ini
    while tam > tamanho_min:
        f = _fonte(caminho, tam)
        if len(_quebrar(draw, texto, f, largura_max)) <= 2:
            return f
        tam -= 4
    return _fonte(caminho, tamanho_min)


# ------------------------------------------------------------------ fundos
def _cobrir(img, alvo):
    """Redimensiona cobrindo o alvo inteiro e corta o excesso (object-fit: cover)."""
    lm, am = alvo
    escala = max(lm / img.width, am / img.height)
    novo = (max(1, int(img.width * escala)), max(1, int(img.height * escala)))
    img = img.resize(novo, Image.LANCZOS)
    esq = (img.width - lm) // 2
    topo = (img.height - am) // 2
    return img.crop((esq, topo, esq + lm, topo + am))


def _fundo_liso(tamanho, cor):
    """Fundo de emergencia: degrade diagonal na cor da marca (ou do lojista)."""
    l, a = tamanho
    base = Image.new("RGB", (l, a), config.COR_FUNDO)
    d = ImageDraw.Draw(base)
    r, g, b = _rgb(cor)
    for y in range(a):
        t = y / max(1, a - 1)
        d.line(
            [(0, y), (l, y)],
            fill=(int(11 + (r - 11) * t * 0.35),
                  int(18 + (g - 18) * t * 0.35),
                  int(32 + (b - 32) * t * 0.35)),
        )
    return base


def escolher_fundo(tamanho, segmento=None, cor=None, semente=None):
    """Pega um fundo do banco de criativos. Prefere o do segmento.

    Nomes esperados em assets/fundos:
      <segmento>-01.jpg, <segmento>-02.jpg ... e generico-01.jpg ...
    """
    dir_fundos = config.FUNDOS_DIR
    candidatos = []
    if dir_fundos.is_dir():
        todos = [p for p in sorted(dir_fundos.iterdir())
                 if p.suffix.lower() in (".jpg", ".jpeg", ".png")]
        if segmento:
            candidatos = [p for p in todos if p.stem.lower().startswith(str(segmento).lower())]
        if not candidatos:
            candidatos = [p for p in todos if p.stem.lower().startswith("generico")] or todos

    if not candidatos:
        return _fundo_liso(tamanho, cor)

    rnd = random.Random(semente) if semente is not None else random
    escolhido = rnd.choice(candidatos)
    try:
        return _cobrir(Image.open(escolhido).convert("RGB"), tamanho)
    except Exception as e:  # noqa: BLE001
        print(f"aviso: fundo {escolhido.name} falhou ({e}) -> fundo liso")
        return _fundo_liso(tamanho, cor)


def _escurecer_base(img, forca=0.55):
    """Degrade escuro de baixo pra cima: garante leitura do texto sobre
    qualquer fundo, inclusive foto clara."""
    l, a = img.size
    camada = Image.new("L", (1, a), 0)
    px = camada.load()
    for y in range(a):
        t = y / max(1, a - 1)
        px[0, y] = int(255 * forca * (t ** 1.6))
    mascara = camada.resize((l, a))
    preto = Image.new("RGB", (l, a), (0, 0, 0))
    return Image.composite(preto, img, mascara).convert("RGB")


# ------------------------------------------------------------------ pecas
def _circulo(img, diametro):
    """Recorta a imagem num circulo (logo do lojista)."""
    img = _cobrir(img.convert("RGB"), (diametro, diametro))
    mascara = Image.new("L", (diametro, diametro), 0)
    ImageDraw.Draw(mascara).ellipse((0, 0, diametro - 1, diametro - 1), fill=255)
    saida = Image.new("RGBA", (diametro, diametro), (0, 0, 0, 0))
    saida.paste(img, (0, 0), mascara)
    return saida


def _colar_logo(base, logo_bytes, centro, diametro, cor_borda):
    """Cola a logo do lojista com anel na cor dele. Sem logo -> nao desenha."""
    if not logo_bytes:
        return False
    try:
        logo = Image.open(io.BytesIO(logo_bytes))
    except Exception:
        return False

    cx, cy = centro
    raio = diametro // 2
    anel = 8
    d = ImageDraw.Draw(base)
    d.ellipse(
        (cx - raio - anel, cy - raio - anel, cx + raio + anel, cy + raio + anel),
        fill=_rgb(cor_borda),
    )
    base.paste(_circulo(logo, diametro), (cx - raio, cy - raio), _circulo(logo, diametro))
    return True


def _marca_dagua(base, cor):
    """Assinatura do Moviki no rodape. Sempre presente."""
    l, a = base.size
    d = ImageDraw.Draw(base)
    f = _fonte(config.FONTE_FORTE, 30)
    texto = "moviki.com.br"
    w = _largura(d, texto, f)

    try:
        if config.LOGO_PATH.exists():
            logo = Image.open(config.LOGO_PATH).convert("RGBA")
            alt = 46
            logo = logo.resize((max(1, int(logo.width * alt / logo.height)), alt), Image.LANCZOS)
            total = logo.width + 14 + w
            x = (l - total) // 2
            base.paste(logo, (x, a - 92), logo)
            d.text((x + logo.width + 14, a - 82), texto, font=f, fill=_rgb(cor))
            return
    except Exception:
        pass

    d.text(((l - w) // 2, a - 82), texto, font=f, fill=_rgb(cor))


# ------------------------------------------------------------------ cards
def card_vitrine(negocio, logo_bytes=None, cidade="", chamada="", tamanho=FEED, semente=None):
    """Post que divulga UM negocio real cadastrado no Moviki.

    negocio: dict vindo do Firestore (nome, slug, cor, segmento...).
    """
    cor = _hex(negocio.get("cor"), config.COR_PRIMARIA)
    base = escolher_fundo(tamanho, negocio.get("segmento"), cor, semente)
    base = _escurecer_base(base, 0.62)
    l, a = base.size
    d = ImageDraw.Draw(base)
    margem = 80
    larg_util = l - margem * 2

    # etiqueta de topo
    f_tag = _fonte(config.FONTE_FORTE, 30)
    tag = (chamada or "ESTA NO MOVIKI").upper()
    tw = _largura(d, tag, f_tag)
    d.rounded_rectangle(
        (margem, 78, margem + tw + 56, 78 + 62), radius=31, fill=_rgb(cor)
    )
    d.text((margem + 28, 78 + 15), tag, font=f_tag, fill=(8, 14, 26))

    # logo do lojista
    tem_logo = _colar_logo(base, logo_bytes, (l // 2, int(a * 0.40)), 300, cor)

    # nome do negocio
    y = int(a * 0.40) + (185 if tem_logo else 20)
    f_nome = _ajustar_fonte(d, negocio.get("nome", "Negocio"), config.FONTE_TITULO,
                            larg_util, 92, 44)
    for linha in _quebrar(d, negocio.get("nome", "Negocio"), f_nome, larg_util)[:2]:
        w = _largura(d, linha, f_nome)
        d.text(((l - w) // 2, y), linha, font=f_nome, fill=(255, 255, 255))
        y += f_nome.size + 12

    # cidade / segmento
    sub = " · ".join(x for x in [negocio.get("segmento_rotulo", ""), cidade] if x)
    if sub:
        f_sub = _fonte(config.FONTE_TEXTO, 36)
        w = _largura(d, sub, f_sub)
        d.text(((l - w) // 2, y + 8), sub, font=f_sub, fill=(215, 225, 240))
        y += 60

    # link
    slug = (negocio.get("slug") or "").strip()
    if slug:
        f_link = _fonte(config.FONTE_FORTE, 42)
        link = f"moviki.com.br/{slug}"
        w = _largura(d, link, f_link)
        cx0 = (l - w) // 2
        d.rounded_rectangle(
            (cx0 - 34, y + 30, cx0 + w + 34, y + 30 + 84), radius=42,
            outline=_rgb(cor), width=4,
        )
        d.text((cx0, y + 30 + 20), link, font=f_link, fill=_rgb(cor))

    _marca_dagua(base, cor)
    return base


def card_institucional(titulo, subtitulo="", etiqueta="", tamanho=FEED, semente=None):
    """Post sobre o proprio Moviki (educativo/conversao)."""
    cor = config.COR_PRIMARIA
    base = escolher_fundo(tamanho, "institucional", cor, semente)
    base = _escurecer_base(base, 0.66)
    l, a = base.size
    d = ImageDraw.Draw(base)
    margem = 84
    larg_util = l - margem * 2

    if etiqueta:
        f_tag = _fonte(config.FONTE_FORTE, 30)
        tag = etiqueta.upper()
        tw = _largura(d, tag, f_tag)
        d.rounded_rectangle((margem, 92, margem + tw + 56, 92 + 62), radius=31, fill=_rgb(cor))
        d.text((margem + 28, 92 + 15), tag, font=f_tag, fill=(8, 14, 26))

    f_tit = _fonte(config.FONTE_TITULO, 86)
    linhas = _quebrar(d, titulo, f_tit, larg_util)
    while len(linhas) > 4 and f_tit.size > 48:
        f_tit = _fonte(config.FONTE_TITULO, f_tit.size - 6)
        linhas = _quebrar(d, titulo, f_tit, larg_util)

    altura = len(linhas) * (f_tit.size + 14)
    y = (a - altura) // 2 - 40
    for linha in linhas:
        d.text((margem, y), linha, font=f_tit, fill=(255, 255, 255))
        y += f_tit.size + 14

    if subtitulo:
        f_sub = _fonte(config.FONTE_TEXTO, 38)
        y += 22
        for linha in _quebrar(d, subtitulo, f_sub, larg_util)[:3]:
            d.text((margem, y), linha, font=f_sub, fill=(205, 218, 235))
            y += f_sub.size + 12

    _marca_dagua(base, cor)
    return base


# ------------------------------------------------------------------ saida
def salvar(img, caminho, qualidade=88):
    """Salva otimizado. O Instagram aceita ate 8MB; a gente fica MUITO abaixo."""
    caminho = str(caminho)
    os.makedirs(os.path.dirname(caminho) or ".", exist_ok=True)
    if caminho.lower().endswith((".jpg", ".jpeg")):
        img.convert("RGB").save(caminho, "JPEG", quality=qualidade, optimize=True)
    else:
        img.save(caminho, "PNG", optimize=True)
    return caminho
