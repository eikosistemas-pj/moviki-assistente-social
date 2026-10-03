# -*- coding: utf-8 -*-
"""
Configuracao central do moviki-assistente-social.

Le variaveis de ambiente (GitHub Secrets em producao) com padrao de
desenvolvimento local. NENHUM segredo mora neste arquivo.

Regra de ouro herdada do projeto: este repo NAO escreve em colecao
financeira e NAO guarda credencial de banco. Desde 04/09/2026 ele nem fala
mais com o Firestore: le a vitrine pronta em moviki.com.br/api/vitrine e
escreve so em estado/ (commitado pelo proprio workflow).
"""
import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

# Marca de versao do robo. Sai na primeira linha do log de cada execucao do
# feed: e assim que se confere, no Actions, qual versao rodou de verdade.
VERSAO = "2026-10-02-semcard"

# ----------------------------------------------------------------- caminhos
ASSETS_DIR = Path(os.environ.get("ASSETS_DIR", RAIZ / "assets"))
FUNDOS_DIR = ASSETS_DIR / "fundos"   # APOSENTADO em 22/09/2026 — arte.py nao le mais
REELS_DIR = ASSETS_DIR / "reels"
CONTEUDO_DIR = Path(os.environ.get("CONTEUDO_DIR", RAIZ / "conteudo"))

FONTE_TITULO = ASSETS_DIR / "fontes" / "Anton.ttf"
FONTE_FORTE = ASSETS_DIR / "fontes" / "Montserrat-ExtraBold.ttf"
FONTE_TEXTO = ASSETS_DIR / "fontes" / "Montserrat.ttf"
LOGO_PATH = ASSETS_DIR / "logo.png"

# ----------------------------------------------------------------- marca
MARCA = "Moviki"
SITE = "https://moviki.com.br"
APP = "https://app.moviki.com.br"
INSTAGRAM = "@moviki.oficial"
COR_PRIMARIA = "#00f2fe"   # mesma cor padrao gravada em negocios.cor
COR_FUNDO = "#0b1220"
COR_TEXTO = "#ffffff"

# ----------------------------------------------------------------- base
# ATE 04/09/2026 este robo lia /negocios direto na REST API do Firestore com a
# API key do app web. Isso deixou de ser possivel: para o Firebase, chamada com
# a chave publica e chamada de CLIENTE, e com o App Check enforcado ela passa a
# ser RECUSADA. O robo pararia de postar e o erro so apareceria dentro de um
# workflow que ninguem le todo dia.
#
# A saida NAO foi por chave de service account aqui: este repo e PUBLICO, e
# guardar credencial de banco num GitHub Secret so para ler dado que ja e
# publico e trocar um problema por outro maior.
#
# Agora o robo consome /api/vitrine no proprio site. Quem fala com o Firestore
# e o servidor da Vercel, com conta de servico SOMENTE LEITURA, e a lista ja
# vem filtrada pelo opt-in (autorizaDivulgacao) e com um conjunto FECHADO de
# campos. Menos credencial neste repo, menos leitura no Firestore, e o dado de
# quem NAO autorizou divulgacao nunca mais sai do banco.
VITRINE_URL = os.environ.get("VITRINE_URL", f"{SITE}/api/vitrine")

# Opcional: so precisa existir se um dia o endpoint for fechado por segredo
# (env VITRINE_SECRET no projeto Vercel do site). Vazio = endpoint aberto.
VITRINE_SECRET = os.environ.get("VITRINE_SECRET", "")

# Mantido: o run_verificar confere este secret como sinal de ambiente montado,
# e ele identifica o projeto nos logs. Nao e mais usado para ler o banco.
FIREBASE_PROJECT_ID = os.environ.get("FIREBASE_PROJECT_ID", "")

# Hospedagem publica da arte final. O Instagram exige uma URL publica no
# momento em que o container e criado; depois ele copia a imagem pro CDN
# dele e a URL de origem pode sumir. Por isso a arte e commitada no proprio
# repo (publico) e servida por raw.githubusercontent.com, e a limpeza
# semanal apaga o que passou de 60 dias.
#
# DECISAO CONSCIENTE: nao usamos Firebase Storage nem service account aqui.
# Uma chave de Admin SDK num GitHub Secret daria escrita total no banco,
# inclusive nas colecoes de dinheiro (comissoes/saques/assinaturas) — o
# oposto do isolamento que o projeto adota. Hospedar imagem nao vale esse
# risco. Se um dia precisar de Storage, criar conta de servico com papel
# SOMENTE de Storage, nunca a chave completa do projeto.
GH_REPO = os.environ.get("GITHUB_REPOSITORY", "eikosistemas-pj/moviki-assistente-social")
GH_BRANCH = os.environ.get("GITHUB_REF_NAME", "main")
PUBLICADO_DIR = RAIZ / "publicado"
RAW_BASE = f"https://raw.githubusercontent.com/{GH_REPO}/{GH_BRANCH}/publicado"
DIAS_RETENCAO_IMAGEM = int(os.environ.get("DIAS_RETENCAO_IMAGEM", "60"))

