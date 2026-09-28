# -*- coding: utf-8 -*-
"""
Freio automatico do Instagram (28/09/2026).

Por que existe: a conta nova @moviki.oficial nao pode insistir em publicar
depois de uma recusa da Meta — repetir chamada que falha e exatamente o
padrao que leva a restricao. A conta antiga ja foi restrita uma vez.

Regra:
  - toda falha do Instagram (post saiu so na Pagina, plano B) soma 1;
  - todo post que sai no Instagram zera a conta;
  - FREIO_FALHAS falhas seguidas (padrao 2) -> Instagram fora por FREIO_HORAS
    (padrao 72 h). Nesse periodo TUDO sai so na Pagina, sem tentar o Instagram.
  - passado o prazo, o robo tenta de novo sozinho. Falhou mais 2 vezes, freia
    de novo.

O estado mora em estado/instagram_freio.json (commitado pelo workflow, lido
pelo painel do dono e pelo agente diario). Soltar o freio na mao: apagar esse
arquivo no GitHub.
"""
from datetime import datetime, timedelta, timezone

from . import config, estado

ARQUIVO = "instagram_freio.json"


def _agora():
    return datetime.now(timezone.utc)


def ler():
    d = estado.ler_lista(ARQUIVO)
    return d if isinstance(d, dict) else {}


def _gravar(d):
    estado.gravar_lista(ARQUIVO, d)


def ativo(agora=None):
    """Data/hora (datetime UTC) ate quando o freio vale, ou None."""
    ate = ler().get("ate")
    if not ate:
        return None
    try:
        fim = datetime.fromisoformat(ate)
    except ValueError:
        return None
    return fim if (agora or _agora()) < fim else None


def no_instagram(formato, agora=None):
    """Decisao final de canal: config (secret + rampa) E freio solto."""
    if not config.instagram_ligado(formato):
        return False
    fim = ativo(agora)
    if fim:
        print(f"FREIO do Instagram ativo ate {fim.isoformat(timespec='minutes')} -> so Facebook.")
        return False
    return True


def falhou(formato, erro, agora=None):
    """Conta a falha. Devolve True se esta falha ACIONOU o freio."""
    agora = agora or _agora()
    d = ler()
    d["falhas"] = int(d.get("falhas") or 0) + 1
    d["ultima_falha"] = {"quando": agora.isoformat(timespec="seconds"),
                         "formato": formato, "erro": str(erro)[:300]}
    acionou = False
    if d["falhas"] >= config.FREIO_FALHAS:
        d["ate"] = (agora + timedelta(hours=config.FREIO_HORAS)).isoformat(timespec="seconds")
        d["acionado_em"] = agora.isoformat(timespec="seconds")
        d["falhas"] = 0
        acionou = True
        print(f"FREIO ACIONADO: {config.FREIO_FALHAS} falhas seguidas do Instagram -> "
              f"so Facebook por {config.FREIO_HORAS} h.")
    _gravar(d)
    return acionou


def sucesso():
    """Post saiu no Instagram: zera a contagem (mantem o historico do ultimo freio)."""
    d = ler()
    if d.get("falhas"):
        d["falhas"] = 0
        _gravar(d)
