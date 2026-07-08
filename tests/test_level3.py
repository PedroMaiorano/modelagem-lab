"""Testes do nível 3 (backward complexo recursivo).

Sem `Rscript` neste ambiente (mesma limitação documentada em test_metrics.py).
Foco: as garantias que a versão Python adiciona sobre o original — nunca piora,
termina (profundidade limitada), memoização evita recomputar o mesmo ramo, e
desligado por padrão (`Level3Config().ativado is False`, espelhando o próprio
script R que rodava com `backward_complexo_nivel_3 = FALSE`).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from pedro_wise.estimators import LogisticGLM
from pedro_wise.level3 import run_pedro_wise_completo
from pedro_wise.metrics import KSGaussianMetric
from pedro_wise.pipeline import run_pedro_wise
from pedro_wise.types import Level1Config, Level3Config, SelectionState


@pytest.fixture
def dataset_redundante() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Várias variáveis fracas e parcialmente redundantes entre si (mesmo
    fator latente com ruídos diferentes) — cenário em que remover uma variável
    e re-buscar do zero pode achar uma combinação melhor do que a gulosa pura.
    """
    rng = np.random.default_rng(21)
    n = 1200
    u = rng.normal(0, 1, n)

    cols = {}
    for i in range(6):
        cols[f"v{i}_woe"] = u + rng.normal(0, 1.3, n)

    logit_p = 1.3 * u
    p = 1 / (1 + np.exp(-logit_p))
    y = rng.binomial(1, p)

    df = pd.DataFrame({"y": y, **cols})
    metade = n // 2
    return df.iloc[:metade].reset_index(drop=True), df.iloc[metade:].reset_index(drop=True)


def _estado_nulo(estimator, metric, df_dev, df_teste):
    modelo_nulo = estimator.fit(df_dev[[]], df_dev["y"])
    score_nulo = metric(modelo_nulo, df_dev[[]], df_dev["y"], df_teste[[]], df_teste["y"])
    return SelectionState(variables=(), model=modelo_nulo, score=score_nulo)


def test_level3_desligado_por_padrao():
    assert Level3Config().ativado is False


def test_level3_nunca_piora_e_e_pelo_menos_tao_bom_quanto_pipeline_sem_nivel3(dataset_redundante):
    df_dev, df_teste = dataset_redundante
    estimator = LogisticGLM()
    metric = KSGaussianMetric(criterio="teste")
    config1 = Level1Config(min_vars_para_backward=2)

    estado_sem_l3, _ = run_pedro_wise(
        estimator, metric, df_dev, df_teste, _estado_nulo(estimator, metric, df_dev, df_teste), config1
    )
    estado_com_l3, trace = run_pedro_wise_completo(
        estimator,
        metric,
        df_dev,
        df_teste,
        _estado_nulo(estimator, metric, df_dev, df_teste),
        config1=config1,
        config3=Level3Config(ativado=True, n_best_backward=2, profundidade_maxima=1),
    )

    assert estado_com_l3.score >= estado_sem_l3.score
    assert isinstance(trace.eventos, list)


def test_level3_respeita_profundidade_maxima(dataset_redundante):
    """Com profundidade_maxima=0, nível 3 nunca chega a recursar — resultado
    idêntico a rodar só níveis 1/2/2.5.
    """
    df_dev, df_teste = dataset_redundante
    estimator = LogisticGLM()
    metric = KSGaussianMetric(criterio="teste")
    config1 = Level1Config(min_vars_para_backward=2)

    estado_sem_l3, _ = run_pedro_wise(
        estimator, metric, df_dev, df_teste, _estado_nulo(estimator, metric, df_dev, df_teste), config1
    )
    estado_profundidade_zero, _ = run_pedro_wise_completo(
        estimator,
        metric,
        df_dev,
        df_teste,
        _estado_nulo(estimator, metric, df_dev, df_teste),
        config1=config1,
        config3=Level3Config(ativado=True, n_best_backward=2, profundidade_maxima=0),
    )

    assert estado_profundidade_zero.score == pytest.approx(estado_sem_l3.score)
    assert set(estado_profundidade_zero.variables) == set(estado_sem_l3.variables)


def test_level3_memoiza_ramos_repetidos(dataset_redundante):
    """Chama a busca duas vezes com o mesmo cache; a segunda não deve recomputar
    nenhum ramo novo (dict de cache não cresce).
    """
    df_dev, df_teste = dataset_redundante
    estimator = LogisticGLM()
    metric = KSGaussianMetric(criterio="teste")
    config1 = Level1Config(min_vars_para_backward=2)
    config3 = Level3Config(ativado=True, n_best_backward=2, profundidade_maxima=1)
    cache: dict = {}

    run_pedro_wise_completo(
        estimator,
        metric,
        df_dev,
        df_teste,
        _estado_nulo(estimator, metric, df_dev, df_teste),
        config1=config1,
        config3=config3,
        cache=cache,
    )
    tamanho_apos_primeira = len(cache)
    assert tamanho_apos_primeira > 0

    run_pedro_wise_completo(
        estimator,
        metric,
        df_dev,
        df_teste,
        _estado_nulo(estimator, metric, df_dev, df_teste),
        config1=config1,
        config3=config3,
        cache=cache,
    )
    assert len(cache) == tamanho_apos_primeira
