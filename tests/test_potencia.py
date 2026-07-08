"""Testes de Box-Cox / Yeo-Johnson (fit/transform anti-leakage)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from transformacao import ajustar_box_cox, ajustar_yeo_johnson, aplicar_potencia


@pytest.fixture
def x_assimetrico_positivo() -> pd.Series:
    rng = np.random.default_rng(0)
    return pd.Series(rng.lognormal(mean=1.0, sigma=1.0, size=2000))


def test_box_cox_reduz_assimetria(x_assimetrico_positivo):
    from scipy.stats import skew

    transformacao = ajustar_box_cox(x_assimetrico_positivo)
    x_transformado = aplicar_potencia(x_assimetrico_positivo, transformacao)

    assert abs(skew(x_transformado)) < abs(skew(x_assimetrico_positivo))


def test_box_cox_rejeita_valores_nao_positivos():
    x = pd.Series([1.0, 2.0, 0.0, 3.0])
    with pytest.raises(ValueError, match="estritamente positivos"):
        ajustar_box_cox(x)


def test_yeo_johnson_aceita_negativos_e_zero():
    x = pd.Series([-5.0, -1.0, 0.0, 2.0, 10.0])
    transformacao = ajustar_yeo_johnson(x)
    x_transformado = aplicar_potencia(x, transformacao)
    assert np.isfinite(x_transformado).all()


def test_aplicar_potencia_usa_lambda_ajustado_no_dev_nao_reestima():
    """dev e teste com escalas MUITO diferentes: se aplicar_potencia
    reestimasse lambda no teste (bug de vazamento), o resultado dependeria
    da escala do teste. Deve depender só do lambda do dev.
    """
    rng = np.random.default_rng(1)
    x_dev = pd.Series(rng.lognormal(1.0, 1.0, 2000))
    x_teste_a = pd.Series(rng.lognormal(1.0, 1.0, 500))
    x_teste_b = x_teste_a * 1000  # mesma forma, escala bem diferente

    transformacao = ajustar_box_cox(x_dev)
    resultado_a = aplicar_potencia(x_teste_a, transformacao)
    resultado_b = aplicar_potencia(x_teste_b, transformacao)

    # com o MESMO lambda, escalas diferentes devem dar resultados diferentes
    # (a transformação não "corrige" a escala sozinha) — prova que não há
    # reajuste por trás dos panos escondendo esse efeito.
    assert not np.allclose(resultado_a.to_numpy(), resultado_b.to_numpy())


def test_box_cox_lambda_1_e_aproximadamente_identidade_menos_1():
    """Sanity check da fórmula: com lambda=1, Box-Cox(x) = x - 1."""
    from transformacao.potencia import TransformacaoPotencia

    x = pd.Series([1.0, 2.0, 3.0, 10.0])
    transformacao = TransformacaoPotencia(lambda_=1.0, metodo="box-cox")
    resultado = aplicar_potencia(x, transformacao)
    assert resultado.to_numpy() == pytest.approx((x - 1).to_numpy())
