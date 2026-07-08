"""Testes do nível 2 (forward duplo) e 2.5 (forward triplo).

Sem `Rscript` neste ambiente (mesma limitação documentada em test_metrics.py),
então validamos propriedades estruturais: semântica de base preservada nas
combinações, respeito aos limites n_best_*, e um cenário de "par sinérgico"
onde adicionar duas variáveis correlacionadas ao mesmo hidden factor junto
supera qualquer adição individual — o caso de uso central do forward duplo.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from pedro_wise.base import extrair_base
from pedro_wise.estimators import LogisticGLM
from pedro_wise.level2 import forward_duplo, forward_triplo
from pedro_wise.metrics import KSGaussianMetric


@pytest.fixture
def dataset_par_sinergico() -> tuple[pd.DataFrame, pd.DataFrame]:
    """u é um fator latente não observado. xa_woe e xb_woe são proxies ruidosas
    de u (bases diferentes). y depende de u -> nenhuma das duas sozinha separa
    tão bem quanto as duas juntas (proxies parcialmente independentes de u).
    x_ruido_woe é puro ruído, sem relação com y ou com u.
    """
    rng = np.random.default_rng(7)
    n = 2000

    u = rng.normal(0, 1, n)
    xa_woe = u + rng.normal(0, 1.5, n)
    xb_woe = u + rng.normal(0, 1.5, n)
    x_ruido_woe = rng.normal(0, 1, n)

    logit_p = 1.6 * u
    p = 1 / (1 + np.exp(-logit_p))
    y = rng.binomial(1, p)

    df = pd.DataFrame({"y": y, "xa_woe": xa_woe, "xb_woe": xb_woe, "x_ruido_woe": x_ruido_woe})
    metade = n // 2
    return df.iloc[:metade].reset_index(drop=True), df.iloc[metade:].reset_index(drop=True)


def test_forward_duplo_encontra_par_sinergico_melhor_que_qualquer_single(dataset_par_sinergico):
    df_dev, df_teste = dataset_par_sinergico
    estimator = LogisticGLM()
    metric = KSGaussianMetric(criterio="teste")

    from pedro_wise.selection import forward_simples

    singles = forward_simples(estimator, metric, df_dev, df_teste, (), n_jobs=1)
    melhor_single = max(singles, key=lambda c: c.score)

    duplos = forward_duplo(estimator, metric, df_dev, df_teste, (), n_best_duplo=3, n_jobs=1)
    melhor_duplo = max(duplos, key=lambda c: c.score)

    assert melhor_duplo.score > melhor_single.score
    assert set(melhor_duplo.added) == {"xa_woe", "xb_woe"}


def test_forward_duplo_nunca_combina_duas_versoes_da_mesma_base(dataset_par_sinergico):
    df_dev, df_teste = dataset_par_sinergico
    estimator = LogisticGLM()
    metric = KSGaussianMetric(criterio="teste")

    duplos = forward_duplo(estimator, metric, df_dev, df_teste, (), n_best_duplo=3, n_jobs=1)
    assert duplos
    for c in duplos:
        bases = [extrair_base(v) for v in c.added]
        assert len(bases) == len(set(bases))


def test_forward_duplo_respeita_n_best_duplo(dataset_par_sinergico):
    df_dev, df_teste = dataset_par_sinergico
    estimator = LogisticGLM()
    metric = KSGaussianMetric(criterio="teste")

    duplos_amplo = forward_duplo(estimator, metric, df_dev, df_teste, (), n_best_duplo=3, n_jobs=1)
    duplos_estreito = forward_duplo(estimator, metric, df_dev, df_teste, (), n_best_duplo=1, n_jobs=1)

    # com n_best_duplo=1, só a melhor candidata single vira "var1" -> menos pares testados
    assert len(duplos_estreito) <= len(duplos_amplo)


def test_forward_triplo_gera_triplas_com_bases_distintas(dataset_par_sinergico):
    df_dev, df_teste = dataset_par_sinergico
    estimator = LogisticGLM()
    metric = KSGaussianMetric(criterio="teste")

    triplas = forward_triplo(
        estimator,
        metric,
        df_dev,
        df_teste,
        (),
        n_best_duplo=3,
        n_best_triplo_1=2,
        n_best_triplo_2=2,
        n_jobs=1,
    )
    assert triplas
    for c in triplas:
        assert len(c.added) == 3
        bases = [extrair_base(v) for v in c.added]
        assert len(bases) == len(set(bases))