# Estado (rotacao, historico) vive em estado/ e e commitado de volta pelo
# workflow. Mesmo motivo: nao exige credencial de escrita em lugar nenhum.
ESTADO_DIR = RAIZ / "estado"

# ----------------------------------------------------------------- material de apoio
# 22/09/2026: o feed institucional passou a publicar as PECAS PRONTAS do
# Material de apoio do parceiro (moviki-app/material). Fonte unica: o robo
# le o catalogo AO VIVO no painel — arte nova que entra na aba do parceiro
# entra na rotacao do robo sozinha, sem mexer neste repo.
MATERIAL_BASE = os.environ.get("MATERIAL_BASE", "https://app.moviki.com.br").rstrip("/")
MATERIAL_CATALOGO = os.environ.get("MATERIAL_CATALOGO", f"{MATERIAL_BASE}/material/catalogo.json")

# Pecas que NAO podem ir para a pagina oficial. Todas estas trazem impresso
# na arte (ou falado no video) "CADASTRE-SE PELO LINK DESTE PARCEIRO",
# "ACESSE PELO LINK DESTE PARCEIRO" ou "fale comigo pelo link": na pagina do
# proprio Moviki a frase manda o leitor para um parceiro que nao existe.
# Peca nova com texto de parceiro entra AQUI (ou no secret MATERIAL_EXCLUIR,
# ids separados por virgula, sem mexer em codigo).
# 28/09/2026: lista LEGADA. Peca nova e barrada pelo campo `so_parceiro` do
# catalogo e pela triagem por imagem (src/triagem.py) — ninguem precisa
# lembrar de escrever aqui.
MATERIAL_EXCLUIR_FIXO = {
    # feed
    "feed-na-hora-foodtruck", "feed-quem-se-move", "feed-tudo-em-um-lugar",
    "quadrado-zero-comissao", "feed-na-hora-cidade", "feed-quem-se-move-2",
    "quadrado-na-hora",
    # story
    "story-na-hora", "story-tudo-em-um-lugar", "story-quem-se-move",
    # video
    "video-cada-negocio", "video-live-parceiro", "video-live-parceiro-4x5",
    "video-parceiro-chama-parceiro",
}
MATERIAL_EXCLUIR = MATERIAL_EXCLUIR_FIXO | {
    x.strip() for x in os.environ.get("MATERIAL_EXCLUIR", "").split(",") if x.strip()
}

# ----------------------------------------------------------------- criadores
# "Brecha" para as pecas dos INFLUENCIADORES (22/09/2026). O painel do
# criador (parceiro.html em modo criador) vai ter o botao "Autorizar nas
# redes do Moviki". O robo le as pecas liberadas num endpoint do site, no
# mesmo desenho da vitrine: quem fala com o Firestore e o servidor da
# Vercel, com conta SOMENTE LEITURA; este repo publico nunca recebe
# credencial de banco. Contrato completo em conteudo/CRIADORES-CONTRATO.md.
#
# VAZIO = FONTE DESLIGADA. Nada muda no robo ate o endpoint existir e o
# secret CRIADORES_URL ser criado no GitHub.
# 23/09/2026: o Modo Live esta em beta fechado. Enquanto este secret nao for
# "1", nenhuma peca do material que venda live (lives, transmissao, "vender ao
# vivo") vai para a pagina oficial — seria anunciar um recurso que o cliente
# ainda nao consegue usar. Ligar quando a live abrir para todos.
LIVE_NA_PAGINA = os.environ.get("LIVE_NA_PAGINA", "").strip() == "1"

CRIADORES_URL = os.environ.get("CRIADORES_URL", "").strip()
CRIADORES_SECRET = os.environ.get("CRIADORES_SECRET", "").strip()

# Fatia dos posts de cada formato que vai para peca de criador, quando houver
# peca liberada. 0.5 = metade. O resto continua saindo do Material de apoio,
# pra pagina nao virar mural de um influenciador so.
CRIADORES_PARTICIPACAO = float(os.environ.get("CRIADORES_PARTICIPACAO") or "0.5")

