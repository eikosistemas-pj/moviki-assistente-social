# -*- coding: utf-8 -*-
"""Pergunta do dia, trava de tema e de estreia (23/10/2026)."""
from datetime import date, datetime, timedelta, timezone

from src import compliance, config, story, story_pergunta as sp, tema

HOJE = date(2026, 10, 23)


def _h(formato="story", peca="p", tipo="arte", horas=0, descricao="", tema_=None):
    """Linha de historico de HOJE (meio-dia BRT menos `horas`)."""
    q = datetime(2026, 10, 23, 15, 0, tzinfo=timezone.utc) - timedelta(hours=horas)
    linha = {"formato": formato, "peca": peca, "tipo": tipo, "descricao": descricao,
             "quando": q.isoformat(timespec="seconds")}
    if tema_:
        linha["tema"] = tema_
    return linha


# ------------------------------------------------------------------ tema
def test_tema_reconhece_black_friday_por_id_e_titulo():
    assert tema.tema({"id": "video:bf-ao-vivo"}) == "black-friday"
    assert tema.tema({"peca": "grade:ugc-bastidores-bf-perfumaria-c"}) == "black-friday"
    assert tema.tema({"descricao": "Black Friday ao vivo: Pix"}) == "black-friday"
    assert tema.tema({"id": "story-suco-ao-vivo", "titulo": "Seu suco ao vivo"}) is None


def test_um_story_de_bf_por_dia():
    hist = [_h(peca="story-suco"), _h(peca="video:bf-sem-checkout", tipo="video", horas=2)]
    lista = [{"id": "video:bf-uma-resposta"}, {"id": "video:video-comercio-brecho"}]
    assert tema.filtrar(lista, "story", hist, HOJE) == [{"id": "video:video-comercio-brecho"}]


def test_nunca_dois_do_mesmo_tema_em_seguida_nem_de_um_dia_para_outro():
    ontem = _h(peca="video:bf-ao-vivo", tipo="video", horas=20)
    lista = [{"id": "bf-pix"}, {"id": "story-moto"}]
    assert tema.filtrar(lista, "story", [ontem], HOJE) == [{"id": "story-moto"}]


def test_teto_do_perfil_inteiro():
    hist = [_h("feed", "bf-sem-checkout-feed"), _h("reel", "grade:ugc-bastidores-bf-perfumaria-c", horas=1),
            _h("story", "story-suco", horas=2)]
    lista = [{"id": "bf-pix"}, {"id": "story-moto"}]
    assert tema.filtrar(lista, "story", hist, HOJE) == [{"id": "story-moto"}]


def test_trava_de_tema_nunca_deixa_sem_post():
    hist = [_h(peca="video:bf-ao-vivo", tipo="video")]
    lista = [{"id": "bf-pix"}]
    assert tema.filtrar(lista, "story", hist, HOJE) == lista


# ------------------------------------------------------------------ estreia
GRADE = {"versao": "t", "itens": [
    {"id": "bf-sem-checkout", "formato": "reel", "titulo": "x", "video": "https://v/a.mp4",
     "dias": ["2026-10-27"], "valido_ate": "2026-11-30"},
    {"id": "antigo", "formato": "reel", "titulo": "y", "video": "https://v/b.mp4",
     "dias": ["2026-10-01"], "valido_ate": "2026-11-30"},
]}


def test_estreia_proxima_sai_do_sorteio(monkeypatch):
    monkeypatch.setattr(tema.grade, "validos", lambda dados=None: (GRADE["itens"], []))
    lista = [{"id": "bf-sem-checkout"}, {"id": "antigo"},
             {"id": "video:bf-sem-checkout", "fonte_id": "bf-sem-checkout"},
             {"id": "video:grade:bf-sem-checkout", "fonte_id": "bf-sem-checkout", "origem": "grade"}]
    ids = [p["id"] for p in tema.sem_estreia(lista, HOJE)]
    assert ids == ["antigo", "video:grade:bf-sem-checkout"]


# ------------------------------------------------------------------ pergunta
def test_banco_de_perguntas_limpo_e_sem_repetir_id():
    ids = [b[0] for b in sp.BANCO]
    assert len(ids) == len(set(ids))
    for _, pergunta, resposta in sp.BANCO:
        assert not compliance.violacoes(pergunta), pergunta
        assert not compliance.violacoes(resposta), resposta
        assert "trial" not in (pergunta + resposta).lower()


def test_pergunta_gira_o_banco():
    primeira = sp.da_vez([])
    assert primeira["tipo"] == "pergunta" and primeira["id"].startswith("pergunta:")
    usados = [b[0] for b in sp.BANCO if b[0] != "tripe"]
    assert sp.da_vez(usados)["pid"] == "tripe"


def test_pergunta_sai_do_segundo_story_do_dia(monkeypatch):
    monkeypatch.setattr(config, "hoje_br", lambda: HOJE)
    assert not story.precisa_pergunta([], HOJE, hora=10)
    um = [_h(peca="story-suco")]
    assert not story.precisa_pergunta(um, HOJE, hora=10)
    assert story.precisa_pergunta(um, HOJE, hora=18)
    dois = um + [_h(peca="video:x", tipo="video", horas=1)]
    assert story.precisa_pergunta(dois, HOJE, hora=10)
    feita = dois + [_h(peca="pergunta:ramo", tipo="pergunta", horas=3)]
    assert not story.precisa_pergunta(feita, HOJE, hora=20)


def test_pergunta_nao_entra_na_alternancia_video_arte():
    hist = [_h(peca="pergunta:ramo", tipo="pergunta"), _h(peca="video:x", tipo="video", horas=1)]
    assert story.proximo_tipo(hist) == "arte"


def test_madrugada_nao_publica():
    assert story.madrugada(1) and story.madrugada(6)
    assert not story.madrugada(7) and not story.madrugada(21)


def test_arte_da_pergunta_no_tamanho_do_story():
    img = sp.imagem(sp.da_vez([]), semente=1)
    assert img.size == (1080, 1920)
