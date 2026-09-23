# -*- coding: utf-8 -*-
"""
Espelho da arvore de segmentos do quiz (moviki-app/quiz/quiz-segmentos.js).

10 macros / 31 subtipos. Serve pra dois usos:
  - rotulo legivel no post ("Hamburgueria / Food Truck");
  - etiqueta de topo da arte de vitrine, por macro.

MANTER SINCRONIZADO com o quiz. Se entrar segmento novo la, entra aqui —
senao o post sai sem rotulo (degrada, nao quebra).

22/09/2026: rotulos e chamadas passaram a ter ACENTO. Eles sao impressos na
arte e na legenda publica ("Alimentacao", "Servicos" iam ao ar sem acento).
E a chamada "TA ABERTO AGORA" saiu: o robo nao sabe se o negocio esta aberto
na hora do post — afirmar isso e informacao falsa sobre terceiro.
"""

MACROS = {
    "alimentacao": "Alimentação",
    "hortifruti": "Hortifrúti / Feira",
    "bebidas": "Bebidas",
    "suplementos": "Suplementos e Nutrição",
    "moda": "Moda / Brechó",
    "artesanato": "Artesanato",
    "servicos": "Serviços",
    "belezaperfumaria": "Beleza e Perfumaria",
    "papelarialivraria": "Papelaria e Livraria",
    "tecnologia": "Tecnologia / Acessórios",
}

# subtipo -> (macro, rotulo)
SUBTIPOS = {
    "foodtruck": ("alimentacao", "Hamburgueria / Food Truck"),
    "pizzaria": ("alimentacao", "Pizzaria"),
    "sushi": ("alimentacao", "Sushi / Comida Japonesa"),
    "lanches": ("alimentacao", "Pastelaria / Lanches de Rua"),
    "pratofeito": ("alimentacao", "Prato Feito / Marmitex"),
    "pipoca": ("alimentacao", "Pipoca / Doces e Guloseimas"),
    "feira": ("hortifruti", "Verduras, Legumes e Frutas"),
    "floricultura": ("hortifruti", "Floricultura / Plantas e Mudas"),
    "sorvete": ("bebidas", "Sorvete / Picolé / Açaí"),
    "suco": ("bebidas", "Suco / Vitamina Natural"),
    "cafeteria": ("bebidas", "Café / Cafeteria Móvel"),
    "aguacoco": ("bebidas", "Água de Coco / Outras Bebidas"),
    "barmovel": ("bebidas", "Bar Móvel / Chopp / Drinks"),
    "suplementosesportivos": ("suplementos", "Suplementos / Nutrição Esportiva"),
    "naturaisvitaminas": ("suplementos", "Produtos Naturais / Vitaminas"),
    "roupas": ("moda", "Roupas"),
    "calcados": ("moda", "Calçados"),
    "acessorios": ("moda", "Acessórios / Bijuterias"),
    "decoracao": ("artesanato", "Decoração / Utilidades"),
    "bijuteriaartesanal": ("artesanato", "Bijuteria Artesanal"),
    "manufaturados": ("artesanato", "Outros Manufaturados"),
    "petshop": ("servicos", "Petshop Móvel / Banho e Tosa"),
    "barbeariasalao": ("servicos", "Barbearia / Salão Móvel"),
    "estetica": ("servicos", "Estética / Manicure Móvel"),
    "lavagemcarro": ("servicos", "Lavagem de Carro Móvel"),
    "chaveiroconserto": ("servicos", "Chaveiro / Conserto Rápido"),
    "otica": ("servicos", "Ótica / Óculos"),
    "perfumariacosmeticos": ("belezaperfumaria", "Perfumaria / Cosméticos"),
    "livrariapapelaria": ("papelarialivraria", "Livraria / Papelaria de Rua"),
    "acessorioscelular": ("tecnologia", "Acessórios de Celular"),
    "relogiosgadgets": ("tecnologia", "Relógios e Gadgets"),
}

PADRAO = "ESTÁ NO MOVIKI"

# Etiqueta de topo do card, por macro. So frase que o robo consegue
# sustentar sem saber nada alem do cadastro.
CHAMADAS = {
    "alimentacao": "SABOR NO MAPA",
    "hortifruti": "DA FEIRA PRO MAPA",
    "bebidas": "PRA REFRESCAR",
    # Suplementos fica no texto neutro de proposito: chamada tipo "GANHE MASSA" /
    # "SECA BARRIGA" seria alegacao de saude/resultado, barrada pela ANVISA e pelas
    # politicas de Meta e Google. Nao trocar.
    "suplementos": "ACHOU NO MOVIKI",
    "moda": "ACHOU NO MOVIKI",
    "artesanato": "FEITO À MÃO",
    "servicos": "SERVIÇO NO MAPA",
    "belezaperfumaria": "ACHOU NO MOVIKI",
    "papelarialivraria": "ACHOU NO MOVIKI",
    "tecnologia": "ACHOU NO MOVIKI",
}


def macro_de(segmento):
    """Aceita id de subtipo OU de macro. Devolve o id do macro."""
    s = (segmento or "").strip().lower()
    if s in MACROS:
        return s
    if s in SUBTIPOS:
        return SUBTIPOS[s][0]
    return ""


def rotulo(segmento):
    """Nome legivel pra imprimir no post."""
    s = (segmento or "").strip().lower()
    if s in SUBTIPOS:
        return SUBTIPOS[s][1]
    return MACROS.get(s, "")


def chamada(segmento):
    return CHAMADAS.get(macro_de(segmento), PADRAO)
