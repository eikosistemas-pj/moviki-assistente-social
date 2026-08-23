# -*- coding: utf-8 -*-
"""
Trava de conteudo do Moviki. Roda ANTES de publicar, em TODO texto
(legenda, arte e roteiro de reel), venha da IA ou de pauta escrita a mao.

Herdou a ARQUITETURA da trava do agente original (camadas de regex +
`garantir()` com texto reserva), mas o dicionario e outro: la o risco era
ANVISA/cosmetico, aqui os riscos sao outros e mais graves.

CAMADAS
  GANHO_FACIL  - promessa de ganho no Programa de Parceiros. E o risco
                 numero 1 do projeto: prometer retorno financeiro em
                 programa de indicacao multinivel e o que faz um negocio
                 legitimo ser tratado como piramide (CVM/PROCON/MP).
                 Comissao pode ser explicada; RENDIMENTO nao pode ser
                 prometido.
  RESULTADO    - garantia de resultado comercial pro lojista
                 ("vai vender mais", "aumente 300%"). Publicidade
                 enganosa (CDC art. 37).
  FORNECEDOR   - nomear a stack/fornecedores. Regra de ouro ja existente
                 no Mapa Mestre, valida em pagina publica, no atendente de
                 IA e agora tambem aqui.
  PROVA_FALSA  - depoimento/numero inventado. Regra ja existente: nao
                 fabricar prova social.
  CONCORRENTE  - citar concorrente pelo nome (risco de conflito e de dar
                 palco de graca).
  DADO_PESSOAL - telefone/CPF/e-mail solto no texto do post.

Uso:
    texto = garantir(texto_gerado, texto_reserva)
"""
import re
import unicodedata

# --------------------------------------------------------------------- camadas
GANHO_FACIL = [
    r"\brenda\s+(extra|garantida|passiva|f[áa]cil)\b",
    r"\bganhe?\s+(at[ée]\s+)?r\$\s*\d",
    r"\bfature?\s+(at[ée]\s+)?r\$\s*\d",
    r"\blucr(e|o)\s+(at[ée]\s+)?r\$\s*\d",
    r"\bganho\s+garantido\b|\bretorno\s+garantido\b",
    r"\bdinheiro\s+(f[áa]cil|r[áa]pido|no\s+autom[áa]tico)\b",
    r"\bfique\s+rico\b|\benriqueca\b|\bindepend[êe]ncia\s+financeira\b",
    r"\bsem\s+(fazer\s+)?(nada|esfor[çc]o)\b",
    r"\bganhe\s+enquanto\s+dorme\b",
    r"\bmultipliqu?e\s+(o\s+)?seu\s+dinheiro\b",
    r"\binvestimento\s+garantido\b|\brentabilidade\b",
    r"\bat[ée]\s+\d+\s*%\s+(de\s+)?(lucro|retorno|ganho)\b",
]
RESULTADO = [
    r"\b(vai|voc[êe]\s+vai)\s+vender\s+mais\b",
    r"\bgarant(o|imos|ido|ia\s+de)\s+(mais\s+)?(venda|cliente|resultado|faturamento)",
    r"\baument(e|o)\s+(de\s+)?\d+\s*%",
    r"\bdobr(e|ar)\s+(as\s+)?vendas\b|\btriplique\b",
    r"\bresultado\s+garantido\b|\bsucesso\s+garantido\b",
    r"\bnunca\s+mais\s+(vai\s+)?(ficar\s+sem|perder)\s+cliente",
    r"\b100%\s+de\s+(sucesso|efic|resultado)",
]
FORNECEDOR = [
    r"\basaas\b", r"\bfirebase\b", r"\bvercel\b", r"\bgoogle\s+cloud\b",
    r"\banthropic\b", r"\bclaude\b", r"\bopenai\b", r"\bchatgpt\b",
    r"\bhostgator\b", r"\bresend\b", r"\btitan\b", r"\bcloudflare\b",
    r"\bsupabase\b", r"\baws\b", r"\bstripe\b", r"\bmercado\s*pago\b",
]
PROVA_FALSA = [
    r"\bmais\s+de\s+[\d\.]+\s*(mil\s+)?(clientes|lojistas|usu[áa]rios|neg[óo]cios)\b",
    r"\b[\d\.]+\s*(mil|milh[õo]es)\s+de\s+(clientes|usu[áa]rios|downloads|vendas)\b",
    r"\bo\s+n[ºo°]?\s*1\s+do\s+brasil\b|\bl[íi]der\s+de\s+mercado\b",
    r"\bo\s+maior\s+(app|aplicativo|sistema|plataforma)\s+d[eo]\b",
    r"\beleito\s+o\s+melhor\b|\bpremiad[oa]\b",
    r"\bavaliado\s+em\s+[\d,\.]+\s+estrelas\b",
    r"\bmilhares\s+de\s+(clientes|lojistas|pessoas)\s+j[áa]\b",
]
CONCORRENTE = [
    r"\bifood\b", r"\brappi\b", r"\buber\s*eats\b", r"\bdelivery\s*much\b",
    r"\bgoomer\b", r"\banota\s*a[íi]\b", r"\bcardapio\s*web\b",
    r"\bmelhor\s+que\s+o\s+\w+\b",
]
DADO_PESSOAL = [
    r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b",                 # CPF
    r"\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b",           # CNPJ
    r"\b\(?\d{2}\)?\s*9?\d{4}[-\s]?\d{4}\b",          # telefone
    r"[\w\.\-]+@[\w\.\-]+\.\w{2,}",                    # e-mail
]

