"""Métricas de seleção plugáveis.

`KSGaussianMetric` é o port fiel de `calc_ks_score` (R): prob -> logit -> score
Gaussiano 0-1000 rescalonado por faixas de percentil -> KS entre y=1 e y=0.
É *uma* implementação da interface `Metric`, não a única (ver `AUCMetric`).

Bug conhecido do original corrigido aqui: `return(as.numeric(ks_value_1, ks_value_2))`
descarta silenciosamente o segundo argumento — na prática o R sempre otimizava
KS-dev, nunca KS-teste, apesar de calcular os dois. Aqui o critério é explícito
via `criterio` ("dev", "teste" ou "min" — o mínimo dos dois penaliza overfit).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd
from scipy.stats import ks_2samp

from pedro_wise.types import FittedModel

# Quantis fixos usados para definir as quebras de score (fiel ao R original).
QUANTIS_QUEBRA: tuple[float, ...] = (0.0, 0.025, 0.070, 0.150, 0.300, 0.500, 0.700, 0.85, 0.930, 0.975, 1.0)

# (saida_min, saida_max) de cada uma das 10 faixas entre as 11 quebras.
FAIXAS_SAIDA: tuple[tuple[int, int], ...] = (
    (0, 100),
    (101, 200),
    (201, 300),
    (301, 400),
    (401, 500),
    (501, 600),
    (601, 700),
    (701, 800),
    (801, 900),
    (901, 1000),
)

_EPS = 1e-10


def _logit(prob: np.ndarray) -> np.ndarray:
    """`-log(1/p - 1)` no R == logit(p). Clipa para evitar log(0)/divisão por zero."""
    p = np.clip(prob, _EPS, 1.0 - _EPS)
    return np.asarray(np.log(p / (1.0 - p)))


def _score_gaussiano(prob: np.ndarray) -> np.ndarray:
    xbeta = _logit(prob)
    return np.asarray(np.trunc(500.0 + xbeta * (100.0 / np.log(2.0))))


def _rescalonar_por_faixas(score_gauss: np.ndarray, quebras: np.ndarray) -> np.ndarray:
    """Reescala linearmente por faixa, replicando a cadeia if/elif do R.

    `np.select` avalia as condições em ordem e usa a primeira verdadeira —
    equivalente à cadeia `ifelse` aninhada do original.
    """
    condicoes = [score_gauss <= quebras[0]]
    escolhas: list[np.ndarray] = [np.zeros_like(score_gauss)]

    for i in range(10):
        saida_lo, saida_hi = FAIXAS_SAIDA[i]
        quebra_lo, quebra_hi = quebras[i], quebras[i + 1]
        denom = quebra_hi - quebra_lo
        with np.errstate(divide="ignore", invalid="ignore"):
            valor = saida_lo + (score_gauss - quebra_lo) * (saida_hi - saida_lo) / denom
        # Quebras degeneradas (denom==0, ex.: poucos valores distintos) colapsam no piso da faixa.
        valor = np.where(denom == 0, float(saida_lo), valor)
        condicoes.append(score_gauss <= quebra_hi)
        escolhas.append(valor)

    return np.select(condicoes, escolhas, default=1000.0)


def _ks_estatistica(score: np.ndarray, y: np.ndarray) -> float:
    score = np.asarray(score, dtype=float)
    y = np.asarray(y)
    grupo_1 = score[y == 1]
    grupo_0 = score[y == 0]
    if grupo_1.size == 0 or grupo_0.size == 0:
        return 0.0
    return float(ks_2samp(grupo_1, grupo_0).statistic)


@dataclass(frozen=True)
class KSGaussianMetric:
    """KS sobre score Gaussiano 0-1000, fiel ao `calc_ks_score` do R.

    As quebras de percentil são sempre calculadas na base de DEV e aplicadas
    também ao score de TESTE — reproduz a semântica "quebras fixadas no
    desenvolvimento" do original (anti-leakage: teste nunca define suas próprias quebras).
    """

    criterio: Literal["dev", "teste", "min"] = "teste"
    quantis: tuple[float, ...] = QUANTIS_QUEBRA

    def __call__(
        self,
        model: FittedModel,
        X_dev: pd.DataFrame,
        y_dev: pd.Series,
        X_test: pd.DataFrame,
        y_test: pd.Series,
    ) -> float:
        prob_dev = model.predict_proba(X_dev)
        score_gauss_dev = _score_gaussiano(prob_dev)
        quebras = np.quantile(score_gauss_dev, self.quantis)
        score_dev = np.trunc(_rescalonar_por_faixas(score_gauss_dev, quebras))
        ks_dev = _ks_estatistica(score_dev, y_dev.to_numpy())

        prob_test = model.predict_proba(X_test)
        score_gauss_test = _score_gaussiano(prob_test)
        score_test = np.trunc(_rescalonar_por_faixas(score_gauss_test, quebras))
        ks_test = _ks_estatistica(score_test, y_test.to_numpy())

        if self.criterio == "dev":
            return ks_dev
        if self.criterio == "teste":
            return ks_test
        return min(ks_dev, ks_test)


@dataclass(frozen=True)
class AUCMetric:
    """AUC-ROC na base de teste — alternativa mais barata ao KS-Gaussiano,
    útil quando a calibração de score em faixas não é necessária.
    """

    criterio: Literal["dev", "teste", "min"] = "teste"

    def __call__(
        self,
        model: FittedModel,
        X_dev: pd.DataFrame,
        y_dev: pd.Series,
        X_test: pd.DataFrame,
        y_test: pd.Series,
    ) -> float:
        from sklearn.metrics import roc_auc_score

        auc_dev = float(roc_auc_score(y_dev, model.predict_proba(X_dev)))
        auc_test = float(roc_auc_score(y_test, model.predict_proba(X_test)))
        if self.criterio == "dev":
            return auc_dev
        if self.criterio == "teste":
            return auc_test
        return min(auc_dev, auc_test)
