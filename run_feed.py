# -*- coding: utf-8 -*-
"""
Ciclo do FEED.

Decide entre dois tipos de post e publica UM:

  VITRINE      - divulga um negocio real cadastrado no Moviki que autorizou
                 divulgacao. E o post que gera prova social verdadeira,
                 retencao (o lojista e divulgado de graca) e alcance
                 organico (ele compartilha o post do proprio negocio).
  INSTITUCIONAL- explica o produto pra quem nunca ouviu falar.

Regra de mistura: enquanto a base de comerciantes autorizados for pequena
(< MIN_NEGOCIOS_VITRINE), TUDO e institucional — senao o mesmo lojista
apareceria toda semana e o perfil viraria panfleto de uma pessoa so.

Uso:
    python run_feed.py                 # decide sozinho
    python run_feed.py vitrine         # forca vitrine
    python run_feed.py institucional   # forca institucional
    DRY_RUN=1 python run_feed.py       # monta tudo e NAO publica
"""
import re
import sys
from datetime import datetime, timezone

from src import arte, config, conteudo, estado, firestore, ia, segmentos
from src import util_net as net
from src.social.facebook import Facebook, espelhar
from src.social.instagram import Instagram
from src import hospedagem


# ------------------------------------------------------------------ auxiliares
def _baixar(url):
    """Baixa a logo/foto do lojista. Falha nao derruba o post."""
    if not url:
        return None
    try:
        r = net.get(url, timeout=25)
        if r.status_code == 200 and len(r.content) > 500:
            return r.content
    except Exception as e:  # noqa: BLE001
        print(f"aviso: nao baixei a imagem do lojista ({e})")
    return None


def _cidade(negocio):
    """Cidade a partir de lat/lng, por geocodificacao reversa publica.

    Best-effort: sem cidade o post continua valido. NUNCA imprimimos o
    endereco exato — so municipio/UF. Endereco preciso de terceiro em post
    publico e exposicao desnecessaria.
    """
    lat, lng = negocio.get("lat"), negocio.get("lng")
    if lat is None or lng is None:
        return ""
    try:
        r = net.get(
            "https://nominatim.openstreetmap.org/reverse",
            params={"lat": lat, "lon": lng, "format": "json", "zoom": 10,
                    "accept-language": "pt-BR"},
            headers={"User-Agent": "moviki-assistente-social/1.0 (contato@moviki.com.br)"},
            timeout=20,
        )
        a = (r.json() or {}).get("address", {}) or {}
        cidade = a.get("city") or a.get("town") or a.get("village") or a.get("municipality") or ""
        uf = a.get("state_code") or ""
        if not uf:
            estado_nome = a.get("state") or ""
            uf = estado_nome[:2].upper() if estado_nome else ""
        return " - ".join(x for x in [cidade, uf.upper()] if x)
    except Exception:  # noqa: BLE001
        return ""


