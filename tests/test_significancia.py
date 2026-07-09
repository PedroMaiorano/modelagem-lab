"""Testes do filtro de p-valor (`Level1Config.p_valor_maximo` /
`Level2Config.p_valor_maximo`) — restrição, não critério de otimização: o
KS continua mandando, isto só reduz quais candidatas são elegíveis.

`_passa_significancia`/`_melhor` são testados diretamente (não só via
`run_level1`) porque a lógica em si é pura e determinística — testar via
convergência de um modelo real exigiria manipular ruído estatístico pra
forçar p-valores específicos, bem mais frágil que testar a função isolada.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
import pytest
from pedro_wise.estimators import LogisticGLM
from pedro_wise.metrics import KSGaussianMetric
from pedro_wise.selection import _melhor, _passa_significancia, run_level1
from pedro_wise.types import CandidateResult, Level1Config, SelectionState


@dataclass(frozen=True)
class _ModeloFalso:
    """Stub de FittedModel só com o que `_passa_significancia` precisa —
    não usa LogisticGLM de verdade pra controlar o p-valor exatamente.
    """

    variables: tuple[str, ...]
    p_valores: dict[str, float]

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        raise NotImplementedError

    def estatisticas(self) -> dict[str, dict[str, float]]:
        return {v: {"coeficiente": 1.0, "erro_padrao": 1.0, "p_valor": p} for v, p in self.p_valores.items()}


def test_passa_significancia_aceita_candidata_significativa():
    candidato = CandidateResult(added=("x1",), score=0.5, model=_ModeloFalso(("x1",), {"x1": 0.01}))
    assert _passa_significancia(candidato, p_valor_maximo=0.05) is True


def test_passa_significancia_rejeita_candidata_nao_significativa():
    candidato = CandidateResult(added=("x1",), score=0.5, model=_ModeloFalso(("x1",), {"x1": 0.30}))
    assert _passa_significancia(candidato, p_valor_maximo=0.05) is False


def test_passa_significancia_nunca_filtra_remocao():
    """`added` vazio (candidata de backward, só `removed`) — sempre passa,
    não importa o p-valor de quem ficou no modelo."""
    candidato = CandidateResult(removed=("x1",), score=0.5, model=_ModeloFalso((), {}))
    assert _passa_significancia(candidato, p_valor_maximo=1e-9) is True


def test_passa_significancia_todas_as_variaveis_adicionadas_devem_passar():
    """forward_duplo/triplo adicionam >1 variável de uma vez — todas
    precisam ser significativas, não basta uma."""
    modelo = _ModeloFalso(("a", "b"), {"a": 0.01, "b": 0.30})
    candidato = CandidateResult(added=("a", "b"), score=0.5, model=modelo)
    assert _passa_significancia(candidato, p_valor_maximo=0.05) is False


def test_melhor_com_p_valor_maximo_pula_candidata_nao_significativa():
    fraca_mas_significativa = CandidateResult(
        added=("x1",), score=0.3, model=_ModeloFalso(("x1",), {"x1": 0.01})
    )
    forte_mas_nao_significativa = CandidateResult(
        added=("x2",), score=0.9, model=_ModeloFalso(("x2",), {"x2": 0.50})
    )
    # sem filtro, vence quem tem maior score (x2)
    sem_filtro = _melhor([fraca_mas_significativa, forte_mas_nao_significativa])
    assert sem_filtro is not None
    assert sem_filtro.added == ("x2",)
    # com filtro, x2 é descartada por p-valor e x1 vence por ser a única elegível
    resultado = _melhor([fraca_mas_significativa, forte_mas_nao_significativa], p_valor_maximo=0.05)
    assert resultado is not None
    assert resultado.added == ("x1",)


def test_melhor_retorna_none_se_nenhuma_candidata_passa():
    candidato = CandidateResult(added=("x1",), score=0.9, model=_ModeloFalso(("x1",), {"x1": 0.99}))
    assert _melhor([candidato], p_valor_maximo=0.05) is None


@pytest.fixture
def dataset_com_preditor_real() -> tuple[pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(7)
    n = 1000
    x1 = rng.normal(0, 1, n)
    p = 1 / (1 + np.exp(-2.5 * x1))
    y = rng.binomial(1, p)
    df = pd.DataFrame({"y": y, "x1_woe": x1})
    corte = int(n * 0.7)
    return df.iloc[:corte].reset_index(drop=True), df.iloc[corte:].reset_index(drop=True)


def test_p_valor_maximo_impossivel_bloqueia_toda_entrada(dataset_com_preditor_real):
    """Integração ponta a ponta via run_level1: um limiar impossível
    (praticamente 0) deve impedir QUALQUER variável de entrar, mesmo uma
    preditora forte — confirma que a config chega até o laço de verdade."""
    df_dev, df_teste = dataset_com_preditor_real
    estimator = LogisticGLM()
    metric = KSGaussianMetric(criterio="teste")
    modelo_nulo = estimator.fit(df_dev[[]], df_dev["y"])
    score_nulo = metric(modelo_nulo, df_dev[[]], df_dev["y"], df_teste[[]], df_teste["y"])
    estado_inicial = SelectionState(variables=(), model=modelo_nulo, score=score_nulo)

    config = Level1Config(p_valor_maximo=1e-300)
    estado_final, _ = run_level1(estimator, metric, df_dev, df_teste, estado_inicial, config)
    assert estado_final.variables == ()


def test_p_valor_maximo_none_nao_muda_comportamento(dataset_com_preditor_real):
    df_dev, df_teste = dataset_com_preditor_real
    estimator = LogisticGLM()
    metric = KSGaussianMetric(criterio="teste")
    modelo_nulo = estimator.fit(df_dev[[]], df_dev["y"])
    score_nulo = metric(modelo_nulo, df_dev[[]], df_dev["y"], df_teste[[]], df_teste["y"])
    estado_inicial = SelectionState(variables=(), model=modelo_nulo, score=score_nulo)

    config = Level1Config(p_valor_maximo=None)
    estado_final, _ = run_level1(estimator, metric, df_dev, df_teste, estado_inicial, config)
    assert "x1_woe" in estado_final.variables
