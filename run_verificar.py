# -*- coding: utf-8 -*-
"""
Verificacao semanal de saude do robo.

Existe porque a falha mais comum e SILENCIOSA: o token de pagina da Meta
expira (tipicamente 60 dias) e o robo simplesmente para de publicar sem
ninguem perceber por semanas.

Falha aqui = workflow vermelho = e-mail do GitHub. E o alarme.
"""
from src import config, conteudo, firestore
from src.social.instagram import Instagram

CHECAGENS = []


def checar(nome, funcao, critico=True):
    try:
        detalhe = funcao()
        print(f"[ok]    {nome}: {detalhe}")
        CHECAGENS.append((nome, True, detalhe, critico))
    except Exception as e:  # noqa: BLE001
        print(f"[FALHA] {nome}: {e}")
        CHECAGENS.append((nome, False, str(e), critico))


def main():
    def token():
        d = Instagram().validar_token()
        return f"@{d.get('username','?')} | {d.get('followers_count','?')} seguidores"

    def base():
        todos = firestore.listar_negocios()
        ok = firestore.elegiveis(todos)
        return (f"{len(todos)} negocios | {len(ok)} autorizaram divulgacao "
                f"(minimo pra vitrine: {config.MIN_NEGOCIOS_VITRINE})")

    def pautas():
        p = conteudo.carregar()
        if not p:
            raise RuntimeError("conteudo/pautas.md vazio")
        return f"{len(p)} pautas carregadas"

    def envs():
        faltando = [n for n in ("IG_ACCOUNT_ID", "PAGE_ACCESS_TOKEN",
                                "FIREBASE_PROJECT_ID")
                    if not getattr(config, n, "")]
        if faltando:
            raise RuntimeError("secrets ausentes: " + ", ".join(faltando))
        return "todos os secrets obrigatorios presentes"

    checar("secrets", envs)
    checar("token da Meta", token)
    checar("pautas", pautas)
    checar("base do Moviki", base, critico=False)

    falhas_criticas = [c for c in CHECAGENS if not c[1] and c[3]]
    if falhas_criticas:
        raise SystemExit(
            f"\n{len(falhas_criticas)} checagem(ns) critica(s) falharam — "
            f"o robo NAO vai conseguir publicar. Corrigir antes do proximo ciclo."
        )
    print("\nOK -> robo saudavel")


if __name__ == "__main__":
    main()
