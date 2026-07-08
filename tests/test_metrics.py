"""Testes de propriedade para as métricas plugáveis.

Nota: não há `Rscript` disponível neste ambiente, então a equivalência com o
`calc_ks_score` original não pôde ser cross-validada executando o R. Em vez
disso, este arquivo valida as propriedades matemáticas que a implementação
*precisa* satisfazer para ser fiel ao original (separação perfeita -> KS=1,
sem separação -> KS~0, score monotônico em relação à probabilidade) e replica
manualmente, passo a passo, a fórmula do R para um caso pequeno.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from pedro_wise.metrics import (
    FAIXAS_SAIDA,
    QUANTIS_QUEBRA,
    KSGaussianMetric,
    _rescalonar_por_faixas,
    _score_gaussiano,
)


class _ModeloFake:
    """FittedModel de mentira: devolve probabilidades fixas, sem depender de fit real."""

    def __init__(self, probs_por_split: dict[str, np.ndarray]) -> None:
        self._probs = probs_por_split
        self.variables = ("x",)

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        return self._probs[X.attrs["split"]]


def _dataset(probs_dev: np.ndarray, y_dev: np.ndarray, probs_test: np.ndarray, y_test: np.ndarray):
    X_dev = pd.DataFrame({"x": probs_dev})
    X_dev.attrs["split"] = "dev"
    X_test = pd.DataFrame({"x": probs_test})
    X_test.attrs["split"] = "test"
    y_dev_s = pd.Series(y_dev)
    y_test_s = pd.Series(y_test)
    modelo = _ModeloFake({"dev": probs_dev, "test": probs_test})
    return modelo, X_dev, y_dev_s, X_test, y_test_s


def test_ks_gaussiano_separacao_perfeita_da_ks_proximo_de_1():
    rng = np.random.default_rng(0)
    n = 200
    # y=0 tem probabilidades baixas, y=1 tem probabilidades altas -> separação perfeita
    probs_0 = rng.uniform(0.01, 0.2, n // 2)
    probs_1 = rng.uniform(0.8, 0.99, n // 2)
    probs = np.concatenate([probs_0, probs_1])
    y = np.concatenate([np.zeros(n // 2), np.ones(n // 2)])

    modelo, X_dev, y_dev, X_test, y_test = _dataset(probs, y, probs, y)
    metrica = KSGaussianMetric(criterio="teste")
    ks = metrica(modelo, X_dev, y_dev, X_test, y_test)

    assert ks > 0.95


def test_ks_gaussiano_sem_separacao_da_ks_proximo_de_0():
    rng = np.random.default_rng(1)
    n = 400
    # mesma distribuição de probabilidade independente de y -> sem poder discriminante
    probs = rng.uniform(0.3, 0.7, n)
    y = rng.integers(0, 2, n)

    modelo, X_dev, y_dev, X_test, y_test = _dataset(probs, y, probs, y)
    metrica = KSGaussianMetric(criterio="teste")
    ks = metrica(modelo, X_dev, y_dev, X_test, y_test)

    assert ks < 0.25


def test_ks_gaussiano_esta_sempre_entre_0_e_1():
    rng = np.random.default_rng(2)
    n = 150
    probs = rng.uniform(0.01, 0.99, n)
    y = rng.integers(0, 2, n)
    modelo, X_dev, y_dev, X_test, y_test = _dataset(probs, y, probs, y)

    for criterio in ("dev", "teste", "min"):
        ks = KSGaussianMetric(criterio=criterio)(modelo, X_dev, y_dev, X_test, y_test)
        assert 0.0 <= ks <= 1.0


def test_score_gaussiano_e_monotonico_em_relacao_a_probabilidade():
    """xbeta = logit(p) e score = 500 + xbeta*100/log(2) são estritamente crescentes em p."""
    probs = np.linspace(0.01, 0.99, 50)
    score = _score_gaussiano(probs)
    assert np.all(np.diff(score) >= 0)


def test_rescalonar_por_faixas_replica_a_formula_do_r_passo_a_passo():
    """Reproduz manualmente, para um score conhecido, a fórmula do R:
    quebras fixas, banda 2 (quebras[2]..quebras[3] -> saída 101..200).
    """
    quebras = np.array([0.0, 100.0, 200.0, 1000.0, 1000.0, 1000.0, 1000.0, 1000.0, 1000.0, 1000.0, 1000.0])
    score_gauss = np.array([150.0])  # cai na 2ª faixa: (100, 200] -> saída (101, 200]
    saida = _rescalonar_por_faixas(score_gauss, quebras)

    esperado = 101 + (150.0 - 100.0) * (200 - 101) / (200.0 - 100.0)
    assert saida[0] == pytest.approx(esperado)


def test_quantis_e_faixas_de_saida_tem_o_mesmo_numero_de_bandas():
    assert len(QUANTIS_QUEBRA) - 1 == len(FAIXAS_SAIDA) == 10
