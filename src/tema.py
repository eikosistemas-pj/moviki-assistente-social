# -*- coding: utf-8 -*-
"""
TEMAS SAZONAIS e ESTREIAS — trava de repeticao entre formatos (23/10/2026).

O QUE ACONTECEU
  Entre 21 e 23/10/2026 o perfil virou um bloco so de Black Friday: todo
  feed, todo reel e 2 a 3 stories por dia. As pecas de BF do Material de
  apoio sao todas da categoria "geral", entao a trava de ramo ("nunca o
  mesmo ramo em seguida") nao pegava nenhuma delas.

  E o reel `bf-ao-vivo` saiu pelo sorteio em 22/10 com estreia marcada na
  grade para 24/10: a mesma peca existe no Material de apoio com o mesmo id
  e passava por fora da trava da grade.

REGRAS (sorteio; a peca AGENDADA na grade nunca e barrada, mas conta)
  - Por dia (horario de Brasilia), no maximo POR_FORMATO peca de um tema em
    cada formato e no maximo POR_DIA no perfil inteiro.
  - Nunca o mesmo tema duas vezes seguidas no mesmo formato.
  - Peca com estreia de reel marcada na grade (hoje ate ESTREIA_DIAS dias)
    nao sai antes pelo sorteio, em formato nenhum de video.
  - A trava nunca deixa o formato sem post: se esvaziar a lista, volta a
    lista original.
"""
from datetime import datetime, timedelta

from . import config, estado, grade

TEMAS = {
    "black-friday": ("black friday", "black-friday", "bf-"),
    "natal": ("natal",),
}
POR_FORMATO = 1
POR_DIA = 2
ESTREIA_DIAS = 14


def tema(item):
    """Tema de uma peca ou de uma linha do historico (None = sem tema)."""
    if not item:
        return None
    if item.get("tema"):
        return item["tema"]
    texto = " ".join(str(item.get(k) or "") for k in
                     ("id", "fonte_id", "peca", "titulo", "descricao")).lower()
    for nome, pedacos in TEMAS.items():
        if any(p in texto for p in pedacos):
            return nome
    return None


def dia_br(h):
    try:
        return datetime.fromisoformat(h["quando"]).astimezone(config.FUSO_BR).date()
    except (KeyError, ValueError, TypeError):
        return None


def de_hoje(hist=None, formato=None, hoje=None):
    hist = estado.ler_lista("historico.json") if hist is None else hist
    hoje = hoje or config.hoje_br()
    return [h for h in hist if dia_br(h) == hoje
            and (formato is None or h.get("formato") == formato)]


def ultimo(formato, hist=None):
    hist = estado.ler_lista("historico.json") if hist is None else hist
    for h in hist:
        if h.get("formato") == formato and h.get("tipo") != "pergunta":
            return tema(h)
    return None


def bloqueados(formato, hist=None, hoje=None):
    hist = estado.ler_lista("historico.json") if hist is None else hist
    no_formato, no_dia = {}, {}
    for h in de_hoje(hist, None, hoje):
        t = tema(h)
        if not t:
            continue
        no_dia[t] = no_dia.get(t, 0) + 1
        if h.get("formato") == formato:
            no_formato[t] = no_formato.get(t, 0) + 1
    saida = {t for t, n in no_formato.items() if n >= POR_FORMATO}
    saida |= {t for t, n in no_dia.items() if n >= POR_DIA}
    ult = ultimo(formato, hist)
    if ult:
        saida.add(ult)
    return saida


def filtrar(lista, formato, hist=None, hoje=None):
    if not lista:
        return lista
    fora = bloqueados(formato, hist, hoje)
    if not fora:
        return lista
    saida = [p for p in lista if tema(p) not in fora]
    if saida:
        print(f"{formato}: tema fora hoje -> {', '.join(sorted(fora))}")
        return saida
    return lista


def estreias(hoje=None, dados=None):
    """Ids da grade com estreia de hoje ate ESTREIA_DIAS dias."""
    hoje = hoje or config.hoje_br()
    ids = set()
    try:
        itens, _ = grade.validos(dados)
    except Exception:  # noqa: BLE001
        return ids
    for it in itens:
        for d in it.get("dias") or []:
            try:
                dia = datetime.fromisoformat(str(d)).date()
            except ValueError:
                continue
            if hoje <= dia <= hoje + timedelta(days=ESTREIA_DIAS):
                ids.add(it.get("id"))
    return ids


def sem_estreia(lista, hoje=None, dados=None):
    """Tira do sorteio a peca do Material de apoio que vai estrear na grade.
    A propria peca da grade (origem 'grade') nunca sai por aqui."""
    if not lista:
        return lista
    ids = estreias(hoje, dados)
    if not ids:
        return lista
    saida = [p for p in lista if p.get("origem") == "grade"
             or (p.get("fonte_id") or p.get("id")) not in ids]
    return saida or lista
