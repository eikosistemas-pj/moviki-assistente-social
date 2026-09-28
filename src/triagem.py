# -*- coding: utf-8 -*-
"""
Triagem "so parceiro" das pecas do Material de apoio (28/09/2026).

O PROBLEMA
  Algumas artes trazem IMPRESSO na imagem "cadastre-se pelo link deste
  parceiro", "fale comigo", "meu link". Na pagina oficial do Moviki isso manda
  o leitor para um parceiro que nao existe. O robo le a legenda, mas nao le o
  texto dentro da imagem — ate hoje a protecao era uma lista escrita a mao
  (config.MATERIAL_EXCLUIR_FIXO). Arte nova fora da lista ia ao ar.

AS TRES CAMADAS (qualquer uma barra a peca)
  1. Campo `so_parceiro: true` no catalogo — gravado por quem processa a arte
     (skill material-de-apoio). Vale para imagem E video.
  2. Lista fixa + secret MATERIAL_EXCLUIR (legado, continua valendo).
  3. ESTA triagem: a IA olha a imagem (arte do feed/story ou capa do video)
     UMA VEZ e guarda o veredito em estado/triagem_material.json. Arte trocada
     no mesmo id (arquivo diferente) e olhada de novo.

FALHA FECHADA
  Peca de imagem ainda nao olhada fica FORA ate ser olhada. O relatorio das
  redes (~08h e ~22h) olha as pendentes em lote; a publicacao olha no maximo
  POR_PUBLICACAO na hora. Se a IA falhar, a peca espera a proxima rodada —
  nunca vai ao ar sem veredito.
  Sem ANTHROPIC_API_KEY a triagem fica DESLIGADA: valem so as camadas 1 e 2
  (comportamento anterior) e o relatorio acende um alerta.

VIDEO
  A IA olha a CAPA. Frase de parceiro FALADA no video so a camada 1 ou 2
  pegam — por isso a skill marca `so_parceiro` ao processar video novo.
"""
import base64
import io
import json
import re
from datetime import datetime, timezone

from . import config, estado
from . import util_net as net

ARQUIVO = "triagem_material.json"
POR_PUBLICACAO = 8     # olhadas no maximo durante uma publicacao
POR_RELATORIO = 80     # olhadas no maximo por execucao do relatorio
LADO_MAX = 1024        # a imagem vai reduzida para a IA (custo e tempo)

PERGUNTA = """\
Esta arte vai ser publicada na pagina OFICIAL da marca Moviki (Instagram,
Facebook e TikTok da propria marca).

Leia TODO o texto impresso na imagem. Responda se ele direciona o leitor para
um PARCEIRO, revendedor, indicador ou pessoa especifica, e nao para a marca.
Exemplos que contam como parceiro: "link deste parceiro", "pelo link do
parceiro", "meu link", "fale comigo", "me chama", "use meu codigo", "cadastre-se
comigo", "acesse pelo link na minha bio", QR code identificado como "do
parceiro".
NAO contam: chamadas da propria marca ("cadastre-se gratis", "baixe o app",
"moviki.com.br", "link na bio", "30 dias gratis"), nome do app, telas do app.

Responda SO com JSON, sem mais nada:
{"parceiro": true ou false, "trecho": "o texto que decidiu, ou vazio"}"""


def ligada():
    return bool(config.ANTHROPIC_API_KEY)


def _cache():
    d = estado.ler_lista(ARQUIVO)
    return d if isinstance(d, dict) else {}


def _gravar(cache):
    estado.gravar_lista(ARQUIVO, cache)


def imagem_da_peca(peca):
    """URL que a IA olha: a arte (feed/story) ou a capa (reel). None = nada a olhar."""
    if peca.get("midia") == "imagem":
        return peca.get("url")
    return peca.get("capa_triagem") or peca.get("capa")


def _chave(peca):
    return f"{peca.get('id')}|{imagem_da_peca(peca) or ''}"


def veredito(peca, cache=None):
    """True = pode ir a pagina | False = so parceiro | None = ainda nao olhada."""
    cache = _cache() if cache is None else cache
    v = cache.get(peca.get("id"))
    if not v or v.get("imagem") != (imagem_da_peca(peca) or ""):
        return None
    return not v.get("parceiro")


