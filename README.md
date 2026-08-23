# moviki-assistente-social

Robô de publicação nas redes do Moviki. Publica no Instagram e espelha no
Facebook, sozinho, no calendário. Roda **100% em GitHub Actions** — sem
servidor, sem Vercel, sem consumir o teto de 12 funções do plano Hobby dos
outros repositórios.

---

## O que ele publica

| Formato | Quando | O que é |
|---|---|---|
| **Feed — vitrine** | Seg/Qua/Ter/Qui/Sex | Divulga um **negócio real** cadastrado no Moviki que autorizou divulgação |
| **Feed — institucional** | idem | Explica o produto, a partir de `conteudo/pautas.md` |
| **Reel** | Ter e Sáb | Vídeo do banco (`conteudo/reels.md`) |
| **Verificação** | Segunda | Alarme: avisa se o token da Meta expirou |
| **Limpeza** | Domingo | Apaga arte com mais de 60 dias |

O post de **vitrine** é o motor do projeto: gera prova social verdadeira,
dá motivo de retenção ao lojista (ele é divulgado de graça) e traz alcance
orgânico quando ele compartilha o post do próprio negócio.

Enquanto houver menos de `MIN_NEGOCIOS_VITRINE` (padrão 3) negócios
autorizados, **tudo sai institucional** — senão o mesmo lojista apareceria
toda semana e o perfil viraria panfleto de uma pessoa só.

---

## Antes de ligar: 2 mudanças fora deste repo

O robô **não funciona em modo vitrine** sem elas. Modo institucional
funciona desde já.

### 1. Persistir o segmento e o aceite de divulgação

Hoje `negocios/{uid}` **não guarda o segmento** escolhido no quiz — ele é
usado só em memória, pra injetar o `cardapioExemplo`, e depois se perde.
Isso além de bloquear a vitrine segmentada, impede qualquer relatório de
composição da base ("quantos % são alimentação?").

Em `moviki-app/index.html`, nos **dois** pontos que montam `dadosNegocio`
(cadastro por e-mail/senha e cadastro por Google), acrescentar:

```js
const dadosNegocio={
  nome:nome,status:'fechado',promocoes:[],eventos:[],fotos:[],
  markerLogo:'',cor:'#00f2fe',whiteLabel:false,
  cardapio:tpl,slug:slug,atualizadoEm:serverTimestamp(),
  segmento:d.template,            // <-- id do subtipo do quiz
  autorizaDivulgacao:false        // <-- opt-in, começa DESLIGADO
};
```

### 2. Liberar os dois campos nas regras do Firestore

`negocioValido()` usa `hasOnly` com lista exata — campo novo sem liberar na
regra faz o `setDoc` inteiro ser **rejeitado**. Na função `negocioValido`:

```
return d.keys().hasOnly(['nome','status','recado','cardapio','promocoes',
  'eventos','fotos','atualizadoEm','lat','lng','slug','whatsapp','email',
  'markerLogo','cor','whiteLabel','segmento','autorizaDivulgacao'])
  && ...
  && (!('segmento' in d) || (d.segmento is string && d.segmento.size() <= 40))
  && (!('autorizaDivulgacao' in d) || d.autorizaDivulgacao is bool)
```

Ambos **opcionais** na regra, pelo mesmo motivo de `whatsapp` e `email`:
contas antigas não têm esses campos e exigir presença quebraria qualquer
update futuro nelas.

### 3. (recomendado) Toggle no painel do lojista

Um switch em `index.html`: *"Deixar o Moviki divulgar meu negócio nas redes
sociais"*, gravando `autorizaDivulgacao`. Sem esse toggle nenhum lojista
consegue optar por entrar, e a vitrine nunca sai do institucional.

**O opt-in é obrigatório, não opcional.** Divulgar negócio de terceiro sem
aceite é problema de LGPD e de confiança. O robô filtra por
`autorizaDivulgacao === true` e há teste garantindo que nem ausência do
campo nem a string `"true"` passam.

---

## Instalação

### 1. Criar o repositório

`eikosistemas-pj/moviki-assistente-social`, **público**.

Público de propósito: a arte precisa de URL pública no instante em que o
Instagram cria o container, e `raw.githubusercontent.com` resolve isso sem
fornecedor externo, sem chave nova e sem custo. Não há segredo no código —
tudo vem de GitHub Secrets.

### 2. Secrets

`Settings → Secrets and variables → Actions`:

