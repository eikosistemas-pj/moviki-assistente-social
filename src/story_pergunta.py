# -*- coding: utf-8 -*-
"""
PERGUNTA DO DIA no story (23/10/2026).

POR QUE
  Em 23/10/2026 os stories do @moviki.oficial chegaram a 0-3 visualizacoes
  com ~2 mil seguidores reais. A conta estava limpa (Status da conta todo
  verde); o problema era a posicao na barra de stories: so peca com cara de
  anuncio, nada para o seguidor responder, e o Instagram empurra a conta para
  o fim da barra.

  A API do Instagram NAO publica figurinha (enquete, pergunta, quiz). O que
  mais pesa na barra, depois da figurinha, e a RESPOSTA do story (ela vira
  conversa no direct). Por isso: 1 story por dia e uma pergunta curta que se
  responde com uma palavra, na caixa "Enviar mensagem".

  A resposta cai no direct do ManyChat: "LIVE" dispara o Funil LIVE; qualquer
  outra palavra vai para a resposta padrao (Vik), que conversa com a pessoa.

REGRAS DO BANCO
  - Pergunta para lojista, curta, sem afirmar a situacao de quem le, sem
    numero de resultado, sem promessa. Passa pelo compliance.garantir().
  - Resposta em UMA palavra (ou uma de duas/tres opcoes escritas na arte).
  - Gira o banco inteiro antes de repetir (estado recentes_perguntas_story).
"""
from PIL import Image, ImageDraw

from . import arte, compliance, config, estado

EST = "perguntas_story"

# id estavel -> (pergunta, como responder)
BANCO = [
    ("ramo", "Qual é o ramo da sua loja?",
     "Responda com uma palavra. A gente te manda uma live do seu ramo."),
    ("ja-vendeu-ao-vivo", "Você já vendeu ao vivo?",
     "Responda SIM ou AINDA NÃO."),
    ("whats-ou-live", "Vender pelo WhatsApp ou ao vivo?",
     "Responda WHATS ou LIVE."),
    ("o-que-trava", "O que mais trava a venda pelo celular?",
     "Responda PREÇO, FRETE ou DÚVIDA."),
    ("dia-forte", "Qual dia da semana a sua loja vende mais?",
     "Responda com o dia."),
    ("live-curta", "Live curta ou live longa?",
     "Responda CURTA ou LONGA."),
    ("pergunta-repetida", "O que o cliente mais pergunta?",
     "Responda PREÇO, TAMANHO ou ENTREGA."),
    ("um-produto", "Se pudesse mostrar só 1 produto ao vivo hoje, qual seria?",
     "Responda com o nome do produto."),
    ("tripe", "Você tem tripé para o celular?",
     "Responda SIM ou NÃO."),
    ("cidade", "Em que cidade fica a sua loja?",
     "Responda com a cidade."),
    ("carrinho", "O seu cliente já desistiu no carrinho?",
     "Responda SIM ou NÃO."),
    ("horario", "Que horário o seu cliente mais te chama?",
     "Responda MANHÃ, TARDE ou NOITE."),
    ("foto-ou-video", "Para mostrar produto: foto ou vídeo ao vivo?",
     "Responda FOTO ou VÍDEO."),
    ("pix", "O seu cliente prefere pagar como?",
     "Responda PIX, CARTÃO ou DINHEIRO."),
    ("sozinha", "Você toca a loja sozinha ou com equipe?",
     "Responda SOZINHA, SOZINHO ou EQUIPE."),
    ("timidez", "O que dá mais frio na barriga: aparecer na câmera ou falar ao vivo?",
     "Responda CÂMERA ou FALAR."),
]
RESERVA = ("ramo", "Qual é o ramo da sua loja?",
           "Responda com uma palavra. A gente te manda uma live do seu ramo.")


def da_vez(recentes=None):
    """A pergunta que esta ha mais tempo sem sair (inedita primeiro)."""
    recentes = estado.recentes(EST) if recentes is None else recentes

    def idade(item):
        return len(recentes) + 1 if item[0] not in recentes else recentes.index(item[0])

    pid, pergunta, resposta = max(BANCO, key=idade)
    pergunta = compliance.garantir(pergunta, RESERVA[1])
    resposta = compliance.garantir(resposta, RESERVA[2])
    return {"id": "pergunta:" + pid, "pid": pid, "titulo": pergunta, "resposta": resposta,
            "origem": "casa", "categoria": "geral", "tipo": "pergunta", "formato": "story"}


def marcar(pid):
    estado.marcar_usado(EST, pid, janela=max(len(BANCO) - 1, 1))


def _seta(d, cx, y, cor):
    """Seta para baixo apontando para a caixa 'Enviar mensagem'."""
    d.rectangle((cx - 9, y, cx + 9, y + 70), fill=cor)
    d.polygon([(cx - 42, y + 62), (cx + 42, y + 62), (cx, y + 118)], fill=cor)


def imagem(peca, semente=None):
    """Arte 1080x1920 no padrao Moviki. Tudo acima de y=1600: a faixa de baixo
    fica livre para a caixa de resposta do Instagram."""
    base = arte.fundo_padrao(arte.STORY, semente)
    l, _ = base.size
    arte._cabecalho(base, "Pergunta do dia")
    d = ImageDraw.Draw(base)
    margem = 80
    larg = l - margem * 2

    f_tit, linhas = arte._caber(d, peca["titulo"].upper(), config.FONTE_TITULO, larg, 132, 72, 5)
    alt_tit = len(linhas) * int(f_tit.size * 1.08)
    f_resp, l_resp = arte._caber(d, peca["resposta"], config.FONTE_FORTE, larg - 80, 44, 30, 3)
    alt_resp = len(l_resp) * (f_resp.size + 14) + 70

    y = 420 + max(0, (1500 - 420 - alt_tit - alt_resp - 60) // 2)
    for i, linha in enumerate(linhas):
        cor = arte.CIANO if (i == len(linhas) - 1 and len(linhas) > 1) else arte.BRANCO
        arte._centro(d, y, linha, f_tit, cor, l)
        y += int(f_tit.size * 1.08)

    y += 60
    d.rounded_rectangle((margem, y, l - margem, y + alt_resp), radius=36,
                        outline=arte.CIANO, width=4)
    yy = y + 35
    for linha in l_resp:
        arte._centro(d, yy, linha, f_resp, arte.BRANCO, l)
        yy += f_resp.size + 14

    f_aqui = arte._fonte(config.FONTE_FORTE, 40)
    arte._centro(d, 1440, "RESPONDA AQUI EMBAIXO", f_aqui, arte.VERDE, l)
    _seta(d, l // 2, 1500, arte.VERDE)
    return base


def salvar(peca, caminho, semente=None):
    img = imagem(peca, semente)
    if img.mode != "RGB":
        img = img.convert("RGB")
    return arte.salvar(img, caminho)


def _teste_visual(caminho="pergunta-teste.jpg"):  # pragma: no cover
    """Gera uma arte local para conferir o layout."""
    p = da_vez([])
    salvar(p, caminho, semente=1)
    return caminho


if __name__ == "__main__":  # pragma: no cover
    print(_teste_visual())
    Image.open("pergunta-teste.jpg")