# Limites de video aceitos pelas duas redes ao mesmo tempo (Reels da Pagina
# do Facebook: 3 a 90 s). Video mais longo fica fora da rotacao de Reels.
REEL_DURACAO_MIN = 3
REEL_DURACAO_MAX = 90
# Story em video: Instagram e Pagina do Facebook aceitam ate 60 s.
STORY_DURACAO_MAX = 60

# ----------------------------------------------------------------- Meta
IG_ACCOUNT_ID = os.environ.get("IG_ACCOUNT_ID", "")
FACEBOOK_PAGE_ID = os.environ.get("FACEBOOK_PAGE_ID", "")
PAGE_ACCESS_TOKEN = os.environ.get("PAGE_ACCESS_TOKEN", "")
GRAPH = "https://graph.facebook.com/v25.0"

# ----------------------------------------------------------------- IA
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
# 28/09/2026: o padrao era "claude-3-5-haiku-latest", geracao 3.5 que sai de
# linha (platform.claude.com/docs/en/about-claude/model-deprecations). Modelo
# aposentado = IA falha e a legenda cai no texto reserva sem aviso.
ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL") or "claude-haiku-4-5"
# Modelo que LE IMAGEM na triagem "so parceiro" (src/triagem.py).
ANTHROPIC_MODEL_VISAO = os.environ.get("ANTHROPIC_MODEL_VISAO") or "claude-haiku-4-5"

# ----------------------------------------------------------------- regras
# Quantos negocios no minimo precisam ter autorizado divulgacao para o
# robo publicar um post de vitrine. Abaixo disso ele cai no institucional
# (evita repetir o mesmo comerciante toda semana no comeco da base).
MIN_NEGOCIOS_VITRINE = int(os.environ.get("MIN_NEGOCIOS_VITRINE", "3"))

# Nao repetir o mesmo negocio antes de N publicacoes.
JANELA_ANTI_REPETICAO = int(os.environ.get("JANELA_ANTI_REPETICAO", "10"))

# Teto de posts de VITRINE (lojista) por 7 dias corridos.
#
# PADRAO 0 = VITRINE DESLIGADA (22/09/2026). Os negocios com opt-in hoje sao
# contas de teste do proprio Paulo (base real = zero, confirmado em 16/09), e
# de 11 a 16/09 foram 4 posts seguidos delas na pagina oficial — prova
# social de mentira. Quando entrar o primeiro lojista real, criar o secret
# VITRINE_POR_SEMANA=1 no GitHub. Nada mais muda.
VITRINE_POR_SEMANA = int(os.environ.get("VITRINE_POR_SEMANA") or "0")  # secret vazio = desligada

# Slugs que nunca entram na vitrine, mesmo com opt-in. Conta demo e conta de
# teste nao sao "negocio real": publicar como se fossem e prova social falsa.
# Secret VITRINE_EXCLUIR, slugs separados por virgula, soma a esta lista.
VITRINE_EXCLUIR = {"hamburguermaster", "karina"} | {
    x.strip().lower() for x in os.environ.get("VITRINE_EXCLUIR", "").split(",") if x.strip()
}

# Modo seco: monta tudo e NAO publica. Usado nos testes e no dry-run.
DRY_RUN = os.environ.get("DRY_RUN", "").strip().lower() in ("1", "true", "sim")

# Modo SO FACEBOOK (24/08/2026).
#
# POR QUE EXISTE: a conta @moviki.app do Instagram esta sob restricao de
# integridade da Meta ("conta comercial proibida de anunciar"), e conta
# restrita nao consegue nem se conectar a uma Pagina. Sem conexao nao existe
# IG_ACCOUNT_ID, e sem ele o robo nao publica no Instagram.
#
# A Pagina do Facebook `Moviki.app` esta LIMPA. Entao o robo passa a publicar
# nela, sozinho, enquanto o Instagram nao volta. O projeto para de ficar
# refem de uma decisao da Meta.
#
# Ligar: secret/env SO_FACEBOOK=1
# Desligar (quando o Instagram voltar): apagar o secret. Nada mais muda.
SO_FACEBOOK = os.environ.get("SO_FACEBOOK", "").strip().lower() in ("1", "true", "sim")

