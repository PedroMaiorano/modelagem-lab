"""Teste do orquestrador completo (nível 1 <-> nível 2 <-> nível 2.5).

Sem `Rscript` neste ambiente — validamos as propriedades que o laço principal
do R garante por construção: nunca piora, sempre termina, e o resultado é pelo
menos tão bom quanto rodar só o nível 1.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from pedro_wise.estimators import LogisticGLM
from pedro_wise.metrics import KSGaussianMetric
from pedro_wise.pipeline import run_pedro_wise
from pedro_wise.selection import run_level1
from pedro_wise.types import Level1Config, Level2Config, SelectionState


@pytest.fixture
def dataset_misto() -> tuple[pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(11)
    n = 1500

    u = rng.normal(0, 1, n)
    xa_woe = u + rng.normal(0, 1.5, n)
    xb_woe = u + rng.normal(0, 1.5, n)
    x1_woe = rng.normal(0, 1, n)
    logit_p_x1 = 1.2 * x1_woe
    x1_log = x1_woe + rng.normal(0, 0.8, n)
    x_ruido_woe = rng.normal(0, 1, n)
    x_ruido_log = rng.normal(0, 1, n)

    logit_p = 1.4 * u + logit_p_x1
    p = 1 / (1 + np.exp(-logit_p))
    y = rng.binomial(1, p)

    df = pd.DataFrame(
        {
            "y": y,
            "xa_woe": xa_woe,
            "xb_woe": xb_woe,
            "x1_woe": x1_woe,
            "x1_log": x1_log,
            "x_ruido_woe": x_ruido_woe,
            "x_ruido_log": x_ruido_log,
        }
    )
    metade = n // 2
    return df.iloc[:metade].reset_index(drop=True), df.iloc[metade:].reset_index(drop=True)


def _estado_nulo(estimator, metric, df_dev, df_teste):
    modelo_nulo = estimator.fit(df_dev[[]], df_dev["y"])
    score_nulo = metric(modelo_nulo, df_dev[[]], df_dev["y"], df_teste[[]], df_teste["y"])
    return SelectionState(variables=(), model=modelo_nulo, score=score_nulo)


def test_pipeline_termina_e_nunca_piora(dataset_misto):
    df_dev, df_teste = dataset_misto
    estimator = LogisticGLM()
    metric = KSGaussianMetric(criterio="teste")
    estado_inicial = _estado_nulo(estimator, metric, df_dev, df_teste)

    estado_final, trace = run_pedro_wise(estimator, metric, df_dev, df_teste, estado_inicial)

    assert estado_final.score >= estado_inicial.score
    assert isinstance(trace.eventos, list)


def test_pipeline_e_pelo_menos_tao_bom_quanto_nivel1_sozinho(dataset_misto):
    df_dev, df_teste = dataset_misto
    estimator = LogisticGLM()
    metric = KSGaussianMetric(criterio="teste")

    estado_inicial_l1 = _estado_nulo(estimator, metric, df_dev, df_teste)
    estado_l1, _ = run_level1(estimator, metric, df_dev, df_teste, estado_inicial_l1)
    estado_pipeline, _ = run_pedro_wise(
        estimator, metric, df_dev, df_teste, _estado_nulo(estimator, metric, df_dev, df_teste)
    )

    assert estado_pipeline.score >= estado_l1.score


def test_pipeline_respeita_config_desligando_niveis_2_e_25(dataset_misto):
    """Com forward_duplo e forward_triplo desligados, o pipeline se comporta
    como nível 1 puro (mesmo resultado, sem escalar).
    """
    df_dev, df_teste = dataset_misto
    estimator = LogisticGLM()
    metric = KSGaussianMetric(criterio="teste")
    config2_desligado = Level2Config(forward_duplo=False, forward_triplo=False)

    estado_inicial_l1 = _estado_nulo(estimator, metric, df_dev, df_teste)
    estado_l1, _ = run_level1(estimator, metric, df_dev, df_teste, estado_inicial_l1)
    estado_pipeline, _ = run_pedro_wise(
        estimator,
        metric,
        df_dev,
        df_teste,
        _estado_nulo(estimator, metric, df_dev, df_teste),
        config1=Level1Config(),
        config2=config2_desligado,
    )

    assert estado_pipeline.score == pytest.approx(estado_l1.score)
    assert set(estado_pipeline.variables) == set(estado_l1.variables)
