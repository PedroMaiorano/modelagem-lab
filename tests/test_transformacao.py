"""Testes do módulo de transformação (WOE/IV)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from transformacao import ajustar_woe, aplicar_woe, classificar_iv


def test_woe_bate_com_calculo_manual():
    """2 bins, contagens redondas, sem suavização — confere a fórmula
    WOE = ln(%não-evento / %evento) contra conta feita à mão.
    """
    # bin 0: 80 não-evento, 20 evento | bin 1: 20 não-evento, 80 evento
    bin_idx = pd.Series([0] * 100 + [1] * 100)
    y = pd.Series([0] * 80 + [1] * 20 + [0] * 20 + [1] * 80)

    tabela = ajustar_woe(bin_idx, y, suavizacao=0.0)

    total_evento, total_nao_evento = 100, 100
    prop_evento_0, prop_nao_evento_0 = 20 / total_evento, 80 / total_nao_evento
    woe_0_esperado = np.log(prop_nao_evento_0 / prop_evento_0)

    assert tabela.woe_por_bin[0] == pytest.approx(woe_0_esperado)
    assert tabela.woe_por_bin[0] > 0  # mais não-evento que evento -> WOE positivo (convenção Siddiqi)
    assert tabela.woe_por_bin[1] < 0  # simétrico: mais evento -> WOE negativo
    assert tabela.woe_por_bin[0] == pytest.approx(-tabela.woe_por_bin[1])  # simetria do exemplo


def test_iv_total_e_soma_dos_parciais():
    bin_idx = pd.Series([0] * 100 + [1] * 100 + [2] * 100)
    y = pd.Series([0] * 90 + [1] * 10 + [0] * 50 + [1] * 50 + [0] * 10 + [1] * 90)

    tabela = ajustar_woe(bin_idx, y)

    assert tabela.iv_total == pytest.approx(tabela.resumo["iv_parcial"].sum())
    assert tabela.iv_total > 0  # sinal real presente (bins bem diferentes) -> IV positivo


def test_bin_sem_ruido_da_iv_proximo_de_zero():
    """Se a taxa de evento é igual em todos os bins, o bin não carrega
    informação -> IV deve ficar perto de zero.
    """
    rng = np.random.default_rng(0)
    n = 5000
    bin_idx = pd.Series(rng.integers(0, 5, n))
    y = pd.Series(rng.binomial(1, 0.3, n))  # y independente do bin

    tabela = ajustar_woe(bin_idx, y)
    assert tabela.iv_total < 0.02  # "sem poder preditivo" pela régua de classificar_iv


def test_suavizacao_evita_infinito_com_bin_de_zero_eventos(caplog):
    bin_idx = pd.Series([0] * 50 + [1] * 50)
    y = pd.Series([0] * 50 + [0] * 40 + [1] * 10)  # bin 0 tem ZERO eventos

    tabela = ajustar_woe(bin_idx, y, suavizacao=0.5)

    assert np.isfinite(tabela.woe_por_bin).all()
    assert "contagem zero" in caplog.text


def test_ajustar_woe_rejeita_y_nao_binario():
    bin_idx = pd.Series([0, 0, 1, 1])
    y = pd.Series([0, 1, 2, 1])
    with pytest.raises(ValueError, match="binário"):
        ajustar_woe(bin_idx, y)


def test_aplicar_woe_sem_vazamento_treino_teste():
    """Ajusta no 'dev', aplica no 'teste' com uma categoria nova (não vista
    no dev) — não deve levantar erro, deve mapear para WOE=0 (neutro).
    """
    bin_dev = pd.Series([0] * 100 + [1] * 100)
    y_dev = pd.Series([0] * 80 + [1] * 20 + [0] * 20 + [1] * 80)
    tabela = ajustar_woe(bin_dev, y_dev)

    bin_teste = pd.Series([0, 1, 2, 2])  # bin 2 nunca apareceu no dev
    woe_teste = aplicar_woe(bin_teste, tabela)

    assert woe_teste.iloc[0] == pytest.approx(tabela.woe_por_bin[0])
    assert woe_teste.iloc[1] == pytest.approx(tabela.woe_por_bin[1])
    assert woe_teste.iloc[2] == 0.0
    assert woe_teste.iloc[3] == 0.0


@pytest.mark.parametrize(
    ("iv", "esperado"),
    [
        (0.01, "sem poder preditivo"),
        (0.05, "fraco"),
        (0.2, "médio"),
        (0.4, "forte"),
        (0.6, "suspeito (possível vazamento)"),
    ],
)
def test_classificar_iv(iv, esperado):
    assert classificar_iv(iv) == esperado
