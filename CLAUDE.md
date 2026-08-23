# CLAUDE.md — moviki-assistente-social

Repositório de PUBLICAÇÃO nas redes do Moviki. Python 3.11, roda só em
GitHub Actions.

## 1. Escopo e fronteira (não violar)

- Idioma obrigatório: Português (Brasil).
- Este repo **só publica**. Não responde DM, não responde comentário —
  isso é do `moviki-ai` (webhook Node). Não trazer conversa pra cá.
- Este repo **não escreve** no Firestore. Só lê `negocios` pela REST API,
  sem autenticação (a leitura já é pública nas regras).
- **Nunca** adicionar secret de service account do Firebase aqui. Chave de
  Admin SDK dá escrita total, inclusive em `comissoes`, `saques` e
  `assinaturas`. Se algo parecer exigir isso, a resposta é redesenhar, não
  adicionar a chave.

| Repo | Papel |
|---|---|
| `moviki-robo` | Dinheiro (Asaas, comissões, saque). Muda o mínimo. |
| `moviki-ai` | Conversa (WhatsApp, futuramente DM/comentários do IG). |
| `moviki-assistente-social` | Publicação. |

## 2. Regras de ouro

1. **Todo texto passa por `compliance.garantir()` antes de publicar.** Sem
   exceção — legenda de IA, pauta escrita à mão, roteiro de reel.
2. **Texto reserva é obrigatório e precisa estar limpo.** Se a reserva
   violar a trava, o robô estoura de propósito: é bug nosso, e quebrar o
   workflow é melhor que publicar.
3. **Falha de IA nunca fura o calendário.** Sem chave, com erro ou com
   resposta suja, o post sai com o texto reserva.
4. **Vitrine exige `autorizaDivulgacao === true`.** Booleano, não string.
   Ausência do campo = fora. Isso é LGPD, não preferência.
5. **Nunca imprimir endereço exato de terceiro.** Só município/UF.
6. **Instagram é prioridade; Facebook é best-effort.** Falha no espelho
   nunca derruba o ciclo.
7. **Imagem não é gerada por IA na hora de publicar.** O robô compõe sobre
   fundo já aprovado do banco. Ver seção 4.
8. **Vídeo não entra no git.** Asset de release + ponteiro em
   `conteudo/reels.md`.
9. **Antes de confiar em "já subiu", conferir por clone/leitura ao vivo.**
   Índice de Project (RAG) pode estar desatualizado.
10. **Escrita direta pelo Claude em repositório continua bloqueada**
    (GitHub Issue `anthropics/claude-code#76248`). Entregar arquivo pronto
    no chat, upload manual.

## 3. Camadas da trava (`src/compliance.py`)

| Camada | Risco |
|---|---|
| `ganho_facil` | Promessa de retorno no Programa de Parceiros → enquadramento como pirâmide (CVM/PROCON/MP). **Risco nº 1.** |
| `resultado` | Garantia de venda pro lojista → publicidade enganosa (CDC art. 37). |
| `fornecedor` | Nomear a stack. Regra de ouro do projeto. |
| `prova_falsa` | Número de clientes, prêmio ou depoimento inventado. |
| `concorrente` | Citar concorrente pelo nome. |
| `dado_pessoal` | Telefone, CPF ou e-mail no post. |

Comissão **pode** ser explicada. Rendimento **não pode** ser prometido.
Essa distinção é a linha inteira.

Nota: o campo `angulo` das pautas é instrução pra IA e pode nomear termo
proibido pra proibi-lo. Os testes validam só `titulo` e `subtitulo`, que
são o que vira texto público.

## 4. Banco de criativos

`assets/fundos/<macro>-NN.jpg`. Gerados no Kairogen, **revisados por
humano**, e só então commitados. O robô escolhe e compõe por cima.

Prompt que funciona (validado): fotografia cinematográfica, cena real
brasileira de rua, e a instrução explícita de deixar **grande área escura
vazia no centro e embaixo para sobreposição de texto**, mais "sem nenhum
texto, sem letras, sem logotipos". Sem isso a IA preenche o quadro inteiro
e não sobra lugar pro nome do negócio.

Modelo custo/benefício: `seedream-5-pro`, 2 créditos por imagem.
Reels: `veo-3-1-fast`, 45 créditos.

Fallback em cascata: fundo do segmento → `generico-*` → degradê na cor do
lojista. Nunca quebra por falta de arquivo.

## 5. Comportamento e economia de tokens

- Direto ao ponto. Sem saudação, sem introdução, sem encerramento.
- Retornar arquivo completo com nome final, nunca "pedaço + onde colar".
- Antes de entregar: `python -m compileall`, testes passando, LF sem CR.
- Ser crítico: apontar falha lógica e propor solução superior antes de
  aplicar o que foi pedido.
