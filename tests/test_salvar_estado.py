# -*- coding: utf-8 -*-
"""Salvar estado sem perder o post (incidente Feed #44, 07/10/2026).

O feed saiu, outro commit mexeu em estado/historico.json no meio do caminho,
o `git pull --rebase` deu conflito e o registro do post se perdeu.
"""
import json
import os
import subprocess

import salvar_estado as se


# ------------------------------------------------------------------ mescla
def test_historico_novo_entra_no_topo_de_origin():
    base = [{"q": 1}]
    nosso = [{"q": 3, "formato": "feed"}, {"q": 1}]
    deles = [{"q": 2, "formato": "story"}, {"q": 1}]
    assert se.mesclar(base, nosso, deles) == [{"q": 3, "formato": "feed"}, {"q": 2, "formato": "story"}, {"q": 1}]


def test_recentes_peca_que_volta_para_frente():
    base = ["a", "b", "c"]
    nosso = ["c", "a", "b"]          # marcar_usado("c")
    deles = ["x", "a", "b"]          # outro commit marcou "x" e cortou "c"
    assert se.mesclar(base, nosso, deles) == ["c", "x", "a"]


def test_so_um_lado_mudou():
    assert se.mesclar([1], [1], [2, 1]) == [2, 1]
    assert se.mesclar([1], [3, 1], [1]) == [3, 1]
    assert se.mesclar({"a": 1}, {"a": 1}, {"a": 2}) == {"a": 2}


def test_dicionario_os_dois_mudaram_vale_a_rodada():
    assert se.mesclar({"v": 0}, {"v": 1}, {"v": 2}) == {"v": 1}


def test_arquivo_criado_e_apagado():
    assert se.mesclar(se.AUSENTE, {"freio": 1}, se.AUSENTE) == {"freio": 1}
    assert se.mesclar({"freio": 1}, se.AUSENTE, {"freio": 1}) is se.AUSENTE


def test_respeita_teto():
    base = list(range(10))
    nosso = [99] + list(range(9))
    deles = [50] + list(range(9))
    r = se.mesclar(base, nosso, deles)
    assert r[:2] == [99, 50] and len(r) == 10


# ------------------------------------------------------------------ git real
def _sh(cwd, *cmd):
    return subprocess.run(cmd, cwd=cwd, check=True, capture_output=True, text=True).stdout


def _grava(pasta, nome, valor):
    p = pasta / "estado" / nome
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(valor, ensure_ascii=False, indent=1), encoding="utf-8")


def _le(pasta, nome):
    return json.loads((pasta / "estado" / nome).read_text(encoding="utf-8"))


def test_incidente_feed_44_conflito_no_historico(tmp_path, monkeypatch):
    origem = tmp_path / "origem.git"
    _sh(tmp_path, "git", "init", "--bare", "-b", "main", str(origem))
    semente = tmp_path / "semente"
    _sh(tmp_path, "git", "clone", str(origem), str(semente))
    for c in (("user.name", "t"), ("user.email", "t@t")):
        _sh(semente, "git", "config", *c)
    _grava(semente, "historico.json", [{"quando": "06/10", "formato": "feed"}])
    _grava(semente, "recentes_pecas_feed.json", ["p1", "p2"])
    _sh(semente, "git", "add", "-A")
    _sh(semente, "git", "commit", "-m", "inicio")
    _sh(semente, "git", "push", "origin", "main")

    # A rodada do feed baixa o repo...
    rodada = tmp_path / "rodada"
    _sh(tmp_path, "git", "clone", "--depth=1", f"file://{origem}", str(rodada))

    # ...enquanto isso a story grava o historico em origin/main.
    _grava(semente, "historico.json", [{"quando": "07/10 16:08", "formato": "story"},
                                       {"quando": "06/10", "formato": "feed"}])
    _sh(semente, "git", "commit", "-am", "estado: story")
    _sh(semente, "git", "push", "origin", "main")

    # A rodada publica o feed e grava o proprio estado.
    _grava(rodada, "historico.json", [{"quando": "07/10 16:15", "formato": "feed"},
                                      {"quando": "06/10", "formato": "feed"}])
    _grava(rodada, "recentes_pecas_feed.json", ["p3", "p1", "p2"])

    monkeypatch.chdir(rodada)
    monkeypatch.setattr(se.time, "sleep", lambda s: None)
    assert se.main() == 0

    final = tmp_path / "final"
    _sh(tmp_path, "git", "clone", str(origem), str(final))
    assert [h["quando"] for h in _le(final, "historico.json")] == ["07/10 16:15", "07/10 16:08", "06/10"]
    assert _le(final, "recentes_pecas_feed.json") == ["p3", "p1", "p2"]


def test_nada_a_commitar(tmp_path, monkeypatch):
    origem = tmp_path / "o.git"
    _sh(tmp_path, "git", "init", "--bare", "-b", "main", str(origem))
    r = tmp_path / "r"
    _sh(tmp_path, "git", "clone", str(origem), str(r))
    for c in (("user.name", "t"), ("user.email", "t@t")):
        _sh(r, "git", "config", *c)
    _grava(r, "historico.json", [])
    _sh(r, "git", "add", "-A")
    _sh(r, "git", "commit", "-m", "i")
    _sh(r, "git", "push", "origin", "main")
    monkeypatch.chdir(r)
    assert se.main() == 0
    assert _sh(r, "git", "log", "--oneline").count("\n") == 1
