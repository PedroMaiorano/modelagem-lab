"""Teste de equivalência/propriedade do nível 1 (forward/troca/backward simples)
contra o comportamento esperado do `Pedro_Wise_3.0` (R).

Não há `Rscript` neste ambiente para rodar o R original lado a lado — este teste
valida as propriedades que a lógica de seleção original garante por construção:
(1) a variável informativa é escolhida sobre puro ruído, (2) duas versões da
mesma base nunca coexistem no modelo, (3) o score nunca piora entre iterações,
(4) o algoritmo converge (termina o laço).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from pedro_wise.base import extrair_base
from pedro_wise.estimators import LogisticGLM
from pedro_wise.metrics import KSGaussianMetric
from pedro_wise.selection import run_level1
from pedro_wise.types import Level1Config, SelectionState


@pytest.fixture
def dataset_sintetico() -> tuple[pd.DataFrame, pd.DataFrame]:
    """x1_woe é informativo; x1_log é outra versão (mesma base) um pouco mais
    ruidosa; x2_woe/x2_log são puro ruído (base diferente, sem relação com y).
    """
    rng = np.random.default_rng(42)
    n = 1200

    x1 = rng.normal(0, 1, n)
    logit_p = 1.8 * x1
    p = 1 / (1 + np.exp(-logit_p))
    y = rng.binomial(1, p)

    x1_woe = x1
    x1_log = x1 + rng.normal(0, 0.8, n)  # mesma base, versão mais ruidosa
    x2_woe = rng.normal(0, 1, n)  # ruído puro, base "x2"
    x2_log = rng.normal(0, 1, n)  # ruído puro, mesma base "x2"

    df = pd.DataFrame(
        {"y": y, "x1_woe": x1_woe, "x1_log": x1_log, "x2_woe": x2_woe, "x2_log": x2_log}
    )
    metade = n // 2
    return df.iloc[:metade].reset_index(drop=True), df.iloc[metade:].reset_index(drop=True)


def test_forward_simples_prefere_variavel_informativa_sobre_ruido(dataset_sintetico):
    df_dev, df_teste = dataset_sintetico
    estimator = LogisticGLM()
    metric = KSGaussianMetric(criterio="teste")
    estado_inicial = SelectionState(variables=(), model=estimator.fit(df_dev[[]], df_dev["y"]), score=0.0)
    estado_inicial.score = metric(
        estado_inicial.model, df_dev[[]], df_dev["y"], df_teste[[]], df_teste["y"]
    )

    estado_final, trace = run_level1(
        estimator,
        metric,
        df_dev,
        df_teste,
        estado_inicial,
        Level1Config(backward_simples=False, min_vars_para_backward=999),
    )

    # x1_woe (ou x1_log, mesma base) precisa ter entrado — nunca x2_*
    bases_no_modelo = {extrair_base(v) for v in estado_final.variables}
    assert "x1" in bases_no_modelo
    assert estado_final.score > estado_inicial.score
    assert trace.eventos  # alguma atualização foi registrada


def test_nunca_coexistem_duas_versoes_da_mesma_base(dataset_sintetico):
    df_dev, df_teste = dataset_sintetico
    estimator = LogisticGLM()
    metric = KSGaussianMetric(criterio="teste")
    modelo_nulo = estimator.fit(df_dev[[]], df_dev["y"])
    score_nulo = metric(modelo_nulo, df_dev[[]], df_dev["y"], df_teste[[]], df_teste["y"])
    estado_inicial = SelectionState(variables=(), model=modelo_nulo, score=score_nulo)

    estado_final, _ = run_level1(estimator, metric, df_dev, df_teste, estado_inicial)

    bases = [extrair_base(v) for v in estado_final.variables]
    assert len(bases) == len(set(bases)), f"bases duplicadas em {estado_final.variables}"


def test_score_nunca_piora_entre_o_estado_inicial_e_final(dataset_sintetico):
    df_dev, df_teste = dataset_sintetico
    estimator = LogisticGLM()
    metric = KSGaussianMetric(criterio="teste")
    modelo_nulo = estimator.fit(df_dev[[]], df_dev["y"])
    score_nulo = metric(modelo_nulo, df_dev[[]], df_dev["y"], df_teste[[]], df_teste["y"])
    estado_inicial = SelectionState(variables=(), model=modelo_nulo, score=score_nulo)

    estado_final, _ = run_level1(estimator, metric, df_dev, df_teste, estado_inicial)

    assert estado_final.score >= estado_inicial.score


def test_metrica_alternativa_auc_tambem_funciona_no_mesmo_laco(dataset_sintetico):
    """Prova de que a seleção é agnóstica à métrica — troca KS por AUC sem mudar selection.py."""
    from pedro_wise.metrics import AUCMetric

    df_dev, df_teste = dataset_sintetico
    estimator = LogisticGLM()
    metric = AUCMetric(criterio="teste")
    modelo_nulo = estimator.fit(df_dev[[]], df_dev["y"])
    score_nulo = metric(modelo_nulo, df_dev[[]], df_dev["y"], df_teste[[]], df_teste["y"])
    estado_inicial = SelectionState(variables=(), model=modelo_nulo, score=score_nulo)

    estado_final, _ = run_level1(estimator, metric, df_dev, df_teste, estado_inicial)

    assert estado_final.score >= estado_inicial.score
    assert "x1" in {extrair_base(v) for v in estado_final.variables}
