"""Testes do módulo de construção de variáveis (v1: razões/diferenças)."""

from __future__ import annotations

import numpy as np
import pandas as pd
from construcao import construir_diferenca, construir_razao, construir_razoes_em_lote


def test_construir_razao_basica():
    numerador = pd.Series([10.0, 20.0, 30.0])
    denominador = pd.Series([2.0, 4.0, 5.0])
    resultado = construir_razao(numerador, denominador, "razao")
    assert resultado.tolist() == [5.0, 5.0, 6.0]
    assert resultado.name == "razao"


def test_construir_razao_evita_divisao_por_zero_literal():
    numerador = pd.Series([10.0, 20.0])
    denominador = pd.Series([0.0, 5.0])
    resultado = construir_razao(numerador, denominador, "razao", epsilon=1e-6)
    assert np.isfinite(resultado).all()
    assert resultado.iloc[1] == 4.0  # caso normal não afetado pela epsilon


def test_construir_razao_preserva_sinal_de_denominador_negativo():
    """Correção de um bug real encontrado no design inicial: usar abs() no
    denominador inverteria o sinal da razão para denominadores negativos.
    """
    numerador = pd.Series([10.0])
    denominador = pd.Series([-5.0])
    resultado = construir_razao(numerador, denominador, "razao")
    assert resultado.iloc[0] == -2.0


def test_construir_diferenca():
    a = pd.Series([100.0, 200.0])
    b = pd.Series([80.0, 250.0])
    resultado = construir_diferenca(a, b, "diferenca")
    assert resultado.tolist() == [20.0, -50.0]
    assert resultado.name == "diferenca"


def test_construir_razoes_em_lote():
    df = pd.DataFrame(
        {"pay1": [50.0, 100.0], "bill1": [100.0, 200.0], "pay2": [30.0, 60.0], "bill2": [60.0, 120.0]}
    )
    pares = [("pay1", "bill1", "prop_paga_1"), ("pay2", "bill2", "prop_paga_2")]
    resultado = construir_razoes_em_lote(df, pares)

    assert list(resultado.columns) == ["prop_paga_1", "prop_paga_2"]
    assert resultado["prop_paga_1"].tolist() == [0.5, 0.5]
    assert resultado["prop_paga_2"].tolist() == [0.5, 0.5]
    assert len(resultado) == len(df)
