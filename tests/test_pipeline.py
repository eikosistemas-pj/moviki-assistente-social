# -*- coding: utf-8 -*-
"""
Testes do pipeline sem rede: elegibilidade, pautas, rotacao e publicacao
com Graph API falsa.
"""
import pytest

from src import conteudo, firestore, segmentos
from src.social.instagram import Instagram


# ------------------------------------------------------------- elegibilidade
def _negocio(**kw):
    base = {"uid": "u1", "nome": "Burger do Ze", "slug": "burgerdoze",
            "autorizaDivulgacao": True, "markerLogo": "https://x/y.png"}
    base.update(kw)
    return base


def test_sem_optin_fica_de_fora():
    """Divulgar negocio de terceiro sem aceite e problema de LGPD."""
    assert firestore.elegiveis([_negocio(autorizaDivulgacao=False)]) == []
    assert firestore.elegiveis([_negocio(autorizaDivulgacao=None)]) == []
    sem_campo = _negocio()
    del sem_campo["autorizaDivulgacao"]
    assert firestore.elegiveis([sem_campo]) == []


def test_optin_precisa_ser_booleano_verdadeiro():
    """String 'true' nao vale — evita aceite gravado errado virar permissao."""
    assert firestore.elegiveis([_negocio(autorizaDivulgacao="true")]) == []


def test_sem_slug_fica_de_fora():
    assert firestore.elegiveis([_negocio(slug="")]) == []


def test_sem_visual_nem_segmento_fica_de_fora():
    assert firestore.elegiveis([_negocio(markerLogo="", fotos=[])]) == []


def test_negocio_completo_entra():
    assert len(firestore.elegiveis([_negocio()])) == 1


def test_segmento_sozinho_ja_basta():
    assert len(firestore.elegiveis([_negocio(markerLogo="", segmento="foodtruck")])) == 1


# ------------------------------------------------------------- segmentos
def test_subtipo_resolve_macro_e_rotulo():
    assert segmentos.macro_de("foodtruck") == "alimentacao"
    assert segmentos.rotulo("foodtruck") == "Hamburgueria / Food Truck"


def test_macro_resolve_ele_mesmo():
    assert segmentos.macro_de("servicos") == "servicos"


def test_segmento_desconhecido_degrada_sem_quebrar():
    assert segmentos.macro_de("inexistente") == ""
    assert segmentos.rotulo("inexistente") == ""
    assert segmentos.chamada("inexistente") == "ESTA NO MOVIKI"


# ------------------------------------------------------------- pautas
def test_pautas_carregam_e_tem_campos():
    pautas = conteudo.carregar()
    assert len(pautas) >= 8
    for p in pautas:
        assert p["id"] and p["titulo"]
        assert p["tipo"] in ("educativo", "conversao", "parceiro", "bastidor")


def test_todas_as_pautas_passam_na_trava():
    """Pauta escrita a mao tambem tem que passar — senao o post quebra
    exatamente no dia em que ela for sorteada.

    So valida titulo e subtitulo: sao os campos IMPRESSOS na arte e que
    viram texto publico. 'angulo' e instrucao pra IA e precisa poder
    nomear o termo proibido pra proibi-lo ("nao fale em renda extra") —
    validar ele bloquearia a propria regra de seguranca. O que a IA
    devolve a partir do angulo passa por compliance.garantir() normalmente.
    """
    from src import compliance
    for p in conteudo.carregar():
        for campo in ("titulo", "subtitulo"):
            texto = p.get(campo, "")
            assert compliance.violacoes(texto) == [], f"{p['id']}.{campo}: {texto}"


def test_existe_pauta_de_cada_tipo():
    pautas = conteudo.carregar()
    for tipo in ("educativo", "conversao", "parceiro"):
        assert conteudo.por_tipo(pautas, tipo), f"falta pauta do tipo {tipo}"


# ------------------------------------------------------------- instagram falso
class GraphFalso:
    def __init__(self, falhar_em=None):
        self.chamadas = []
        self.falhar_em = falhar_em

    def post(self, caminho, params):
        self.chamadas.append((caminho, params))
        if self.falhar_em and self.falhar_em in caminho:
            return {"error": {"message": "falha simulada"}}
        if caminho.endswith("/media"):
            return {"id": "container-1"}
        if caminho.endswith("/media_publish"):
            return {"id": "media-99"}
        return {"id": "comentario-1"}

    def get(self, caminho, params):
        return {"status_code": "FINISHED"}


def _ig(falso):
    return Instagram(account_id="123", token="t", post_fn=falso.post,
                     get_fn=falso.get, sleep_fn=lambda s: None)


def test_foto_cria_container_espera_e_publica():
    falso = GraphFalso()
    assert _ig(falso).foto("https://img", "legenda", "#tag") == "media-99"
    caminhos = [c for c, _ in falso.chamadas]
    assert caminhos == ["123/media", "123/media_publish", "media-99/comments"]


def test_hashtags_vao_no_comentario_nao_na_legenda():
    falso = GraphFalso()
    _ig(falso).foto("https://img", "legenda limpa", "#moviki")
    _, params_container = falso.chamadas[0]
    assert "#moviki" not in params_container["caption"]
    _, params_comentario = falso.chamadas[2]
    assert params_comentario["message"] == "#moviki"


def test_falha_ao_publicar_estoura():
    falso = GraphFalso(falhar_em="media_publish")
    with pytest.raises(RuntimeError, match="publicar"):
        _ig(falso).foto("https://img", "legenda")


def test_comentario_que_falha_nao_derruba_post_ja_publicado():
    class ComentarioRuim(GraphFalso):
        def post(self, caminho, params):
            if caminho.endswith("/comments"):
                raise RuntimeError("rede caiu")
            return super().post(caminho, params)

    assert _ig(ComentarioRuim()).foto("https://img", "legenda", "#tag") == "media-99"


def test_reel_usa_media_type_reels():
    falso = GraphFalso()
    _ig(falso).reel("https://video.mp4", "legenda")
    _, params = falso.chamadas[0]
    assert params["media_type"] == "REELS"
    assert params["video_url"] == "https://video.mp4"


def test_container_com_erro_estoura_antes_de_publicar():
    falso = GraphFalso(falhar_em="/media")
    with pytest.raises(RuntimeError, match="container"):
        _ig(falso).foto("https://img", "legenda")


# ------------------------------------------------------------- comentarios
def test_reels_carregados_tem_url_real():
    """Todo reel ativo precisa de URL utilizavel. Regressao dupla:
    (a) bloco dentro de <!-- --> nao pode virar post;
    (b) URL de exemplo com <owner> nao pode passar."""
    from run_reel import carregar_reels
    for r in carregar_reels():
        assert r["url"].startswith("https://"), r["id"]
        assert "<owner>" not in r["url"], r["id"]
        assert "<repo>" not in r["url"], r["id"]
        assert r["url"].endswith(".mp4"), r["id"]


def test_titulos_de_reel_passam_na_trava():
    """titulo do reel VAI AO AR (vira a 1a linha da legenda reserva)."""
    from src import compliance
    from run_reel import carregar_reels
    for r in carregar_reels():
        assert compliance.violacoes(r["titulo"]) == [], f"{r['id']}: {r['titulo']}"


def test_sem_comentarios_remove_bloco_html():
    texto = "ativo\n<!--\n## fantasma\nurl: https://x/y.mp4\n-->\nfim"
    limpo = conteudo.sem_comentarios(texto)
    assert "fantasma" not in limpo
    assert "ativo" in limpo and "fim" in limpo
