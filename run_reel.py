# -*- coding: utf-8 -*-
"""
Publica um Reel do banco (conteudo/reels.md).

O Reel e o formato de maior alcance organico hoje. Ele NAO e gerado na hora:
os videos sao produzidos em lote no Kairogen, revisados, anexados como asset
de release e so entao entram no banco. O robo apenas escolhe e publica.

Banco vazio = termina sem publicar, com aviso. Nunca quebra o workflow.
"""
import re

from src import config, conteudo, estado, ia
from src.social.instagram import Instagram

CAMPOS = ("tipo", "url", "capa", "titulo", "angulo")


def carregar_reels():
    caminho = config.CONTEUDO_DIR / "reels.md"
    if not caminho.exists():
        return []
    texto = conteudo.sem_comentarios(caminho.read_text(encoding="utf-8"))
    partes = re.split(r"^##\s+", texto, flags=re.M)[1:]
    reels = []
    for bloco in partes:
        linhas = bloco.strip().splitlines()
        if not linhas:
            continue
        r = {"id": linhas[0].strip()}
        for linha in linhas[1:]:
            m = re.match(r"^\s*(\w+)\s*:\s*(.+)$", linha)
            if m and m.group(1).lower() in CAMPOS:
                r[m.group(1).lower()] = m.group(2).strip()
        url = r.get("url", "")
        # ignora o bloco de exemplo do cabecalho
        if url.startswith("http") and "<owner>" not in url:
            r.setdefault("tipo", "educativo")
            r.setdefault("titulo", r["id"])
            r.setdefault("angulo", r["titulo"])
            reels.append(r)
    return reels


def main():
    # Reel so existe no Instagram. Com o Instagram bloqueado pela Meta, sair
    # limpo (sem erro) em vez de deixar o workflow vermelho toda terca e
    # sabado — alarme que toca sempre e alarme que ninguem escuta.
    if config.SO_FACEBOOK:
        print("SO_FACEBOOK ligado -> Reel e exclusivo do Instagram. Nada a publicar hoje.")
        return

    reels = carregar_reels()
    if not reels:
        print("banco de Reels vazio (conteudo/reels.md) -> nada a publicar hoje.")
        return

    reel = estado.escolher("reel", reels, chave=lambda r: r["id"])
    print(f"reel: {reel['id']} ({reel['tipo']})")

    reserva = (
        f"{reel['titulo']}\n\n"
        f"O Moviki mostra onde os negócios itinerantes estão agora.\n"
        f"Conheça em moviki.com.br — link na bio."
    )
    legenda = ia.escrever(
        f"Escreva a legenda de um Reel do Moviki.\n\n"
        f"Assunto do video: {reel['titulo']}\n"
        f"Angulo: {reel.get('angulo','')}\n\n"
        f"Primeira linha precisa segurar a atencao de quem esta rolando o feed. "
        f"Feche com chamada pra acao mandando pro link da bio.",
        reserva,
    )
    print("--- legenda ---")
    print(legenda)
    print("---------------")

    if config.DRY_RUN:
        print("DRY_RUN ligado -> nada foi publicado.")
        return

    media_id = Instagram().reel(
        reel["url"], legenda, conteudo.hashtags(reel["tipo"]),
        capa_url=reel.get("capa"),
    )
    print(f"OK -> Reel publicado | {reel['id']} | id: {media_id}")

    estado.marcar_usado("reel", reel["id"])
    estado.registrar("reel", reel["titulo"], media_id, {"reel_id": reel["id"]})


if __name__ == "__main__":
    main()
