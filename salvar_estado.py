# -*- coding: utf-8 -*-
"""
Salva estado/ no repositorio sem nunca perder o que a rodada publicou.

INCIDENTE 07/10/2026 (Feed #44): o post saiu, mas o passo "Salvar estado"
fazia `git pull --rebase` e, com outro commit mexendo em estado/historico.json
no meio do caminho, o rebase deu conflito, o push falhou (exit 128) e o
registro do post se perdeu: sumiu do historico, do relatorio e do painel, e a
peca nao entrou na janela anti-repeticao.

Como funciona agora (merge a tres pontas, por arquivo, em JSON):
  base   = estado no commit que a rodada baixou (checkout)
  nosso  = estado que a rodada gravou
  deles  = estado atual em origin/main
  - lista (historico, recentes_*): o que a rodada ACRESCENTOU ou trouxe para
    a frente entra no topo da lista de origin/main, sem duplicar;
  - qualquer outro valor: se so um lado mudou, vale esse lado; se os dois
    mudaram, vale o da rodada (e o mais novo).
Tenta ate 5 vezes (fetch -> mescla -> commit -> push). Nunca usa rebase.

Uso no workflow:  python salvar_estado.py "estado: feed"
"""
import json
import random
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

MARCA = "2026-10-08-salvar"
PASTA = "estado"
TENTATIVAS = 5
AUSENTE = object()


# ------------------------------------------------------------------ mescla
def _chave(x):
    return json.dumps(x, ensure_ascii=False, sort_keys=True)


def mesclar_lista(base, nosso, deles):
    """Itens novos (ou trazidos para a frente) pela rodada vao para o topo de
    `deles`. Se a rodada NAO aumentou a lista, ela bateu no teto (janela
    anti-repeticao ou 2000 do historico) e o resultado respeita esse teto."""
    pos_base = {}
    for i, x in enumerate(base):
        pos_base.setdefault(_chave(x), i)
    novos, vistos = [], set()
    for i, x in enumerate(nosso):
        k = _chave(x)
        if k in vistos:
            continue
        if k not in pos_base or i < pos_base[k]:
            novos.append(x)
            vistos.add(k)
    resto = [x for x in deles if _chave(x) not in vistos]
    final = novos + resto
    if base and len(nosso) <= len(base):
        final = final[: len(nosso)]
    return final


def mesclar(base, nosso, deles):
    """Valor final de um arquivo de estado. AUSENTE = arquivo nao existe."""
    if _igual(nosso, base):
        return deles
    if _igual(deles, base):
        return nosso
    if isinstance(nosso, list) and isinstance(deles, list):
        return mesclar_lista(base if isinstance(base, list) else [], nosso, deles)
    return nosso


def _igual(a, b):
    if a is AUSENTE or b is AUSENTE:
        return a is b
    return _chave(a) == _chave(b)


# ------------------------------------------------------------------ git
def _git(*args, ok=False):
    r = subprocess.run(["git", *args], capture_output=True, text=True)
    if r.returncode != 0 and not ok:
        raise RuntimeError(f"git {' '.join(args)}: {r.stderr.strip()[-400:]}")
    return r


def _ler_commit(ref, caminho):
    r = _git("show", f"{ref}:{caminho}", ok=True)
    if r.returncode != 0:
        return AUSENTE
    try:
        return json.loads(r.stdout)
    except Exception:
        return AUSENTE


def _ler_disco(caminho):
    p = Path(caminho)
    if not p.exists():
        return AUSENTE
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return AUSENTE


def _gravar(caminho, valor):
    p = Path(caminho)
    if valor is AUSENTE:
        if p.exists():
            p.unlink()
        return
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(valor, ensure_ascii=False, indent=1), encoding="utf-8")


def _alterados():
    r = _git("status", "--porcelain", "--untracked-files=all", "--", PASTA)
    nomes = []
    for linha in r.stdout.splitlines():
        caminho = linha[3:].strip().strip('"')
        if " -> " in caminho:
            caminho = caminho.split(" -> ", 1)[1]
        if caminho.endswith(".json"):
            nomes.append(caminho)
    return sorted(set(nomes))


def main():
    print(f"salvar_estado {MARCA}")
    msg = (sys.argv[1] if len(sys.argv) > 1 else "estado").strip()
    msg = f"{msg} {datetime.now(timezone.utc):%Y-%m-%d}"
    _git("config", "user.name", "moviki-assistente-social")
    _git("config", "user.email", "bot@moviki.com.br")

    base = _git("rev-parse", "HEAD").stdout.strip()
    arquivos = _alterados()
    if not arquivos:
        print("nada a commitar")
        return 0
    nosso = {a: _ler_disco(a) for a in arquivos}
    print(f"estado alterado nesta rodada: {', '.join(arquivos)}")

    for tentativa in range(1, TENTATIVAS + 1):
        _git("fetch", "--depth=1", "origin", "main")
        deles_ref = _git("rev-parse", "FETCH_HEAD").stdout.strip()
        if deles_ref != base:
            print(f"origin/main andou ({base[:7]} -> {deles_ref[:7]}): mesclando")
        _git("reset", "--hard", deles_ref)
        for a in arquivos:
            final = mesclar(_ler_commit(base, a), nosso[a], _ler_commit(deles_ref, a))
            _gravar(a, final)
        _git("add", "-A", "--", PASTA)
        if _git("diff", "--staged", "--quiet", ok=True).returncode == 0:
            print("nada a commitar depois da mescla")
            return 0
        _git("commit", "-m", msg)
        if _git("push", "origin", "HEAD:main", ok=True).returncode == 0:
            print(f"estado salvo na tentativa {tentativa}")
            return 0
        espera = random.randint(3, 12)
        print(f"push recusado (tentativa {tentativa}); nova tentativa em {espera}s")
        time.sleep(espera)

    print("::error::estado NAO foi salvo depois de 5 tentativas — o post pode ter saido sem registro")
    for a in arquivos:
        print(f"--- {a} (versao da rodada) ---")
        print(json.dumps(nosso[a], ensure_ascii=False)[:3000] if nosso[a] is not AUSENTE else "(apagado)")
    return 1


if __name__ == "__main__":
    sys.exit(main())
