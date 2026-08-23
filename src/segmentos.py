# -*- coding: utf-8 -*-
"""
Espelho da arvore de segmentos do quiz (moviki-app/quiz/quiz-segmentos.js).

9 macros / 27 subtipos. Serve pra dois usos:
  - rotulo legivel no post ("Hamburgueria / Food Truck");
  - escolher o fundo do banco de criativos por macro.

MANTER SINCRONIZADO com o quiz. Se entrar segmento novo la, entra aqui —
senao o post cai no fundo generico (degrada, nao quebra).
"""

MACROS = {
    "alimentacao": "Alimentacao",
    "hortifruti": "Hortifruti / Feira",
    "bebidas": "Bebidas",
    "moda": "Moda / Brecho",
    "artesanato": "Artesanato",
    "servicos": "Servicos",
    "belezaperfumaria": "Beleza & Perfumaria",
    "papelarialivraria": "Papelaria & Livraria",
    "tecnologia": "Tecnologia / Acessorios",
}

# subtipo -> (macro, rotulo)
SUBTIPOS = {
    "foodtruck": ("alimentacao", "Hamburgueria / Food Truck"),
    "pizzaria": ("alimentacao", "Pizzaria"),
    "lanches": ("alimentacao", "Pastelaria / Lanches de Rua"),
    "pratofeito": ("alimentacao", "Prato Feito / Marmitex"),
    "pipoca": ("alimentacao", "Pipoca / Doces e Guloseimas"),
    "feira": ("hortifruti", "Verduras, Legumes e Frutas"),
    "floricultura": ("hortifruti", "Floricultura / Plantas e Mudas"),
    "sorvete": ("bebidas", "Sorvete / Picole / Acai"),
    "suco": ("bebidas", "Suco / Vitamina Natural"),
    "cafeteria": ("bebidas", "Cafe / Cafeteria Movel"),
    "aguacoco": ("bebidas", "Agua de Coco / Outras Bebidas"),
    "barmovel": ("bebidas", "Bar Movel / Chopp / Drinks"),
    "roupas": ("moda", "Roupas"),
    "calcados": ("moda", "Calcados"),
    "acessorios": ("moda", "Acessorios / Bijuterias"),
    "decoracao": ("artesanato", "Decoracao / Utilidades"),
    "bijuteriaartesanal": ("artesanato", "Bijuteria Artesanal"),
    "manufaturados": ("artesanato", "Outros Manufaturados"),
    "petshop": ("servicos", "Petshop Movel / Banho e Tosa"),
    "barbeariasalao": ("servicos", "Barbearia / Salao Movel"),
    "estetica": ("servicos", "Estetica / Manicure Movel"),
    "lavagemcarro": ("servicos", "Lavagem de Carro Movel"),
    "chaveiroconserto": ("servicos", "Chaveiro / Conserto Rapido"),
    "perfumariacosmeticos": ("belezaperfumaria", "Perfumaria / Cosmeticos"),
    "livrariapapelaria": ("papelarialivraria", "Livraria / Papelaria de Rua"),
    "acessorioscelular": ("tecnologia", "Acessorios de Celular"),
    "relogiosgadgets": ("tecnologia", "Relogios e Gadgets"),
}

# Chamada de topo do card, por macro. Deixa o post menos repetitivo.
CHAMADAS = {
    "alimentacao": "TA ABERTO AGORA",
    "hortifruti": "FEIRA DE HOJE",
    "bebidas": "GELADO E PERTO",
    "moda": "ACHOU NO MOVIKI",
    "artesanato": "FEITO A MAO",
    "servicos": "ATENDE HOJE",
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
    return CHAMADAS.get(macro_de(segmento), "ESTA NO MOVIKI")
