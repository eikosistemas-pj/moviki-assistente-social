# -*- coding: utf-8 -*-
"""
Geracao de texto (Anthropic), com reserva compliant.

Regra dura: NENHUM texto vai pro ar sem passar por compliance.garantir().
Se a IA cair, se a chave faltar ou se a resposta violar a trava, o post sai
mesmo assim — com o texto reserva. Falha de IA nao pode furar o calendario.
"""
import datetime

from . import compliance, config
from . import util_net as net

TOM = """\
Voce escreve as legendas do Instagram do Moviki, um app que mostra em tempo
real onde negocios itinerantes (food truck, carrinho, barraca, feira, servico
movel) estao AGORA.

TOM: direto, brasileiro, sem enrolacao. Fala com dono de negocio de rua e com
quem procura esses negocios. Frases curtas. Zero linguagem corporativa.

PROIBIDO (o post e bloqueado se aparecer):
- prometer ganho, renda extra, retorno ou lucro de qualquer valor;
- garantir resultado de venda ("vai vender mais", "aumente X%");
- citar fornecedor ou tecnologia por tras do produto;
- inventar numero de clientes, premio, avaliacao ou depoimento;
- citar concorrente pelo nome;
- colocar telefone, e-mail ou CPF no texto.

SEMPRE: no maximo 4 linhas de texto, 1 chamada pra acao no fim.
Nunca use markdown. Escreva texto puro, com emoji com moderacao.
"""


def disponivel():
    return bool(config.ANTHROPIC_API_KEY)


def escrever(instrucao, reserva, max_tokens=500):
    """Pede o texto pra IA e devolve JA validado pela trava.

    `reserva` e obrigatoria e precisa estar limpa — e a rede de seguranca.
    """
    if not disponivel():
        print("IA indisponivel (sem ANTHROPIC_API_KEY) -> texto reserva")
        return compliance.garantir(reserva, reserva)

    try:
        r = net.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": config.ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": config.ANTHROPIC_MODEL,
                "max_tokens": max_tokens,
                "system": TOM,
                "messages": [{"role": "user", "content": instrucao}],
            },
        )
        dados = r.json()
        if "error" in dados:
            raise RuntimeError(dados["error"].get("message", "erro IA"))
        texto = "".join(
            b.get("text", "") for b in dados.get("content", []) if b.get("type") == "text"
        ).strip()
        if not texto:
            raise RuntimeError("resposta vazia")
    except Exception as e:  # noqa: BLE001
        print(f"aviso: IA falhou ({e}) -> texto reserva")
        return compliance.garantir(reserva, reserva)

    return compliance.garantir(texto, reserva)


# ---------------------------------------------------------------------------
# 03/10/2026 — CONFERENCIA DA CHAVE (usada pelo alarme de segunda).
#
# Falha de IA nao derruba o post: cai no texto reserva, calado. Por isso uma
# chave vencida, desativada ou apagada passaria semanas sem ninguem notar —
# as legendas viram todas o texto reserva e a triagem "so parceiro" desliga.
# Esta conferencia consulta o MODELO na API (GET /v1/models/{id}): nao gera
# texto, nao gasta credito. 401 = chave recusada; 404 = modelo aposentado.
# ---------------------------------------------------------------------------

def _data(txt):
    txt = (txt or "").strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.datetime.strptime(txt, fmt).date()
        except ValueError:
            pass
    raise RuntimeError(f"ANTHROPIC_CHAVE_VALIDADE invalida: '{txt}' (use AAAA-MM-DD ou DD/MM/AAAA)")


def _modelo_ok(modelo):
    r = net.get(
        f"https://api.anthropic.com/v1/models/{modelo}",
        headers={"x-api-key": config.ANTHROPIC_API_KEY, "anthropic-version": "2023-06-01"},
    )
    if r.status_code == 200:
        return
    if r.status_code in (401, 403):
        raise RuntimeError("a Anthropic RECUSOU a chave (vencida, desativada ou apagada no Console). "
                           "Criar chave nova e trocar o secret ANTHROPIC_API_KEY deste repositorio")
    if r.status_code == 404:
        raise RuntimeError(f"o modelo '{modelo}' nao existe mais (aposentado). "
                           "Trocar o padrao em src/config.py")
    raise RuntimeError(f"resposta inesperada da Anthropic: HTTP {r.status_code}")


def conferir_chave(hoje=None):
    """Devolve um resumo se a IA esta pronta; levanta RuntimeError se nao."""
    if not disponivel():
        raise RuntimeError("secret ANTHROPIC_API_KEY ausente — legendas saem so com texto reserva "
                           "e a triagem so parceiro fica desligada")
    modelos = sorted({config.ANTHROPIC_MODEL, config.ANTHROPIC_MODEL_VISAO})
    for m in modelos:
        _modelo_ok(m)
    validade = "sem validade cadastrada"
    if config.ANTHROPIC_CHAVE_VALIDADE:
        fim = _data(config.ANTHROPIC_CHAVE_VALIDADE)
        hoje = hoje or datetime.date.today()
        faltam = (fim - hoje).days
        if faltam < 0:
            raise RuntimeError(f"a chave venceu em {fim:%d/%m/%Y}. Criar chave nova no Console")
        if faltam <= config.ANTHROPIC_AVISO_DIAS:
            raise RuntimeError(f"a chave vence em {fim:%d/%m/%Y} (faltam {faltam} dias). "
                               "Criar chave nova no Console e trocar o secret ANTHROPIC_API_KEY")
        validade = f"vence em {fim:%d/%m/%Y} (faltam {faltam} dias)"
    return f"chave aceita | modelos: {', '.join(modelos)} | {validade}"
