# Estado do robo

Arquivos JSON de memoria entre execucoes (rotacao anti-repeticao e
historico). Escritos pelo robo e commitados de volta pelo workflow.

Nao editar a mao a menos que queira forcar uma repeticao.

## Stories (17/10/2026)

- `story_cortes.json` — para cada vídeo, qual corte sai na próxima vez.
- `recentes_pecas_storyvideo.json` — rodízio dos vídeos que viram story.
- `recentes_trilhas_story.json` — rodízio das trilhas.
- No `historico.json`, cada story ganha `tipo` (video|arte), `cta`
  (chamada embutida), `trilha` e `corte`.

## YouTube (22/10/2026)

- `youtube.json` — cada vídeo já no canal Moviki Live Shop, por id da peça: id do YouTube, visibilidade, título, comentário a fixar e playlist. `manual: true` = subiu à mão antes do robô. Apagar uma linha faz o robô subir aquele vídeo de novo.