# Instagram por formato (27/09/2026).
#
# O SO_FACEBOOK era tudo-ou-nada: desligou, feed + 2 stories/dia + 2 reels/semana
# caem de uma vez numa conta nova (@moviki.oficial). Conta nova com volume
# automatico repentino e o padrao que a Meta trata como spam — e a conta
# antiga ja foi restrita uma vez. Aqui se liga o Instagram FORMATO A FORMATO.
#
# Secret IG_FORMATOS, formatos separados por virgula:
#   feed           -> so o feed vai ao Instagram; story e reel seguem so na Pagina
#   feed,reel      -> feed e reel
#   (vazio)        -> todos os formatos (padrao quando SO_FACEBOOK nao existe)
#   nenhum         -> nada no Instagram (mesmo efeito do SO_FACEBOOK)
#
# RAMPA POR DATA (28/09/2026): formato@AAAA-MM-DD liga o formato sozinho a
# partir daquele dia (horario de Brasilia). Exemplo da rampa decidida:
#   feed,reel@2026-10-05,story@2026-10-12
# Ninguem precisa mexer em secret no dia 05 nem no dia 12.
#
# O Facebook recebe TUDO sempre: o que vai ao Instagram e espelhado na Pagina,
# o que nao vai sai direto nela. A Pagina nao perde nenhum post.
#
# SO_FACEBOOK continua mandando: existindo com "sim", nada vai ao Instagram.
# O FREIO automatico (src/freio.py) tambem manda: 2 falhas seguidas do
# Instagram tiram ele do ar por FREIO_HORAS, sozinho.
_IG_FORMATOS_BRUTO = os.environ.get("IG_FORMATOS", "").strip().lower()
IG_FORMATOS = {x.strip() for x in _IG_FORMATOS_BRUTO.split(",") if x.strip()}
FUSO_BR = timezone(timedelta(hours=-3))


def hoje_br():
    return datetime.now(FUSO_BR).date()


def rampa_ig():
    """{formato: data_de_inicio_ou_None} lida do IG_FORMATOS. Vazio = todos hoje."""
    saida = {}
    for tok in IG_FORMATOS:
        fmt, _, quando = tok.partition("@")
        fmt = fmt.strip()
        if not fmt:
            continue
        data = None
        if quando.strip():
            try:
                data = date.fromisoformat(quando.strip())
            except ValueError:
                # data mal escrita nunca LIGA nada por engano
                continue
        saida[fmt] = data
    return saida


def instagram_ligado(formato, hoje=None):
    """True se este formato (feed | story | reel) deve sair no Instagram hoje.
    Nao considera o freio — quem publica usa freio.no_instagram()."""
    if SO_FACEBOOK or not IG_ACCOUNT_ID:
        return False
    if not IG_FORMATOS:
        return True
    rampa = rampa_ig()
    if "nenhum" in rampa:
        return False
    if formato not in rampa:
        return False
    inicio = rampa[formato]
    return inicio is None or (hoje or hoje_br()) >= inicio


# Post em PARCERIA com o criador (28/09/2026). Peca de criador no feed ou no
# reel do Instagram sai com convite de collab para o @ dele: se ele aceitar
# no app, o post aparece no perfil dos dois e o publico dele ve o Moviki.
# Story nao aceita parceria. Desligar: secret COLLAB_CRIADORES = nao.
COLLAB_CRIADORES = os.environ.get("COLLAB_CRIADORES", "").strip().lower() not in ("nao", "não", "0", "false")

# Metas de seguidores do Instagram mostradas no painel do dono (28/09/2026).
# "alvo@AAAA-MM-DD", separadas por virgula. Padrao: 5.000 em 30 dias e
# 10.000 em 90 dias, contados de 28/09/2026 (2.297 seguidores).
META_SEGUIDORES = os.environ.get("META_SEGUIDORES") or "5000@2026-10-28,10000@2026-12-27"

# Freio automatico do Instagram (28/09/2026).
FREIO_FALHAS = int(os.environ.get("FREIO_FALHAS") or "2")
FREIO_HORAS = int(os.environ.get("FREIO_HORAS") or "72")


# Hashtags no Instagram (27/09/2026).
#
# Desde dez/2025 o Instagram aceita no maximo 5 hashtags por post. O robo
# mandava 10 no PRIMEIRO COMENTARIO — acima do limite e, pior, comentario
# automatico, o que a regra permanente da conta nova proibe ("nunca automacao
# de comentarios ou DM"). Agora vao no fim da LEGENDA, no maximo 5, escolhidas
# pelo ramo da peca. Nenhum comentario automatico.
HASHTAGS_MAX = 5

# Alarme do plano B. Se o Instagram falha, o post sai na Pagina (nao se perde)
# e este arquivo e criado; o ultimo passo do workflow le o arquivo e deixa o
# job VERMELHO — o GitHub manda e-mail. Sem isso o Instagram podia morrer por
# semanas com o log verde (foi o que aconteceu com o reel de 24/08 a 22/09).
ALERTA_INSTAGRAM = os.environ.get("ALERTA_INSTAGRAM", "/tmp/alerta-instagram.txt")
