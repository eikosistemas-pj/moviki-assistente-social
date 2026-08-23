# -*- coding: utf-8 -*-
"""
Limpeza semanal de publicado/.

Pode apagar sem medo: o Instagram BAIXA a imagem quando cria o container e
serve a copia dele. A URL de origem so precisa existir naquele instante.

Mantem o repo leve e o historico honesto.
"""
import re
from datetime import datetime, timedelta, timezone

from src import config, hospedagem

PADRAO_DATA = re.compile(r"-(\d{8})-\d{6}\.")


def main():
    corte = datetime.now(timezone.utc) - timedelta(days=config.DIAS_RETENCAO_IMAGEM)
    arquivos = hospedagem.listar_publicados()
    print(f"arquivos em publicado/: {len(arquivos)} | corte: {corte.date()}")

    apagados = 0
    for a in arquivos:
        nome = a.get("name", "")
        m = PADRAO_DATA.search(nome)
        if not m:
            continue
        try:
            data = datetime.strptime(m.group(1), "%Y%m%d").replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        if data < corte:
            if hospedagem.apagar(a["path"], a["sha"]):
                apagados += 1
                print(f"apagado: {nome}")

    print(f"OK -> limpeza concluida | {apagados} arquivo(s) removido(s)")


if __name__ == "__main__":
    main()
