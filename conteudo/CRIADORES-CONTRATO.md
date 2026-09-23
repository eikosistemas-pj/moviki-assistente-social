# Contrato: peças dos criadores → redes oficiais do Moviki

Criado em 22/09/2026. É a "brecha" que o robô deixa aberta para as peças dos
influenciadores entrarem na rotação de **feed, story e reel**.

**Estado em 22/09/2026 (fim do dia):**

| Ponta | Estado |
|---|---|
| Robô (este repo) | pronto — lê `CRIADORES_URL` |
| Endpoint `www.moviki.com.br/api/criadores` (repo `moviki`) | **pronto** (GET para o robô, POST de tráfego para o painel do dono) |
| Regras `criador_pecas` (v27) e Storage `criadores/{uid}/` | **prontas**, publicar no console |
| Painel do dono — menu **Criadores** (aprovar, suspender, desempenho) | **pronto** (`eikoadm01.html` 2026-09-22-criadores) |
| Painel do criador — **Área do criador** no `parceiro.html` (enviar, Autorizar/Revogar, apagar, resultados) | **pronto** (`parceiro.html` 2026-09-22-criador) |

Enquanto o secret não existir, nada muda: o robô publica só o Material de
apoio.

---

## 1. As duas chaves (regra que não se negocia)

Uma peça de criador só vai ao ar com **as duas**:

| Chave | Quem gira | Onde |
|---|---|---|
| **Autorização** | o criador, no botão "Autorizar nas redes do Moviki" | painel do criador (`parceiro.html` em modo criador) |
| **Aprovação** | o Moviki (o Paulo) | painel do dono |

O botão do criador sozinho **nunca** publica nada. Motivos:

- a conta oficial é da marca: uma peça errada (promessa de ganho, música com
  direito autoral, rosto de terceiro, produto proibido) cai sobre o Moviki —
  e a conta antiga do Instagram já foi restringida pela Meta uma vez;
- vídeo não passa pela trava de texto: só olho humano confere o que é dito e
  mostrado;
- é a decisão já tomada no funil de criadores: "tudo entra como Aguardando;
  o dono aprova. Robô só pré-tria, nunca aprova".

**Revogar:** o criador pode tirar a autorização a qualquer momento. A peça
some do endpoint e o robô nunca mais a escolhe. Post já publicado sai só a
pedido, manualmente — isso precisa estar escrito no termo.

**Validade:** a autorização vence (termo v3.1: 12 meses). Vencida, o robô
recusa mesmo que o endpoint a devolva.

---

## 2. O endpoint (repo `moviki`, `api/criadores.js` — pronto em 22/09/2026)

- Endereço: `https://www.moviki.com.br/api/criadores` (usar o
  **www** — o apex redireciona e quebra chamada de servidor).
- Lê o Firestore com a conta de serviço **somente leitura** que o site já
  tem (`FIREBASE_SA_LEITURA`). Este repositório é público e **nunca**
  recebe credencial de banco.
- Devolve **só** peça com autorização válida, não revogada, não vencida
  **e** aprovada. O robô confere tudo de novo (segunda barreira).
- Conjunto **fechado** de campos. E-mail, telefone, chave Pix, CPF e dados
  de comissão do criador **nunca** saem.
- Opcional: fechar com `Authorization: Bearer <CRIADORES_SECRET>` (env na
  Vercel do site + secret aqui com o mesmo valor).

### Resposta

```json
{
  "versao": 1,
  "gerado_em": "2026-10-01T12:00:00Z",
  "itens": [
    {
      "id": "Kq3...",
      "formato": "reel",
      "midia": "video",
      "url": "https://firebasestorage.googleapis.com/...mp4?alt=media&token=...",
      "capa": "https://...jpg",
      "w": 1080, "h": 1920, "duracao": 32,
      "titulo": "Pastel saindo na feira de Tambaú",
      "legenda": "texto que o criador sugeriu (opcional)",
      "categoria": "alimentacao",
      "criador": { "uid": "abc", "nome": "Ana Souza", "arroba": "@ana.souza" },
      "autorizacao": {
        "autorizado": true,
        "versao_termo": "3.1",
        "em": "2026-09-25T12:00:00Z",
        "expira_em": "2027-09-25T12:00:00Z",
        "revogada_em": null
      },
      "aprovacao": { "aprovada": true, "em": "2026-09-26T12:00:00Z" }
    }
  ]
}
```

| Campo | Regra |
|---|---|
| `formato` | `feed` · `story` · `reel` |
| `midia` | `imagem` · `video`. Feed = só imagem. Reel = só vídeo. Story = os dois |
| `url` | `https://`, pública, baixável pela Meta sem login |
| `w`, `h` | feed de 4:5 a 1,91:1 · story e reel 9:16 |
| `duracao` | segundos. Reel de **3 a 90 s** (limite do Reel da Página do Facebook); story em vídeo de **3 a 60 s** |
| `categoria` | mesmos ids do material (`alimentacao`, `moda`, `pet`…), ou `geral` |
| `autorizado`, `aprovada` | **booleano** `true`. Texto `"true"` é recusado |
| `titulo` | vai ao ar se a legenda do criador for recusada — tem que ser limpo |

