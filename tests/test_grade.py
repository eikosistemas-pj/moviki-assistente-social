# -*- coding: utf-8 -*-
"""Grade editorial de videos (30/09/2026)."""
import json
from datetime import date

from src import compliance, config, grade, pecas

URL_V = "https://github.com/eikosistemas-pj/moviki-assistente-social/releases/download/acervo/{}.mp4"
URL_C = "https://raw.githubusercontent.com/eikosistemas-pj/moviki-assistente-social/main/conteudo/acervo-capas/{}.jpg"


def item(iid="video-teste", **kw):
    base = {
        "id": iid, "formato": "reel", "pilar": "serie-live", "ramo": "geral",
        "titulo": "Live da sua loja", "video": URL_V.format(iid), "capa": URL_C.format(iid),
        "legenda": "Abra a live da sua loja pelo celular. Conheça pelo link da bio.",
        "canais": ["instagram", "facebook"], "vende_live": True,
        "dias": ["2026-10-06"], "a_partir_de": "2026-10-06", "valido_ate": "2027-01-04",
        "repetir_apos_dias": 45,
    }
    base.update(kw)
    return base


def grade_de(*itens):
    return {"versao": "t", "itens": list(itens)}


def hist(pid, quando):
    return [{"quando": quando, "formato": "reel", "peca": pid}]


# ------------------------------------------------------------------ validacao
def test_item_valido():
    assert grade.validar(item()) == []


def test_video_fora_da_release_acervo_barra():
    e = grade.validar(item(video="https://exemplo.com/x.mp4"))
    assert any("release acervo" in x for x in e)


def test_sem_valido_ate_barra():
    e = grade.validar(item(valido_ate=None))
    assert any("valido_ate" in x for x in e)


def test_data_mal_escrita_barra():
    assert grade.validar(item(dias=["06/10/2026"]))


def test_canal_desconhecido_barra():
    assert grade.validar(item(canais=["tiktok"]))


# ------------------------------------------------------------------ agendado
def test_agendado_sai_no_dia(monkeypatch):
    monkeypatch.setattr(config, "LIVE_NA_PAGINA", True)
    p = grade.agendada_hoje("reel", date(2026, 10, 6), grade_de(item()), [], conferir=None)
    assert p and p["id"] == "grade:video-teste" and p["origem"] == "grade"
    assert p["legenda_fb"].endswith("moviki.com.br") and "link da bio" not in p["legenda_fb"]


def test_agendado_nao_sai_duas_vezes_no_mesmo_dia(monkeypatch):
    monkeypatch.setattr(config, "LIVE_NA_PAGINA", True)
    h = hist("grade:video-teste", "2026-10-06T20:30:00+00:00")
    assert grade.agendada_hoje("reel", date(2026, 10, 6), grade_de(item()), h, conferir=None) is None


def test_vencido_nunca_sai(monkeypatch):
    monkeypatch.setattr(config, "LIVE_NA_PAGINA", True)
    it = item(dias=["2027-02-02"], valido_ate="2027-01-04", a_partir_de="2026-10-06")
    assert grade.agendada_hoje("reel", date(2027, 2, 2), grade_de(it), [], conferir=None) is None


def test_reconferir_vencido_trava(monkeypatch):
    monkeypatch.setattr(config, "LIVE_NA_PAGINA", True)
    it = item(reconferir_em="2026-10-05")
    assert grade.agendada_hoje("reel", date(2026, 10, 6), grade_de(it), [], conferir=None) is None


def test_live_fechada_trava_video_que_vende_live(monkeypatch):
    monkeypatch.setattr(config, "LIVE_NA_PAGINA", False)
    assert grade.agendada_hoje("reel", date(2026, 10, 6), grade_de(item()), [], conferir=None) is None


def test_video_fora_da_release_nao_vai_para_a_meta(monkeypatch):
    monkeypatch.setattr(config, "LIVE_NA_PAGINA", True)
    assert grade.agendada_hoje("reel", date(2026, 10, 6), grade_de(item()), [], conferir=lambda u: False) is None


def test_relatorio_avisa_video_fora_da_release(monkeypatch):
    monkeypatch.setattr(config, "LIVE_NA_PAGINA", True)
    bloco, al = grade.relatorio(date(2026, 10, 1), grade_de(item()), [], conferir=lambda u: False)
    assert bloco["proximos"][0]["sai"] is False and any("release acervo" in a["texto"] for a in al)


# ------------------------------------------------------------------ rodizio
def test_rodizio_guarda_video_para_o_dia_marcado(monkeypatch):
    monkeypatch.setattr(config, "LIVE_NA_PAGINA", True)
    it = item(a_partir_de="2026-10-01", dias=["2026-10-10"])
    assert grade.rodizio("reel", date(2026, 10, 3), grade_de(it), [], conferir=None) == []


