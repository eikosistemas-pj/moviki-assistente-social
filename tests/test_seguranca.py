# -*- coding: utf-8 -*-
"""23/09/2026: o log do Actions e publico — nenhum token pode aparecer em mensagem de erro."""
from src import util_net


def test_token_na_url_some_do_erro():
    msg = util_net.sem_segredo("Max retries: /v25.0/1/photos?url=a&access_token=EAAB123abc&x=1")
    assert "EAAB123abc" not in msg and "access_token=***" in msg


def test_token_no_cabecalho_some_do_erro():
    assert "EAAxyz" not in util_net.sem_segredo("Authorization: OAuth EAAxyz.-9 falhou")
    assert "abc.def" not in util_net.sem_segredo("Bearer abc.def recusado")