| Secret | Obrigatório | O que é |
|---|---|---|
| `PAGE_ACCESS_TOKEN` | sim | Token da Página do Facebook ligada ao Instagram |
| `IG_ACCOUNT_ID` | sim | ID da conta Instagram Business |
| `FACEBOOK_PAGE_ID` | não | Sem ele, não espelha no Facebook |
| `FIREBASE_PROJECT_ID` | vitrine | ID do projeto Firebase do Moviki |
| `FIREBASE_API_KEY` | vitrine | API key web do app |
| `ANTHROPIC_API_KEY` | não | Sem ela, as legendas saem do texto reserva |

`GITHUB_TOKEN` é injetado pelo próprio Actions — não precisa criar.

**Não existe secret de service account aqui, de propósito.** Uma chave de
Admin SDK daria escrita total no banco, inclusive em `comissoes`, `saques` e
`assinaturas`. Hospedar imagem e ler negócios não vale esse risco: a leitura
de `negocios` já é pública nas regras e é feita pela REST API sem
autenticação.

### 3. Token que não expira em 60 dias

Token de página comum expira e o robô **para em silêncio**. Gere um token de
**System User** no Business Manager (`Configurações do negócio → Usuários do
sistema → Gerar token`), com as permissões `instagram_basic`,
`instagram_content_publish`, `pages_show_list`, `pages_read_engagement`,
`pages_manage_posts`.

O workflow de segunda-feira testa o token toda semana. Se falhar, o job fica
vermelho e o GitHub manda e-mail.

### 4. Primeiro teste sem publicar

`Actions → Feed → Run workflow`, marcando **dry_run**. Ele monta a arte e a
legenda, imprime tudo no log e não publica nada.

---

## Banco de criativos

`assets/fundos/` guarda os fundos aprovados. O robô **não gera imagem por IA
na hora de publicar** — ele compõe: pega um fundo do banco e escreve por
cima os dados reais do negócio.

Por que assim:

- imagem gerada sem revisão pode ir ao ar torta às 10h da manhã;
- o post de vitrine precisa da **logo real** do lojista, senão não é prova
  social, é ilustração genérica;
- um fundo gerado uma vez é reusado centenas de vezes;
- a identidade visual fica consistente em vez de virar roleta.

Nomeie por macro-segmento: `alimentacao-01.jpg`, `servicos-02.jpg`,
`institucional-01.jpg`, `generico-01.jpg`. Sem fundo correspondente, cai no
genérico; sem nenhum fundo, cai num degradê na cor do lojista — degrada,
nunca quebra.

Reels **não ficam no git** (um vídeo de 8s pesa 5-10 MB e viraria ~800 MB de
histórico por ano). Ficam como asset de release, e `conteudo/reels.md` guarda
só o ponteiro.

---

## Mudar o que o robô fala

Editar `conteudo/pautas.md`. Não precisa tocar em código. Cada bloco tem
título e subtítulo (o que é impresso na arte) e um ângulo (a instrução pra
IA escrever a legenda).

---

## A trava de conteúdo

Todo texto passa por `src/compliance.py` antes de publicar. Camadas:

- **ganho_facil** — promessa de retorno no Programa de Parceiros. É o risco
  nº 1: prometer rendimento em programa de indicação multinível é o que faz
  um negócio legítimo ser tratado como pirâmide. Comissão pode ser
  explicada; rendimento não pode ser prometido.
- **resultado** — garantia de venda pro lojista (CDC art. 37).
- **fornecedor** — nomear a stack. Regra de ouro já existente no projeto.
- **prova_falsa** — número de clientes, prêmio ou depoimento inventado.
- **concorrente** — citar concorrente pelo nome.
- **dado_pessoal** — telefone, CPF ou e-mail solto no post.

Texto bloqueado é suavizado; se ainda assim não passar, entra o texto
reserva. Se a **reserva** também violar, o robô estoura de propósito — isso
é bug nosso e é melhor quebrar o workflow do que publicar.

```bash
pip install -r requirements.txt
python -m pytest tests/ -v
```

Se um teste de compliance quebrar, **não publique até consertar**.

---

## Fronteira com os outros repositórios

| Repo | Papel |
|---|---|
| `moviki-robo` | Dinheiro (Asaas, comissões, saque). Muda o mínimo. |
| `moviki-ai` | Conversa: WhatsApp e, futuramente, **DM e comentários do Instagram**. |
| `moviki-assistente-social` | **Publicação.** Só posta. |

Este repo **não** responde DM nem comentário — isso é do `moviki-ai`, que já
tem a arquitetura decidida (webhook Node) e vaga no teto de funções. Duas
implementações do mesmo recurso em linguagens diferentes seria dívida
técnica de graça.

Este repo **não escreve** em nenhuma coleção do Firestore. Só lê `negocios`.