# ------------------------------------------------------------------ IA
def _preparar(url):
    from PIL import Image
    r = net.get(url)
    if r.status_code != 200:
        raise RuntimeError(f"imagem HTTP {r.status_code}")
    img = Image.open(io.BytesIO(r.content))
    img = img.convert("RGB")
    img.thumbnail((LADO_MAX, LADO_MAX))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=85)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def _ler_json(texto):
    m = re.search(r"\{.*\}", texto or "", re.S)
    if not m:
        raise RuntimeError("resposta sem JSON")
    d = json.loads(m.group(0))
    if not isinstance(d.get("parceiro"), bool):
        raise RuntimeError("resposta sem o campo parceiro")
    return d


def perguntar_ia(url):
    """{'parceiro': bool, 'trecho': str}. Levanta erro se nao der pra decidir."""
    b64 = _preparar(url)
    r = net.post(
        "https://api.anthropic.com/v1/messages",
        headers={"x-api-key": config.ANTHROPIC_API_KEY,
                 "anthropic-version": "2023-06-01",
                 "content-type": "application/json"},
        json={"model": config.ANTHROPIC_MODEL_VISAO, "max_tokens": 200,
              "messages": [{"role": "user", "content": [
                  {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": b64}},
                  {"type": "text", "text": PERGUNTA}]}]},
    )
    dados = r.json()
    if "error" in dados:
        raise RuntimeError(str(dados["error"].get("message", "erro IA"))[:160])
    texto = "".join(b.get("text", "") for b in dados.get("content", []) if b.get("type") == "text")
    return _ler_json(texto)


# ------------------------------------------------------------------ filtro
def olhar(pecas, limite, perguntar=None, agora=None):
    """Olha as pecas sem veredito (ate `limite`). Devolve (olhadas, falhas)."""
    if not ligada() and perguntar is None:
        return 0, 0
    perguntar = perguntar or perguntar_ia
    cache = _cache()
    olhadas = falhas = 0
    vistos = set()
    for p in pecas:
        if olhadas + falhas >= limite:
            break
        url = imagem_da_peca(p)
        if not url or p["id"] in vistos or veredito(p, cache) is not None:
            continue
        vistos.add(p["id"])
        try:
            d = perguntar(url)
        except Exception as e:  # noqa: BLE001
            falhas += 1
            print(f"AVISO: triagem de {p['id']} falhou ({net.sem_segredo(e)}) -> fica de fora ate a proxima")
            continue
        cache[p["id"]] = {"imagem": url, "parceiro": bool(d["parceiro"]),
                          "trecho": str(d.get("trecho") or "")[:160],
                          "em": (agora or datetime.now(timezone.utc)).isoformat(timespec="seconds")}
        olhadas += 1
        if d["parceiro"]:
            print(f"triagem: {p['id']} BARRADA (so parceiro): {cache[p['id']]['trecho']}")
    if olhadas:
        _gravar(cache)
    return olhadas, falhas


def filtrar(pecas, limite=POR_PUBLICACAO, perguntar=None):
    """Tira as pecas 'so parceiro' e as que ainda nao tem veredito.

    Triagem desligada (sem chave da IA): devolve a lista como veio."""
    if not ligada() and perguntar is None:
        return list(pecas)
    olhar(pecas, limite, perguntar)
    cache = _cache()
    saida = []
    for p in pecas:
        if not imagem_da_peca(p):
            saida.append(p)          # video sem capa: camadas 1 e 2
            continue
        v = veredito(p, cache)
        if v:
            saida.append(p)
    return saida


def resumo(pecas):
    """Para o relatorio: quantas liberadas, barradas e pendentes."""
    cache = _cache()
    lib = bar = pend = 0
    barradas = []
    for p in pecas:
        if not imagem_da_peca(p):
            continue
        v = veredito(p, cache)
        if v is None:
            pend += 1
        elif v:
            lib += 1
        else:
            bar += 1
            barradas.append({"id": p["id"], "trecho": (cache.get(p["id"]) or {}).get("trecho", "")})
    return {"ligada": ligada(), "liberadas": lib, "barradas": bar, "pendentes": pend,
            "lista_barradas": barradas[:30]}
