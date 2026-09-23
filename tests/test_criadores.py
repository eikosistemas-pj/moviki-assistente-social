# -*- coding: utf-8 -*-
"""
Testes da brecha dos criadores (22/09/2026), sem rede.

A regra que estes testes protegem: NENHUMA peca de influenciador vai ao ar
sem as duas chaves — autorizacao do criador (valida e nao revogada) e
aprovacao do Moviki.
"""
from datetime import datetime, timezone

from src import compliance, config, criadores, pecas

AGORA = datetime(2026, 10, 1, tzinfo=timezone.utc)


def _item(**kw):
    base = {
        "id": "abc123", "formato": "reel", "midia": "video",
        "url": "https://firebasestorage.googleapis.com/v0/b/x/o/v.mp4?alt=media",
        "w": 1080, "h": 1920, "duracao": 32, "categoria": "alimentacao",
        "titulo": "Hambúrguer ao vivo na praça",
        "legenda": "#publi Olha o corte desse hambúrguer! Comece pelo meu link: {link}",
        "criador": {"uid": "u1", "nome": "Ana Souza", "arroba": "@ana.souza"},
        "autorizacao": {"autorizado": True, "versao_termo": "3.1",
                        "em": "2026-09-25T12:00:00Z", "expira_em": "2027-09-25T12:00:00Z"},
        "aprovacao": {"aprovada": True, "em": "2026-09-26T12:00:00Z"},
    }
    for k, v in kw.items():
        base[k] = v
    return base


def test_fonte_nasce_desligada():
    assert config.CRIADORES_URL == ""
    assert criadores.ativa() is False
    assert criadores.carregar() == []


def test_peca_completa_passa():
    assert criadores.valida(_item(), AGORA) == ""


def test_sem_autorizacao_do_criador_fica_fora():
    it = _item(autorizacao={"autorizado": False, "versao_termo": "3.1", "em": "2026-09-25T12:00:00Z",
                            "expira_em": "2027-09-25T12:00:00Z"})
    assert criadores.valida(it, AGORA)


def test_autorizacao_como_texto_nao_vale():
    aut = dict(_item()["autorizacao"], autorizado="true")
    assert criadores.valida(_item(autorizacao=aut), AGORA)


def test_sem_aprovacao_do_moviki_fica_fora():
    """O botao do criador sozinho nunca publica nada."""
    assert criadores.valida(_item(aprovacao={"aprovada": False}), AGORA)
    assert criadores.valida(_item(aprovacao=None), AGORA)


def test_revogada_fica_fora():
    aut = dict(_item()["autorizacao"], revogada_em="2026-09-30T00:00:00Z")
    assert criadores.valida(_item(autorizacao=aut), AGORA) == "autorizacao revogada"


def test_vencida_ou_sem_validade_fica_fora():
    aut = dict(_item()["autorizacao"], expira_em="2026-09-30T00:00:00Z")
    assert criadores.valida(_item(autorizacao=aut), AGORA)
    aut2 = {k: v for k, v in _item()["autorizacao"].items() if k != "expira_em"}
    assert criadores.valida(_item(autorizacao=aut2), AGORA)


def test_video_longo_nao_vira_reel():
    assert criadores.valida(_item(duracao=120), AGORA)


def test_feed_de_criador_so_imagem():
    assert criadores.valida(_item(formato="feed"), AGORA)


def test_url_sem_https_fica_fora():
    assert criadores.valida(_item(url="http://x/v.mp4"), AGORA)


def test_legenda_leva_credito_e_perde_publi():
    p = criadores.pecas([_item()], "reel", AGORA)[0]
    assert p["id"] == "c:abc123" and p["origem"] == "criador"
    assert p["legenda_ig"].endswith("Conteúdo de @ana.souza")
    assert "#publi" not in p["legenda_ig"] and "meu link" not in p["legenda_ig"]
    assert "pelo link da bio" in p["legenda_ig"]
    assert "em moviki.com.br" in p["legenda_fb"]


def test_legenda_suja_do_criador_cai_na_reserva_com_credito():
    it = _item(legenda="Com o Moviki você vai vender mais! Renda extra garantida")
    p = criadores.pecas([it], "reel", AGORA)[0]
    assert compliance.violacoes(p["legenda_ig"]) == []
    assert p["legenda_ig"].startswith("Hambúrguer ao vivo na praça.")
    assert p["legenda_ig"].endswith("@ana.souza")


def test_titulo_sujo_do_criador_nao_derruba_o_robo():
    it = _item(titulo="Renda extra garantida", legenda="Ganhe R$ 500 por dia")
    p = criadores.pecas([it], "reel", AGORA)[0]
    assert compliance.violacoes(p["legenda_ig"]) == []


def test_arroba_invalido_usa_o_nome():
    it = _item(criador={"uid": "u1", "nome": "Ana Souza", "arroba": "ana souza!!"})
    assert criadores.credito(it).endswith("Conteúdo de Ana Souza")


# ------------------------------------------------------------- mistura
def _p(i, origem, uid=None, cat="geral"):
    return {"id": i, "origem": origem, "categoria": cat,
            "criador": {"uid": uid} if uid else None}


def test_sem_criador_e_tudo_da_casa():
    assert pecas.escolher_origem("reel", {"casa": [_p("a", "material")], "criador": []}, []) == "casa"


def test_metade_para_criador_quando_ha_peca():
    g = {"casa": [_p("a", "material")], "criador": [_p("c:1", "criador", "u1")]}
    assert pecas.escolher_origem("reel", g, ["casa", "casa"]) == "criador"
    assert pecas.escolher_origem("reel", g, ["criador", "casa", "criador", "casa"]) == "casa"


def test_nao_repete_criador_em_seguida():
    lista = [_p("c:1", "criador", "u1"), _p("c:2", "criador", "u1"), _p("c:3", "criador", "u2")]
    assert pecas.escolher(lista, ["c:1"])["id"] == "c:3"


def test_inedita_antes_da_usada_e_depois_a_mais_antiga():
    a, b, c = _p("a", "material", cat="x"), _p("b", "material", cat="y"), _p("c", "material", cat="z")
    assert pecas.escolher([a, b], ["a"])["id"] == "b"
    assert pecas.escolher([a, b, c], ["c", "a", "b"])["id"] == "b"


def test_evita_mesmo_ramo_em_seguida():
    a, b, c = _p("a", "material", cat="pet"), _p("b", "material", cat="pet"), _p("c", "material", cat="moda")
    assert pecas.escolher([b, c, a], ["a"])["id"] == "c"
