# -*- coding: utf-8 -*-
"""
Kit TikTok do dia (28/09/2026).

POR QUE NAO E AUTOMATICO
  A API de postagem do TikTok so publica em modo PUBLICO depois de uma
  auditoria, e as regras dela nao aprovam ferramenta que so posta na propria
  conta. Sem auditoria o video sai privado. Robo de navegador viola as regras
  e derruba a conta. Entao o robo prepara e o Paulo posta pelo app (1 minuto)
  — e, postando pelo app, ainda da pra por o som em alta, que a API nem tem.

O QUE O ROBO FAZ
  No relatorio das redes (~08h e ~22h) monta a agenda de 7 dias: um video
  por dia, tirado dos videos 9:16 do Material de apoio que ja passaram por
  TODAS as travas da pagina oficial (legenda sem voz de parceiro, sem live
  com LIVE_NA_PAGINA desligado, so_parceiro, triagem por imagem, compliance).
  A agenda fica em estado/tiktok.json e NAO muda entre as duas rodadas do
  dia: o video de hoje e o mesmo de manha e a noite.

ROTACAO
  Video nunca usado primeiro; depois o usado ha mais tempo. Nunca o mesmo
  ramo dois dias seguidos quando houver alternativa. Nunca o mesmo video
  duas vezes em 7 dias: com menos de 7 videos liberados, sobra dia sem kit. Video que saiu do
  catalogo (ou foi barrado) sai da agenda e o dia e preenchido de novo.
"""
from datetime import timedelta

from . import compliance, config, conteudo, estado

ARQUIVO = "tiktok.json"
DIAS = 7            # hoje + 6
GUARDAR = 120       # dias de historico da agenda


def legenda(peca, dia):
    """Legenda do TikTok: a do Instagram (ja na voz da marca, 'link da bio')
    + ate 5 hashtags do ramo e da data comemorativa."""
    base = (peca.get("legenda_ig") or "").strip()
    reserva = f"{(peca.get('titulo') or 'Seu negócio no mapa').strip().rstrip('.')}.\n\nConheça pelo link da bio."
    texto = compliance.garantir(base or reserva, reserva)
    # 09/10/2026: no TikTok so o direct dispara o funil do ManyChat (comentario
    # nao tem gatilho no Brasil). A chamada abre a legenda, antes da dobra.
    if config.CHAMADA_TIKTOK:
        texto = compliance.garantir(f"{config.CHAMADA_TIKTOK}\n\n{texto}", texto)
    tags = conteudo.hashtags("conversao", peca.get("categoria"), dia)
    return f"{texto}\n\n{tags}".strip(), tags


def _ultimo_uso(agenda, antes_de):
    uso = {}
    for d, pid in agenda.items():
        if d < antes_de and pid:
            uso[pid] = max(uso.get(pid, ""), d)
    return uso


def planejar(videos, hoje, agenda=None):
    """Agenda {AAAA-MM-DD: id} para hoje..hoje+6. Dias ja planejados com video
    ainda valido nao mudam."""
    agenda = dict(agenda or {})
    validos = {v["id"]: v for v in videos}
    dias = [(hoje + timedelta(days=n)).isoformat() for n in range(DIAS)]
    for d in dias:
        if agenda.get(d) not in validos:
            agenda.pop(d, None)
    if not validos:
        return agenda
    for i, d in enumerate(dias):
        if d in agenda:
            continue
        uso = _ultimo_uso({k: v for k, v in agenda.items() if k != d}, "9999")
        ontem = agenda.get((hoje + timedelta(days=i - 1)).isoformat())
        amanha = agenda.get((hoje + timedelta(days=i + 1)).isoformat())
        vizinhos = {validos[x].get("categoria") for x in (ontem, amanha) if x in validos}
        semana = {agenda.get(x) for x in dias if x != d}

        def ordem(v):
            return (v.get("categoria") in vizinhos and v.get("categoria") not in (None, "geral"),
                    uso.get(v["id"], ""),                    # nunca usado ("") primeiro
                    v["id"])
        # Mesmo video duas vezes na mesma semana, nunca: o TikTok derruba o
        # alcance de conteudo repetido. Faltou video novo = dia sem kit.
        livres = [v for v in validos.values() if v["id"] not in semana]
        if livres:
            agenda[d] = sorted(livres, key=ordem)[0]["id"]
    corte = (hoje - timedelta(days=GUARDAR)).isoformat()
    return {d: p for d, p in sorted(agenda.items()) if d >= corte}


def kit(videos, hoje, agenda):
    validos = {v["id"]: v for v in videos}
    saida = []
    for n in range(DIAS):
        dia = hoje + timedelta(days=n)
        v = validos.get(agenda.get(dia.isoformat()))
        if not v:
            continue
        texto, tags = legenda(v, dia)
        saida.append({
            "dia": dia.isoformat(),
            "hoje": n == 0,
            "id": v["id"],
            "titulo": v.get("titulo", ""),
            "ramo": v.get("categoria", ""),
            "video": v["url"],
            # "video_cartela" (09/10/2026): o mesmo video com a cartela
            # "Mande LIVE no direct" no fim; posto por cartela.kit_tiktok.
            "capa": v.get("capa_triagem") or v.get("capa") or "",
            "duracao": v.get("duracao"),
            "legenda": texto,
            "hashtags": tags,
        })
    return saida


def atualizar(videos, hoje):
    """Le a agenda salva, completa os 7 dias, grava e devolve o bloco do relatorio."""
    salvo = estado.ler_lista(ARQUIVO)
    salvo = salvo if isinstance(salvo, dict) else {}
    agenda = planejar(videos, hoje, salvo.get("agenda"))
    estado.gravar_lista(ARQUIVO, {"agenda": agenda})
    dias = kit(videos, hoje, agenda)
    try:
        from . import cartela
        dias = cartela.kit_tiktok(dias, hoje.isoformat())
    except Exception as e:  # noqa: BLE001
        print(f"kit tiktok: cartela fora ({str(e)[:120]}) -> video original.")
    return {
        "videos_disponiveis": len(videos),
        "live_na_pagina": config.LIVE_NA_PAGINA,
        "dias": dias,
    }
