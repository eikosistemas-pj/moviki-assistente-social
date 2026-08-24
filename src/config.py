# -*- coding: utf-8 -*-
"""
Configuracao central do moviki-assistente-social.

Le variaveis de ambiente (GitHub Secrets em producao) com padrao de
desenvolvimento local. NENHUM segredo mora neste arquivo.

Regra de ouro herdada do projeto: este repo NAO escreve em colecao
financeira. Ele so LE 'negocios' (leitura ja publica nas regras) e escreve
exclusivamente em 'social_estado/{doc}', que e dele.
"""
import os
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

# ----------------------------------------------------------------- caminhos
ASSETS_DIR = Path(os.environ.get("ASSETS_DIR", RAIZ / "assets"))
FUNDOS_DIR = ASSETS_DIR / "fundos"
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
INSTAGRAM = "@moviki.app"
COR_PRIMARIA = "#00f2fe"   # mesma cor padrao gravada em negocios.cor
COR_FUNDO = "#0b1220"
COR_TEXTO = "#ffffff"

# ----------------------------------------------------------------- Firebase
# Leitura de 'negocios' e publica nas regras, entao o robo usa a REST API do
# Firestore so com a API key do proprio app web. NAO usamos service account
# aqui de proposito: chave de Admin SDK da acesso de ESCRITA TOTAL ao banco,
# inclusive as colecoes de dinheiro. Este repo nao precisa disso.
FIREBASE_PROJECT_ID = os.environ.get("FIREBASE_PROJECT_ID", "")
FIREBASE_API_KEY = os.environ.get("FIREBASE_API_KEY", "")
FIRESTORE_BASE = (
    f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}"
    f"/databases/(default)/documents"
)

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

# ----------------------------------------------------------------- Meta
IG_ACCOUNT_ID = os.environ.get("IG_ACCOUNT_ID", "")
FACEBOOK_PAGE_ID = os.environ.get("FACEBOOK_PAGE_ID", "")
PAGE_ACCESS_TOKEN = os.environ.get("PAGE_ACCESS_TOKEN", "")
GRAPH = "https://graph.facebook.com/v25.0"

# ----------------------------------------------------------------- IA
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-3-5-haiku-latest")

# ----------------------------------------------------------------- regras
# Quantos negocios no minimo precisam ter autorizado divulgacao para o
# robo publicar um post de vitrine. Abaixo disso ele cai no institucional
# (evita repetir o mesmo comerciante toda semana no comeco da base).
MIN_NEGOCIOS_VITRINE = int(os.environ.get("MIN_NEGOCIOS_VITRINE", "3"))

# Nao repetir o mesmo negocio antes de N publicacoes.
JANELA_ANTI_REPETICAO = int(os.environ.get("JANELA_ANTI_REPETICAO", "10"))

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
