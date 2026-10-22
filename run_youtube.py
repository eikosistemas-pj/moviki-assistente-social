# -*- coding: utf-8 -*-
"""
Sobe UM Short no canal Moviki Live Shop (22/10/2026). Detalhes em src/youtube.py.

Sem as credenciais do YouTube nos secrets = avisa e sai sem erro.
Sem video novo para subir = avisa e sai sem erro.

Uso:
    python run_youtube.py              # sobe o proximo da fila
    DRY_RUN=1 python run_youtube.py    # mostra os proximos e NAO sobe
"""
import os
import sys

from src import config, grade, material, triagem, youtube
from src import util_net as net


def proximos():
    cfg = youtube.carregar_fila()
    est = youtube.ler_estado()
    hoje = config.hoje_br()
    pecas = []
    try:
        pecas = triagem.filtrar(material.pecas(material.carregar_catalogo(), "reel"))
    except Exception as e:  # noqa: BLE001
        print(f"AVISO: material de apoio indisponivel ({net.sem_segredo(e)}) -> so a grade")
    itens = []
    try:
        itens, ruins = grade.validos()
        for iid, erros in ruins:
            print(f"AVISO: grade: {iid} fora ({'; '.join(erros)[:120]})")
    except Exception as e:  # noqa: BLE001
        print(f"AVISO: grade indisponivel ({net.sem_segredo(e)}) -> so o material")
    return youtube.candidatos(cfg, pecas, itens, est["enviados"], hoje), est


def main():
    print(f"moviki-assistente-social {config.VERSAO} — youtube {youtube.MARCA}")
    fila, est = proximos()
    print(f"youtube: {len(fila)} video(s) para subir | {len(est['enviados'])} ja no canal")
    for i, it in enumerate(fila[:5]):
        print(f"  {i + 1}. {it['id']} ({'fila' if it['fila'] else 'auto'}) — {it['titulo']}")
    if os.environ.get("DRY_RUN"):
        print("DRY_RUN: nada foi enviado.")
        return 0
    if not youtube.ligado():
        print("youtube: faltam os secrets YT_CLIENT_ID / YT_CLIENT_SECRET / YT_REFRESH_TOKEN -> nada a fazer.")
        return 0
    if not fila:
        print("youtube: nenhum video novo para subir hoje.")
        return 0

    tok = youtube.token()
    # Um por rodada. Se o primeiro falhar (arquivo fora do ar, por exemplo),
    # tenta o seguinte — mas nunca sobe mais de um.
    for it in fila[:3]:
        try:
            reg = youtube.publicar(it, tok)
        except Exception as e:  # noqa: BLE001
            print(f"youtube: {it['id']} nao subiu ({net.sem_segredo(e)})")
            if "token" in str(e) or "quota" in str(e).lower():
                break
            continue
        youtube.registrar(est, it["id"], reg)
        print(f"youtube: pronto. {it['id']} -> https://youtu.be/{reg['yt']} ({reg['visibilidade']})")
        return 0
    print("::error::youtube: nenhum video subiu nesta rodada")
    return 1


if __name__ == "__main__":
    sys.exit(main())
