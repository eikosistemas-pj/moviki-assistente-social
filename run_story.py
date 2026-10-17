# -*- coding: utf-8 -*-
"""
Publica UM story (22/09/2026; grade de video e trilha em 17/10/2026).

Alterna VIDEO (corte de 9-20 s do Material de apoio ou do acervo, com trilha)
e ARTE (arte 9:16 animada com zoom e trilha). Chamada "Responda LIVE"
embutida um story sim, outro nao. Tudo em src/story.py.

Sem peca publicavel = termina sem publicar, com aviso. Nunca quebra o
workflow por falta de conteudo.

Uso:
    python run_story.py              # decide sozinho
    python run_story.py material     # forca peca da casa
    python run_story.py criador      # forca peca de criador
    DRY_RUN=1 python run_story.py    # escolhe e NAO publica
"""
import sys

from src import config, story


def main():
    print(f"moviki-assistente-social {config.VERSAO}")
    forcado = (sys.argv[1] if len(sys.argv) > 1 else "").strip().lower()
    origem = {"material": "casa", "criador": "criador"}.get(forcado)
    story.rodar(origem)


if __name__ == "__main__":
    main()
