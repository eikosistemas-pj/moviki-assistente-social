# Moviki — instruções para repositório PÚBLICO (versão curta)

> Este repositório é público. Por decisão de segurança (06/10/2026), o mapa
> mestre completo do Moviki — arquitetura, coleções, endpoints, contas e
> histórico — vive **só nos repositórios privados** (`moviki-app`,
> `moviki-robo`, `moviki-ai`) e no cofre `moviki-vault`. Nada daquilo entra
> aqui. Se a tarefa precisar do mapa, peça ao Paulo acesso ao repositório
> privado ou o retrato (`RETRATO <repo>.zip`).

## O que é o Moviki

Plataforma da EIKO SISTEMAS para lojista vender ao vivo e ser encontrado: site
público (`moviki`), painéis (`moviki-app`), robô de dinheiro (`moviki-robo`),
conversacional (`moviki-ai`) e robô de redes (`moviki-assistente-social`).

## Quem dá os comandos

- Paulo, fundador. Não é programador; trabalha pela interface web do GitHub.
- Responder sempre em Português (Brasil), direto, em bullets, sem mostrar
  código na conversa. Avaliar criticamente cada pedido antes de executar.

## Regras que valem aqui

1. **Nunca push direto na `main`.** Branch + Pull Request, sempre. A `main`
   vai para produção na hora.
2. **Um assunto por PR.**
3. **Nunca gravar chave, token, senha ou e-mail interno em arquivo**, nem em
   comentário, nem em exemplo, nem em teste. Segredo fica em Environment
   Variables da Vercel ou em GitHub Secrets.
4. **Vídeo não entra em repositório.** Exceção única: clipe mudo em
   `moviki/ramos/<ramo>.mp4` até 1,2 MB.
5. **Toda entrega atualiza a marca de versão** (`AAAA-MM-DD-assunto`) do
   arquivo tocado, e nunca se monta alteração sobre cópia antiga.
6. **Repositório público não recebe documentação interna.** Este arquivo é o
   único `CLAUDE.md` permitido aqui; o conferidor diário do `moviki-app`
   acusa se um mapa completo aparecer em repositório público.
7. **Escapar todo texto de usuário** exibido em página pública.
8. A palavra "trial" não aparece em texto que o cliente lê; usar "teste
   grátis".

## As cadeiras

As cadeiras transversais (`.claude/skills/gabinete`, `.claude/skills/guarda`)
são as mesmas em todos os repositórios de código e descrevem princípios, não
segredos. A Guarda tem veto em tudo o que expõe dado.