CAMADAS = {
    "ganho_facil": GANHO_FACIL,
    "resultado": RESULTADO,
    "fornecedor": FORNECEDOR,
    "prova_falsa": PROVA_FALSA,
    "concorrente": CONCORRENTE,
    "dado_pessoal": DADO_PESSOAL,
}

# Trocas seguras: reescreve em vez de bloquear, quando existe forma correta.
SUAVIZAR = [
    (r"\brenda\s+extra\b", "uma nova fonte de receita"),
    (r"\brenda\s+passiva\b", "comissao recorrente"),
    (r"\bganho\s+garantido\b", "comissao por indicacao"),
    (r"\bvai\s+vender\s+mais\b", "fica mais facil de achar"),
    (r"\bgarantimos\b", "trabalhamos para"),
    (r"\bdinheiro\s+f[áa]cil\b", "comissao por indicacao"),
    (r"\bfique\s+rico\b", "construa algo seu"),
]


# --------------------------------------------------------------------- motor
def _normalizar(texto):
    """Minusculas sem acento, so pra CASAR o regex (nao altera a saida)."""
    t = (texto or "").lower()
    return "".join(c for c in unicodedata.normalize("NFD", t)
                   if unicodedata.category(c) != "Mn")


def _casa(padroes, texto, texto_sem_acento):
    for p in padroes:
        if re.search(p, texto, re.I) or re.search(p, texto_sem_acento, re.I):
            return p
    return None


def violacoes(texto):
    """Lista as camadas violadas. Vazio = texto liberado."""
    t = texto or ""
    tn = _normalizar(t)
    achados = []
    for nome, padroes in CAMADAS.items():
        p = _casa(padroes, t, tn)
        if p:
            achados.append((nome, p))
    return achados


def suavizar(texto):
    """Aplica as trocas seguras. Nao garante aprovacao — so reduz atrito."""
    t = texto or ""
    for padrao, troca in SUAVIZAR:
        t = re.sub(padrao, troca, t, flags=re.I)
    return t


def garantir(texto, reserva):
    """Devolve `texto` se estiver limpo; senao tenta suavizar; senao usa a
    reserva. A reserva TAMBEM e checada — se ela estiver suja, isso e bug
    nosso e o robo estoura na hora, em vez de publicar algo proibido.
    """
    achados = violacoes(texto)
    if not achados:
        return texto

    print("compliance: bloqueado ->", ", ".join(f"{n}({p})" for n, p in achados))

    tentativa = suavizar(texto)
    if not violacoes(tentativa):
        print("compliance: suavizado e liberado")
        return tentativa

    if violacoes(reserva):
        raise RuntimeError(
            "compliance: o texto reserva TAMBEM viola a trava — corrigir o "
            "codigo, nao publicar."
        )
    print("compliance: usando texto reserva")
    return reserva
