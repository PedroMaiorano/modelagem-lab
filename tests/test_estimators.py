"""Testes de python/pedro_wise/estimators.py."""

from __future__ import annotations

import numpy as np
import pandas as pd
from pedro_wise.estimators import LogisticGLM


def test_coeficientes_inclui_intercepto_e_todas_as_variaveis():
    rng = np.random.default_rng(0)
    n = 500
    x1 = pd.Series(rng.normal(size=n), name="x1")
    x2 = pd.Series(rng.normal(size=n), name="x2")
    y = pd.Series((x1 + 0.5 * x2 + rng.normal(scale=0.1, size=n) > 0).astype(int), name="y")
    X = pd.DataFrame({"x1": x1, "x2": x2})

    modelo = LogisticGLM().fit(X, y)
    coefs = modelo.coeficientes()

    assert set(coefs.keys()) == {"const", "x1", "x2"}
    assert all(isinstance(v, float) for v in coefs.values())
    # sinal esperado: x1 e x2 têm coeficiente positivo por construção do y
    assert coefs["x1"] > 0
    assert coefs["x2"] > 0


def test_estatisticas_inclui_erro_padrao_e_p_valor():
    rng = np.random.default_rng(0)
    n = 500
    x1 = pd.Series(rng.normal(size=n), name="x1")
    x2 = pd.Series(rng.normal(size=n), name="x2")
    y = pd.Series((x1 + 0.5 * x2 + rng.normal(scale=0.1, size=n) > 0).astype(int), name="y")
    X = pd.DataFrame({"x1": x1, "x2": x2})

    modelo = LogisticGLM().fit(X, y)
    stats = modelo.estatisticas()

    assert set(stats.keys()) == {"const", "x1", "x2"}
    for chave in ("coeficiente", "erro_padrao", "p_valor"):
        assert all(chave in v for v in stats.values())
    # x1 tem relação forte e limpa com y — deve ser claramente significativo
    assert stats["x1"]["p_valor"] < 0.01
    assert stats["x1"]["erro_padrao"] > 0
    assert stats["x1"]["coeficiente"] == modelo.coeficientes()["x1"]
