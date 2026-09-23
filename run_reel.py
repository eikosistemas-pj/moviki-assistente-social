# -*- coding: utf-8 -*-
"""
Publica UM reel.

22/09/2026 — o que mudou:
  - Antes, com SO_FACEBOOK ligado, o robo saia dizendo "Reel e exclusivo do
    Instagram" e nao publicava nada. Nao e verdade: a Pagina do Facebook
    aceita Reel pela API. Desde 24/08 nenhum reel foi ao ar por causa disso.
  - Fontes: banco de reels do repo (conteudo/reels.md, asset de release),
    videos 9:16 do Material de apoio e, quando ligada, reels de criadores
    autorizados e aprovados. A escolha mora em src/pecas.py.

Sem video publicavel = termina sem publicar, com aviso. Nunca quebra.

Uso:
    python run_reel.py              # decide sozinho
    python run_reel.py material     # forca peca da casa (material + banco)
    python run_reel.py criador      # forca peca de criador
    DRY_RUN=1 python run_reel.py    # escolhe e NAO publica
"""
import sys

from src import config, conteudo, pecas


def main():
    print(f"moviki-assistente-social {config.VERSAO}")
    forcado = (sys.argv[1] if len(sys.argv) > 1 else "").strip().lower()
    origem = {"material": "casa", "criador": "criador"}.get(forcado)
    peca = pecas.escolher_peca("reel", origem)
    if not peca:
        print("nenhum reel publicavel hoje -> nada a publicar.")
        return
    pecas.publicar(peca, conteudo.hashtags(peca.get("tipo_pauta") or "conversao"))


if __name__ == "__main__":
    main()
