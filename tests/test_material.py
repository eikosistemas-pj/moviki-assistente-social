# -*- coding: utf-8 -*-
"""
Testes do Material de apoio como fonte das redes (22/09/2026), sem rede.

O catalogo de teste imita o formato real de moviki-app/material/catalogo.json.
"""
from src import compliance, config, firestore, material, segmentos


def _peca(**kw):
    base = {
        "id": "feed-pizzaria-ao-vivo", "tipo": "feed", "categoria": "alimentacao",
        "titulo": "Pizzaria ao vivo no mapa", "w": "1080", "h": "1080",
        "arquivo": "material/feed/feed-pizzaria-ao-vivo.jpg",
        "legenda": ("#publi A fome entra pelos olhos.\n\n30 dias grátis. Sem cartão, "
                    "sem fidelidade — você só continua se fizer sentido.\n"
                    "Comece pelo meu link: {link}"),
    }
    base.update(kw)
    return base


def _story(**kw):
    base = {"id": "story-pizzaria", "tipo": "story", "categoria": "alimentacao",
            "titulo": "Pizzaria", "w": "1080", "h": "1920",
            "arquivo": "material/stories/story-pizzaria.jpg"}
    base.update(kw)
    return base


def _video(**kw):
    base = {"id": "video-x", "tipo": "video", "categoria": "geral", "titulo": "Vídeo",
            "w": "1080", "h": "1920", "duracao": "1:07",
            "arquivo": "material/video-x.mp4",
            "legenda": "#publi Ninguém compra de quem não acha.\n\nComece pelo meu link: {link}"}
    base.update(kw)
    return base


def _cat(*pecas):
    return {"versao": "t", "itens": list(pecas)}


# ------------------------------------------------------------- legenda
def test_legenda_perde_publi_e_voz_de_parceiro_no_instagram():
    t = material.legenda_oficial(_peca()["legenda"], "instagram")
    assert not t.startswith("#publi")
    assert "meu link" not in t and "{link}" not in t
    assert t.endswith("Comece pelo link da bio.")


def test_legenda_do_facebook_leva_o_endereco_e_nao_a_bio():
    t = material.legenda_oficial(_peca()["legenda"], "facebook")
    assert "bio" not in t
    assert t.endswith("Comece em moviki.com.br")


def test_comece_gratis_tambem_converte():
    leg = "#publi Tudo num link só.\n\nComece grátis pelo meu link: {link}"
    assert material.legenda_oficial(leg, "instagram").endswith("Comece grátis pelo link da bio.")


def test_sobra_de_parceiro_descarta_a_peca():
    leg = "#publi Fale comigo, sou parceiro. Meu link é {link_parceiro}"
    assert material.legenda_oficial(leg) is None


# ------------------------------------------------------------- formatos
def test_cada_tipo_vai_para_o_seu_formato():
    cat = _cat(_peca(), _story(), _video(), _peca(id="t1", tipo="texto"))
    assert [p["id"] for p in material.pecas(cat, "feed", excluir=set())] == ["feed-pizzaria-ao-vivo"]
    assert [p["id"] for p in material.pecas(cat, "story", excluir=set())] == ["story-pizzaria"]
    assert [p["id"] for p in material.pecas(cat, "reel", excluir=set())] == ["video-x"]


def test_story_nao_tem_legenda_e_url_e_absoluta():
    p = material.pecas(_cat(_story()), "story", excluir=set())[0]
    assert p["legenda_ig"] is None and p["midia"] == "imagem"
    assert p["url"] == f"{config.MATERIAL_BASE}/material/stories/story-pizzaria.jpg"


def test_video_longo_ou_fora_do_9x16_nao_vira_reel():
    assert material.pecas(_cat(_video(duracao="3:12")), "reel", excluir=set()) == []
    assert material.pecas(_cat(_video(h="1350")), "reel", excluir=set()) == []
    assert material.pecas(_cat(_video(duracao="")), "reel", excluir=set()) == []


def test_reel_do_material_tem_legenda_convertida():
    p = material.pecas(_cat(_video()), "reel", excluir=set())[0]
    assert p["legenda_ig"].endswith("pelo link da bio.")
    assert p["legenda_fb"].endswith("em moviki.com.br")


def test_arte_com_link_de_parceiro_impresso_fica_de_fora():
    cat = _cat(_peca(id="feed-na-hora-foodtruck", categoria="geral"),
               _story(id="story-na-hora"), _video(id="video-cada-negocio"))
    for f in ("feed", "story", "reel"):
        assert material.pecas(cat, f) == []


def test_recrutar_fica_de_fora():
    assert material.pecas(_cat(_peca(categoria="recrutar")), "feed", excluir=set()) == []


def test_proporcao_fora_do_feed_fica_de_fora():
    assert material.pecas(_cat(_peca(w="1080", h="1920")), "feed", excluir=set()) == []


def test_legendas_convertidas_passam_na_trava():
    for canal in ("instagram", "facebook"):
        t = material.legenda_oficial(_peca()["legenda"], canal)
        assert compliance.violacoes(t) == []
        assert compliance.violacoes(material.reserva("Título", canal)) == []


def test_duracao_em_texto():
    assert material._segundos("1:07") == 67
    assert material._segundos("27") == 27
    assert material._segundos("x") is None


# ------------------------------------------------------------- vitrine
def test_slug_de_email_nao_vai_ao_ar():
    assert not firestore.slug_publicavel("fabiofffggggmailcom")
    assert not firestore.slug_publicavel("joaohotmailcom")
    assert firestore.slug_publicavel("futebol")
    assert firestore.slug_publicavel("burgerdoze")


def test_conta_demo_e_teste_nao_vao_ao_ar():
    assert not firestore.slug_publicavel("hamburguermaster")
    assert not firestore.slug_publicavel("karina")


def test_vitrine_nasce_desligada():
    assert config.VITRINE_POR_SEMANA == 0


def test_rotulos_tem_acento():
    assert segmentos.rotulo("alimentacao") == "Alimentação"
    assert segmentos.rotulo("calcados") == "Calçados"


def test_ninguem_afirma_que_o_negocio_esta_aberto():
    for c in list(segmentos.CHAMADAS.values()) + [segmentos.PADRAO]:
        assert "ABERTO" not in c


def test_uf_certa_para_parana_e_paraiba():
    import run_feed
    assert run_feed.uf_de({"ISO3166-2-lvl4": "BR-PR", "state": "Paraná"}) == "PR"
    assert run_feed.uf_de({"state": "Paraíba"}) == "PB"
    assert run_feed.uf_de({"state": "Pará"}) == "PA"
    assert run_feed.uf_de({"state": "Estado inventado"}) == ""