def test_rodizio_respeita_intervalo(monkeypatch):
    monkeypatch.setattr(config, "LIVE_NA_PAGINA", True)
    it = item(dias=["2026-10-06"])
    h = hist("grade:video-teste", "2026-10-06T20:30:00+00:00")
    assert grade.rodizio("reel", date(2026, 11, 1), grade_de(it), h, conferir=None) == []
    assert len(grade.rodizio("reel", date(2026, 11, 25), grade_de(it), h, conferir=None)) == 1


def test_so_agendado_fica_fora_do_rodizio(monkeypatch):
    monkeypatch.setattr(config, "LIVE_NA_PAGINA", True)
    it = item(so_agendado=True, dias=["2026-10-06"])
    assert grade.rodizio("reel", date(2026, 12, 1), grade_de(it), [], conferir=None) == []


def test_escolher_peca_prefere_a_agendada(monkeypatch):
    ag = {"id": "grade:x", "origem": "grade", "formato": "reel", "categoria": "geral"}
    monkeypatch.setattr(grade, "agendada_hoje", lambda formato: ag)
    monkeypatch.setattr(pecas, "candidatas", lambda f: (_ for _ in ()).throw(AssertionError("nao devia sortear")))
    assert pecas.escolher_peca("reel") is ag


def test_forcar_criador_pula_a_grade(monkeypatch):
    monkeypatch.setattr(grade, "agendada_hoje", lambda formato: (_ for _ in ()).throw(AssertionError("nao devia olhar")))
    monkeypatch.setattr(pecas, "candidatas", lambda f: {"casa": [], "criador": []})
    assert pecas.escolher_peca("reel", "criador") is None


def test_grade_quebrada_nao_derruba_o_reel(monkeypatch):
    def quebra(formato):
        raise ValueError("json ruim")
    monkeypatch.setattr(grade, "agendada_hoje", quebra)
    monkeypatch.setattr(pecas, "candidatas", lambda f: {"casa": [{"id": "m1", "origem": "material", "formato": "reel", "categoria": "moda", "criador": None}], "criador": []})
    monkeypatch.setattr(pecas.estado, "recentes", lambda f: [])
    assert pecas.escolher_peca("reel")["id"] == "m1"


# ------------------------------------------------------------------ relatorio
def test_relatorio_avisa_dia_sem_reel(monkeypatch):
    monkeypatch.setattr(config, "LIVE_NA_PAGINA", True)
    from run_metricas import esperado
    it = item(dias=["2026-10-05"], a_partir_de="2026-10-05")   # segunda: nao tem reel
    bloco, al = grade.relatorio(date(2026, 10, 1), grade_de(it), [], dia_de=esperado, conferir=None)
    assert bloco["proximos"][0]["sai"] is False
    assert any(a["nivel"] == "grave" and "dia sem reel" in a["texto"] for a in al)


def test_relatorio_avisa_vencimento_proximo(monkeypatch):
    monkeypatch.setattr(config, "LIVE_NA_PAGINA", True)
    it = item(dias=[], valido_ate="2026-10-08", a_partir_de="2026-10-01")
    bloco, al = grade.relatorio(date(2026, 10, 3), grade_de(it), [], conferir=None)
    assert bloco["vencendo"] and any("sai de circulação" in a["texto"] for a in al)


def test_relatorio_item_quebrado_e_grave():
    bloco, al = grade.relatorio(date(2026, 10, 3), grade_de(item(video="http://x")), [], conferir=None)
    assert bloco["com_erro"] == 1 and al[0]["nivel"] == "grave"


# ------------------------------------------------------------------ a grade real
def test_grade_do_repositorio_esta_valida_e_limpa(monkeypatch):
    monkeypatch.setattr(config, "LIVE_NA_PAGINA", True)
    from run_metricas import esperado
    dados = json.loads((config.CONTEUDO_DIR / "grade.json").read_text(encoding="utf-8"))
    ids = [i["id"] for i in dados["itens"]]
    assert len(ids) == len(set(ids)), "id repetido na grade"
    for it in dados["itens"]:
        assert grade.validar(it) == [], it["id"]
        assert compliance.violacoes(it["legenda"]) == [], it["id"]
        assert "tiktok" not in it["legenda"].lower(), "marca de terceiro na legenda"
        for d in it.get("dias") or []:
            assert esperado(it["formato"], date.fromisoformat(d)) > 0, f"{it['id']} marcado em dia sem {it['formato']}"
        capa = config.CONTEUDO_DIR / "acervo-capas" / (it["id"] + ".jpg")
        assert capa.exists(), f"falta a capa {capa.name}"
