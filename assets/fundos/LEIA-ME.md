# Banco de fundos — APOSENTADO em 22/09/2026

O robô **não usa mais** as imagens desta pasta.

Até 21/09 ele escrevia o nome do lojista (ou a frase da pauta) por cima
destas fotos, com a etiqueta na cor do lojista. O resultado no ar ficou
desigual: foto sem relação com o negócio, texto por cima do rosto da pessoa,
cada post de uma cor.

## O que entrou no lugar

| Post | De onde vem a imagem |
|---|---|
| Feed do dia a dia | Peça pronta do **Material de apoio do parceiro** (`app.moviki.com.br/material/catalogo.json`), lida ao vivo por `src/material.py` |
| Vitrine de lojista | Moldura padrão Moviki desenhada em código (`src/arte.py`): marinho, mapa neon, logo real do lojista, botão verde |
| Card de pauta (sexta e reserva) | A mesma moldura padrão |

Para mudar o que vai ao ar no feed, suba ou troque a peça na aba
Material de apoio do painel do parceiro. Nada aqui precisa ser mexido.

Os arquivos `.jpg` podem ser apagados quando o Paulo quiser; nenhum código
depende deles.