---

## 3. Modelo no Firestore — DEFINIDO (regras v27)

Coleção **na raiz**, por causa da regra "o Firestore não tem deny":
`criador_pecas/{id}`.

| Campo | Quem escreve |
|---|---|
| `uid`, `formato`, `midia`, `storagePath`, `url`, `capa` (opcional), `w`, `h`, `duracao`, `titulo` (≤ 120), `legenda` (≤ 2.200), `categoria`, `criadaEm` | o criador, só na criação, `hasOnly` fechado |
| `autorizaRedes` (bool), `autorizaRedesEm`, `termoVersao`, `revogadaEm` | o criador, só nesses campos |
| `status` (`aguardando` · `aprovada` · `recusada` · `suspensa`), `avaliadaEm`, `avaliadaPor`, `motivoRecusa` | **só o dono**, no menu Criadores do painel |

Regras que o painel do criador precisa respeitar (senão a gravação é recusada calada):

- **Quem é criador:** `parceiros/{uid}.status == 'aprovado'` **e**
  `parceiros/{uid}.criador == true`. A marca é dada pelo dono (menu
  Criadores > Quem é criador).
- **Criar:** `status: 'aguardando'`, `criadaEm: serverTimestamp()`,
  `uid` = o próprio, `url` começando com
  `https://firebasestorage.googleapis.com/`, `storagePath` começando com
  `criadores/{uid}/`. Campos fora da lista da tabela = recusado.
- **Arquivo:** subir em `criadores/{uid}/<nome-com-carimbo>` (JPG, PNG ou
  MP4, até 100 MB) e gravar em `url` o `getDownloadURL()`. Arquivo não se
  sobrescreve.
- **Autorizar:** `autorizaRedes: true`, `autorizaRedesEm: serverTimestamp()`,
  `termoVersao: '3.1'`, `revogadaEm: null`.
- **Revogar:** `autorizaRedes: false`, `revogadaEm: serverTimestamp()`.
- Conteúdo não se edita depois de criado: para trocar, apagar e enviar outra.
- Criador lê só as próprias peças e pode apagá-las.
- `expira_em` = `autorizaRedesEm` + 12 meses, calculado no endpoint.
- O crédito sai do **cadastro** (`parceiros/{uid}.nome` e `.arroba`), não do
  que o criador escreve na peça.

---

## 4. O que o robô faz com a peça

- **Legenda:** a do criador passa pela mesma conversão do material (sai
  `#publi`, "meu link" vira link da bio) e pela trava de conteúdo. Violou
  qualquer camada → sai a legenda reserva inteira (o robô **não reescreve**
  frase de terceiro). Sempre termina com **"Conteúdo de @arroba"**.
- **Story de imagem:** ganha um selo "Conteúdo de @arroba" na faixa de
  **78 % a 86 % da altura**. Oriente o criador a deixar essa faixa sem texto.
- **Mistura:** peça de criador fica com até **metade** dos posts de cada
  formato (`CRIADORES_PARTICIPACAO`, padrão 0,5). Nunca o mesmo criador duas
  vezes seguidas quando houver outro.
- **Rotação:** peça inédita primeiro; depois a publicada há mais tempo.

---

## 5. Regras para o criador (colocar no painel, junto do botão)

- Vídeo MP4 (H.264 + AAC), 1080×1920. Reel de 3 a 90 s; story de 3 a 60 s. Até 100 MB.
- **Sem música de biblioteca de plataforma** (Instagram/TikTok): a Meta
  silencia ou derruba vídeo com áudio protegido publicado por API. Voz,
  som ambiente ou trilha própria.
- **Sem marca d'água do TikTok** ou de outro app — o Instagram entrega
  menos esse tipo de vídeo.
- Nada de rosto ou tela de cliente real sem autorização dele; nada de
  preço, ganho, "renda", "garantido".
- Imagem JPG ou PNG. Story 1080×1920; feed 1080×1350 ou 1080×1080.

---

## 6. Para ligar

1. Endpoint no ar (repo `moviki`, `api/criadores.js`) e regras v27
   publicadas.
2. Secret `CRIADORES_URL` = `https://www.moviki.com.br/api/criadores` neste
   repo (Settings → Secrets → Actions). Pode criar já: sem peça liberada, o
   endpoint devolve lista vazia e nada muda.
3. Opcional: `CRIADORES_SECRET` (e a mesma env na Vercel do site).
4. Rodar Actions → Story → Run workflow com `origem: criador` e `dry_run`
   marcado. O log mostra quantas peças entraram e o motivo de cada recusa.
