# Grade de vídeos do robô (desde 30/09/2026)

A grade diz **qual vídeo sai em qual dia**. Sem ela, o reel sai por sorteio entre os vídeos do Material de apoio. Com ela, o vídeo marcado para o dia vence o sorteio.

## Onde mora cada coisa

| O quê | Onde |
|---|---|
| A grade | `conteudo/grade.json` (este repositório) |
| O vídeo (já com a proteção anticópia) | **Firebase Storage do Moviki, pasta `material/`** (desde 21/10/2026, preferido: um lugar só para grade, anúncio e Material de apoio) ou release **`acervo`** deste repositório, anexo `<id>.mp4` |
| A capa (JPG 1080x1920) | `conteudo/acervo-capas/<id>.jpg` |
| Cópia limpa (sem proteção) | Google Drive — nunca no GitHub |

O vídeo **não entra no git** (mesma regra do `reels.md`). Endereço no Firebase: `https://firebasestorage.googleapis.com/v0/b/moviki-app.firebasestorage.app/o/material%2F<id>.mp4?alt=media` (a pasta `material/` tem leitura pública). Nunca trocar o conteúdo mantendo o nome: versão nova ganha nome novo.

## Campos de cada vídeo

| Campo | Para que serve |
|---|---|
| `id` | nome do arquivo sem `.mp4`, só minúsculas, números e hífen |
| `formato` | `reel` (por enquanto o único) |
| `pilar` | `serie-live`, `ramo`, `criador`, `paulo` — o painel e o rodízio usam |
| `titulo` | 1ª linha que aparece no painel; também vira texto reserva |
| `legenda` | legenda do Instagram, na voz da marca, fechando com "link da bio". O Facebook recebe a mesma trocando por moviki.com.br |
| `canais` | `instagram`, `facebook` |
| `vende_live` | `true` se o vídeo vende a live: só sai com o secret `LIVE_NA_PAGINA` = 1 |
| `dias` | datas marcadas (AAAA-MM-DD). Desde 17/10/2026 saem **2 reels por dia** (~13h23 e ~19h37): qualquer data serve. Fora do dia marcado, o rodízio escolhe cada reel de um ramo diferente |
| `a_partir_de` / `valido_ate` | janela em que o vídeo pode sair. **Todo vídeo tem prazo** |
| `reconferir_em` | para vídeo com dado que muda (preço, regra de outra plataforma): nessa data ele para de sair até alguém reconferir |
| `repetir_apos_dias` | intervalo mínimo entre duas saídas (padrão 45) |
| `so_agendado` | `true` = sai só nos dias marcados, nunca no sorteio |
| `marca` | código da proteção anticópia (registro do Project) |
| `chamada` | (opcional, 28/10/2026) primeira linha própria da legenda no Instagram, no lugar do "Comente LIVE". Usado pelos **Guias FARO**: "Comente GUIA…". Texto vazio = sem chamada. Só funciona se a palavra existir no ManyChat |
| `cartela` | (opcional) `false` = o reel sai **sem** a cartela falada "Comenta LIVE" no fim. Obrigatório com `chamada` que não fala LIVE (a trava recusa a combinação errada) |

## Travas (falha fechada)

- Campo errado → o vídeo fica fora e aparece alerta **grave** no painel do dono.
- Vídeo marcado em dia sem reel → alerta grave antes do dia.
- Vídeo que não está na release `acervo` → não vai para a Meta (senão o post cairia no Instagram **e** no Facebook) e vira alerta grave.
- Vencido ou com `reconferir_em` passado → não sai. Faltando 7 dias, alerta de atenção.
- Legenda passa pelo `compliance.garantir()` como todo texto do robô.
- Marca de outra plataforma na legenda é barrada pelo teste `test_grade_do_repositorio_esta_valida_e_limpa`.

## Regra editorial (decisão do Paulo, 29/09/2026)

Vídeo que pode dar problema **não entra**: nada de comparação nominal com outra plataforma, número de concorrente, promessa de resultado ou depoimento. Só a versão sem marca de terceiro.

## Onde ver

Painel do dono → **Redes sociais** → cartão **Grade de vídeos — próximos 14 dias** (lê `estado/redes.json`, atualizado ~08h e ~22h).
