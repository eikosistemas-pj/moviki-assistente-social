# -*- coding: utf-8 -*-
"""
Testes da trava de conteudo.

Estes testes sao a defesa mais importante do repo: um post que promete
ganho no Programa de Parceiros pode enquadrar o Moviki como piramide.
Se algum destes quebrar, NAO publicar ate consertar.
"""
import pytest

from src import compliance


# ------------------------------------------------------------- deve BLOQUEAR
@pytest.mark.parametrize("texto,camada", [
    ("Ganhe R$ 5.000 por mes indicando o Moviki", "ganho_facil"),
    ("Renda extra garantida pra quem indicar", "ganho_facil"),
    ("Dinheiro facil no automatico", "ganho_facil"),
    ("Fature ate R$ 900 no primeiro mes", "ganho_facil"),
    ("Voce vai vender mais com o Moviki", "resultado"),
    ("Aumente 300% suas vendas", "resultado"),
    ("Garantimos mais clientes pro seu carrinho", "resultado"),
    ("Rodamos no Firebase com deploy na Vercel", "fornecedor"),
    ("Nosso atendente usa Claude da Anthropic", "fornecedor"),
    ("Mais de 5 mil lojistas ja usam", "prova_falsa"),
    ("O maior aplicativo do Brasil pra food truck", "prova_falsa"),
    ("Melhor que o iFood pro seu negocio", "concorrente"),
    ("Chama no (81) 99999-8888", "dado_pessoal"),
])
def test_bloqueia(texto, camada):
    achados = dict(compliance.violacoes(texto))
    assert camada in achados, f"deveria bloquear {camada!r} em: {texto!r}"


# ------------------------------------------------------------- deve PASSAR
@pytest.mark.parametrize("texto", [
    "Seu negocio tem endereco. So que ele muda todo dia.",
    "O Moviki mostra onde voce esta agora, em tempo real.",
    "Indicar da comissao recorrente enquanto o indicado for cliente.",
    "Testa 30 dias. Se nao servir, voce sai, sem multa.",
    "Burger do Ze esta no Moviki. Veja se esta aberto agora.",
    "Um link so, pra sempre: moviki.com.br/seunegocio",
    "Cardapio digital que voce mesmo edita quando o preco muda.",
])
def test_libera(texto):
    assert compliance.violacoes(texto) == [], f"nao deveria bloquear: {texto!r}"


# ------------------------------------------------------------- comportamento
def test_garantir_usa_reserva_quando_texto_sujo():
    sujo = "Ganhe R$ 3.000 por mes com o Moviki"
    limpo = "Conheca o Programa de Parceiros do Moviki."
    assert compliance.garantir(sujo, limpo) == limpo


def test_garantir_devolve_texto_quando_limpo():
    ok = "O Moviki mostra onde voce esta agora."
    assert compliance.garantir(ok, "reserva") == ok


def test_garantir_estoura_se_reserva_suja():
    """Reserva suja e bug nosso. Preferimos quebrar o workflow a publicar."""
    with pytest.raises(RuntimeError):
        compliance.garantir("Ganhe R$ 5.000 facil", "Renda extra garantida!")


def test_suavizar_reescreve_termo_de_risco():
    assert "renda extra" not in compliance.suavizar("Tenha renda extra").lower()


def test_acento_nao_escapa_da_trava():
    """A trava normaliza acento: escrever certo nao driba o filtro."""
    assert compliance.violacoes("Aumente sua rentabilidade") != []
