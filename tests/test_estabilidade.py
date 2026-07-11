"""Testes da validação out-of-time de regras (dev vs. teste)."""

from __future__ import annotations

import numpy as np
import pandas as pd
from interacao import Condicao, Regra, avaliar_estabilidade


def _dataset_interacao_xor(n: int, semente: int) -> tuple[pd.DataFrame, pd.Series]:
    rng = np.random.default_rng(semente)
    a = rng.normal(0, 1, n)
    b = rng.normal(0, 1, n)
    logit_p = -3.0 + 6.0 * ((a > 0) & (b > 0)).astype(float)
    p = 1 / (1 + np.exp(-logit_p))
    y = pd.Series(rng.binomial(1, p))
    return pd.DataFrame({"a": a, "b": b}), y


def test_regra_real_mantem_iv_alto_em_dev_e_teste():
    X_dev, y_dev = _dataset_interacao_xor(3000, semente=0)
    X_teste, y_teste = _dataset_interacao_xor(3000, semente=1)  # amostra independente, mesma distribuição
    regra_real = Regra((Condicao("a", ">", 0.0), Condicao("b", ">", 0.0)))

    tabela = avaliar_estabilidade([regra_real], X_dev, y_dev, X_teste, y_teste)

    assert tabela.loc[0, "iv_dev"] > 0.3
    assert tabela.loc[0, "iv_teste"] > 0.3  # o sinal é real -- sustenta fora da amostra de descoberta


def test_regra_espuria_perde_iv_em_teste():
    """Regra que só existe por acaso numa amostra pequena de dev (limiares
    arbitrários sem relação com o y verdadeiro) não deve se sustentar num
    teste com distribuição diferente/aleatória.
    """
    rng = np.random.default_rng(42)
    X_dev = pd.DataFrame({"a": rng.normal(0, 1, 200), "b": rng.normal(0, 1, 200)})
    y_dev = pd.Series(rng.binomial(1, 0.3, 200))  # y independente de a/b -- ruído puro
    X_teste = pd.DataFrame({"a": rng.normal(0, 1, 3000), "b": rng.normal(0, 1, 3000)})
    y_teste = pd.Series(rng.binomial(1, 0.3, 3000))

    regra_arbitraria = Regra((Condicao("a", ">", 0.3), Condicao("b", ">", -0.1)))
    tabela = avaliar_estabilidade([regra_arbitraria], X_dev, y_dev, X_teste, y_teste)

    assert tabela.loc[0, "iv_teste"] < 0.05  # sem sinal de verdade, IV out-of-time fica baixo


def test_ordenado_por_iv_teste_nao_por_iv_dev():
    X_dev, y_dev = _dataset_interacao_xor(3000, semente=0)
    X_teste, y_teste = _dataset_interacao_xor(3000, semente=1)
    regra_real = Regra((Condicao("a", ">", 0.0), Condicao("b", ">", 0.0)))
    regra_fraca = Regra((Condicao("a", ">", 2.5), Condicao("b", ">", 2.5)))  # suporte quase nulo

    tabela = avaliar_estabilidade([regra_fraca, regra_real], X_dev, y_dev, X_teste, y_teste)
    assert tabela.iloc[0]["regra"] == regra_real.nome


def test_suporte_quase_zero_em_teste_nao_quebra_avaliacao():
    X_dev, y_dev = _dataset_interacao_xor(500, semente=0)
    X_teste = pd.DataFrame({"a": [-5.0, -5.0], "b": [-5.0, -5.0]})  # regra nunca satisfeita em teste
    y_teste = pd.Series([0, 1])
    regra = Regra((Condicao("a", ">", 0.0), Condicao("b", ">", 0.0)))

    tabela = avaliar_estabilidade([regra], X_dev, y_dev, X_teste, y_teste)
    assert tabela.loc[0, "suporte_teste"] == 0.0
    assert tabela.loc[0, "iv_teste"] == 0.0


def test_colunas_da_tabela():
    X_dev, y_dev = _dataset_interacao_xor(500, semente=0)
    X_teste, y_teste = _dataset_interacao_xor(500, semente=1)
    regra = Regra((Condicao("a", ">", 0.0), Condicao("b", ">", 0.0)))

    tabela = avaliar_estabilidade([regra], X_dev, y_dev, X_teste, y_teste)
    assert list(tabela.columns) == ["regra", "suporte_dev", "suporte_teste", "iv_dev", "iv_teste"]
