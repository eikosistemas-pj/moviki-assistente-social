# -*- coding: utf-8 -*-
"""
Geracao de texto (Anthropic), com reserva compliant.

Regra dura: NENHUM texto vai pro ar sem passar por compliance.garantir().
Se a IA cair, se a chave faltar ou se a resposta violar a trava, o post sai
mesmo assim — com o texto reserva. Falha de IA nao pode furar o calendario.
"""
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
