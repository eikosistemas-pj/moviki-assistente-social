# -*- coding: utf-8 -*-
"""
Verificacao semanal de saude do robo.

Existe porque a falha mais comum e SILENCIOSA: o token de pagina da Meta
expira (tipicamente 60 dias) e o robo simplesmente para de publicar sem
ninguem perceber por semanas.

Falha aqui = workflow vermelho = e-mail do GitHub. E o alarme.
"""
from src import config, conteudo, firestore
from src import util_net as net
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
        # No modo SO_FACEBOOK a conta do Instagram nao existe pro robo — o
        # que precisa estar vivo e o token da Pagina. Validar pelo canal
        # que realmente publica, senao o alarme vigia a porta errada.
        if config.SO_FACEBOOK:
            r = net.get(
                f"{config.GRAPH}/{config.FACEBOOK_PAGE_ID}",
                params={"fields": "name,fan_count", "access_token": config.PAGE_ACCESS_TOKEN},
            ).json()
            if "error" in r:
                raise RuntimeError(r["error"].get("message"))
            return f"Pagina {r.get('name','?')} | {r.get('fan_count','?')} curtidas"
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
        # O conjunto obrigatorio muda com o canal: sem Instagram, o que nao
        # pode faltar e o FACEBOOK_PAGE_ID.
        if config.SO_FACEBOOK:
            precisa = ("FACEBOOK_PAGE_ID", "PAGE_ACCESS_TOKEN", "FIREBASE_PROJECT_ID")
        else:
            precisa = ("IG_ACCOUNT_ID", "PAGE_ACCESS_TOKEN", "FIREBASE_PROJECT_ID")
        faltando = [n for n in precisa if not getattr(config, n, "")]
        if faltando:
            raise RuntimeError("secrets ausentes: " + ", ".join(faltando))
        canal = "somente Facebook" if config.SO_FACEBOOK else "Instagram + espelho no Facebook"
        return f"secrets obrigatorios presentes | canal: {canal}"

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