# ------------------------------------------------------------------ vitrine
def montar_vitrine():
    negocios = firestore.elegiveis(firestore.listar_negocios())
    print(f"negocios que autorizaram divulgacao: {len(negocios)}")
    if len(negocios) < config.MIN_NEGOCIOS_VITRINE:
        print(f"abaixo do minimo ({config.MIN_NEGOCIOS_VITRINE}) -> institucional")
        return None

    escolhido = estado.escolher("vitrine", negocios, chave=lambda n: n.get("uid", ""))
    if not escolhido:
        return None

    seg = escolhido.get("segmento") or ""
    escolhido["segmento"] = segmentos.macro_de(seg) or seg
    escolhido["segmento_rotulo"] = segmentos.rotulo(seg)
    cidade = _cidade(escolhido)
    nome = escolhido.get("nome", "")
    rotulo = escolhido["segmento_rotulo"] or "negocio itinerante"

    imagem = arte.card_vitrine(
        escolhido,
        logo_bytes=_baixar(escolhido.get("markerLogo")
                           or (escolhido.get("fotos") or [None])[0]),
        cidade=cidade,
        chamada=segmentos.chamada(seg),
        semente=escolhido.get("uid"),
    )

    # Texto reserva: vai AO AR se a IA falhar. Escrever com acentuacao
    # correta — e conteudo publico, nao log interno.
    reserva = (
        f"{nome} está no Moviki. \U0001f4cd\n\n"
        f"{rotulo}{(' em ' + cidade) if cidade else ''}. "
        f"Quer saber se tá aberto agora? É só abrir o link:\n"
        f"moviki.com.br/{escolhido.get('slug','')}\n\n"
        f"Se você trabalha na rua e quer o seu, o link tá na bio."
    )
    legenda = ia.escrever(
        f"Escreva a legenda de um post que divulga um negocio REAL cadastrado no "
        f"Moviki.\n\nNome: {nome}\nTipo: {rotulo}\n"
        f"Cidade: {cidade or 'nao informada'}\n"
        f"Link: moviki.com.br/{escolhido.get('slug','')}\n\n"
        f"Apresente o negocio de forma calorosa, diga que da pra ver pelo link se "
        f"ele esta aberto e onde esta agora, e feche convidando outros donos de "
        f"negocio itinerante a ter o proprio link. Nao invente nada sobre o "
        f"negocio alem do que esta acima. Nao prometa venda nem ganho.",
        reserva,
    )
    return {
        "tipo": "vitrine",
        "imagem": imagem,
        "legenda": legenda,
        "hashtags": conteudo.hashtags("vitrine"),
        "chave": escolhido.get("uid", ""),
        "descricao": f"{nome} ({rotulo})",
    }


# ------------------------------------------------------------------ institucional
def montar_institucional():
    pautas = conteudo.carregar()
    if not pautas:
        raise SystemExit("ERRO: conteudo/pautas.md vazio ou ausente.")

    # Ter/Qui puxam conversao; sexta puxa parceiro; resto e educativo/bastidor.
    dia = datetime.now(timezone.utc).weekday()
    if dia in (1, 3):
        preferidas = conteudo.por_tipo(pautas, "conversao")
    elif dia == 4:
        preferidas = conteudo.por_tipo(pautas, "parceiro")
    else:
        preferidas = (conteudo.por_tipo(pautas, "educativo")
                      + conteudo.por_tipo(pautas, "bastidor"))
    candidatas = preferidas or pautas

    pauta = estado.escolher("institucional", candidatas, chave=lambda p: p["id"])
    print(f"pauta: {pauta['id']} ({pauta['tipo']})")

    imagem = arte.card_institucional(
        pauta["titulo"], pauta.get("subtitulo", ""), pauta.get("etiqueta", ""),
        semente=pauta["id"],
    )

    reserva = (
        f"{pauta['titulo']}\n\n{pauta.get('subtitulo','')}\n\n"
        f"Conheça em moviki.com.br — link na bio."
    )
    legenda = ia.escrever(
        f"Escreva a legenda de um post do Moviki.\n\n"
        f"Titulo do post: {pauta['titulo']}\n"
        f"Complemento: {pauta.get('subtitulo','')}\n"
        f"Angulo: {pauta.get('angulo','')}\n\n"
        f"Feche com chamada pra acao mandando pro link da bio.",
        reserva,
    )
    return {
        "tipo": "institucional",
        "imagem": imagem,
        "legenda": legenda,
        "hashtags": conteudo.hashtags(pauta["tipo"]),
        "chave": pauta["id"],
        "descricao": pauta["id"],
    }


# ------------------------------------------------------------------ Facebook
def _texto_facebook(legenda):
    """Adapta a legenda quando o post vai pro Facebook em vez do Instagram.

    "Link na bio" e' gramatica de Instagram: na Pagina do Facebook nao existe
    bio com link, entao a frase manda o leitor pra lugar nenhum.

    Dois casos, tratados em ordem:
      1) "... moviki.com.br — link na bio."  -> corta o rabicho (o endereco
         ja esta na frase, e no Facebook ele vira link clicavel sozinho).
      2) "o link ta na bio."                 -> troca pelo endereco, senao a
         frase ficaria truncada e sem chamada pra acao.
    """
    t = re.sub(r"\s*[—–-]\s*(o\s+)?link\s+(t[aá]\s+)?na\s+bio\.?", ".", legenda, flags=re.IGNORECASE)
    t = re.sub(r"link\s+(t[aá]\s+)?na\s+bio", "link está em moviki.com.br", t, flags=re.IGNORECASE)
    return re.sub(r"\.\s*\.", ".", t).strip()


