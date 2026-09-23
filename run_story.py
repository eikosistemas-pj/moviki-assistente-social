# -*- coding: utf-8 -*-
"""
Publica UM story (22/09/2026).

Fontes: stories do Material de apoio do parceiro (arte 9:16, sem legenda) e,
quando a fonte estiver ligada, stories de criadores autorizados e aprovados.
A escolha e a mistura moram em src/pecas.py.

Sem peca publicavel = termina sem publicar, com aviso. Nunca quebra o
workflow por falta de conteudo.

Uso:
    python run_story.py              # decide sozinho
    python run_story.py material     # forca peca da casa
    python run_story.py criador      # forca peca de criador
    DRY_RUN=1 python run_story.py    # escolhe e NAO publica
"""
import sys

from src import config, pecas


def main():
    print(f"moviki-assistente-social {config.VERSAO}")
    forcado = (sys.argv[1] if len(sys.argv) > 1 else "").strip().lower()
    origem = {"material": "casa", "criador": "criador"}.get(forcado)
    peca = pecas.escolher_peca("story", origem)
    if not peca:
        print("nenhum story publicavel hoje -> nada a publicar.")
        return
    pecas.publicar(peca)


if __name__ == "__main__":
    main()