# ------------------------------------------------------------------ principal
def main():
    forcado = (sys.argv[1] if len(sys.argv) > 1 else "").strip().lower()

    post = None
    if forcado == "institucional":
        post = montar_institucional()
    else:
        try:
            post = montar_vitrine()
        except Exception as e:  # noqa: BLE001
            print(f"aviso: vitrine falhou ({e}) -> institucional")
        if post is None:
            if forcado == "vitrine":
                raise SystemExit("ERRO: vitrine forcada mas nao ha negocio elegivel.")
            post = montar_institucional()

    caminho = arte.salvar(post["imagem"], f"/tmp/feed-{post['tipo']}.jpg")
    print(f"arte montada: {caminho}")

    # Legenda JA adaptada ao canal antes de imprimir. O dry-run existe pra
    # revisar o que vai ao ar — se ele mostrasse o texto cru e a adaptacao
    # acontecesse so na hora de publicar, a revisao nao valeria nada.
    legenda = _texto_facebook(post["legenda"]) if config.SO_FACEBOOK else post["legenda"]
    print("--- legenda ---")
    print(legenda)
    print("---------------")

    if config.DRY_RUN:
        print("DRY_RUN ligado -> nada foi publicado.")
        return

    url = hospedagem.publicar_arquivo(caminho, prefixo=f"feed-{post['tipo']}")
    print(f"arte publica: {url}")

    # ------------------------------------------------------------------
    # Onde publicar.
    #
    # Modo normal: Instagram e o principal, Facebook e o espelho.
    # Modo SO_FACEBOOK: o Instagram esta bloqueado pela Meta, entao a Pagina
    #   do Facebook vira o canal principal — e ai uma falha dela DERRUBA o
    #   ciclo de proposito, porque nao ha outro lugar pra publicar.
    #
    # Plano B automatico: se o Instagram falhar no modo normal (token
    # revogado, restricao nova), o robo NAO perde o post — publica no
    # Facebook e avisa. Melhor um canal no ar que nenhum.
    # ------------------------------------------------------------------
    if config.SO_FACEBOOK:
        print("SO_FACEBOOK ligado -> publicando direto na Pagina do Facebook.")
        fb_id = Facebook().foto(url, legenda)
        print(f"OK -> Facebook | {post['tipo']} | {post['descricao']} | id: {fb_id}")
        estado.marcar_usado(post["tipo"], post["chave"])
        estado.registrar("feed", post["descricao"], fb_id,
                         {"subtipo": post["tipo"], "rede": "facebook"})
        return

    try:
        media_id = Instagram().foto(url, legenda, post["hashtags"])
    except Exception as e:  # noqa: BLE001
        print(f"AVISO: Instagram falhou ({e}) -> tentando publicar no Facebook.")
        fb_id = Facebook().foto(url, _texto_facebook(post["legenda"]))
        print(f"OK -> Facebook (plano B) | {post['descricao']} | id: {fb_id}")
        estado.marcar_usado(post["tipo"], post["chave"])
        estado.registrar("feed", post["descricao"], fb_id,
                         {"subtipo": post["tipo"], "rede": "facebook", "planoB": True})
        return

    print(f"OK -> Instagram | {post['tipo']} | {post['descricao']} | id: {media_id}")

    estado.marcar_usado(post["tipo"], post["chave"])
    estado.registrar("feed", post["descricao"], media_id, {"subtipo": post["tipo"]})

    espelhar(url, post["legenda"])


if __name__ == "__main__":
    main()
