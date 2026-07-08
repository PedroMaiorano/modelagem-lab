"""Testes do módulo de categorização (binning)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from categorizacao import (
    aplicar_bins,
    bins_arvore,
    bins_frequencia_igual,
    bins_largura_igual,
    bins_monotonicos,
)


@pytest.fixture
def x_y_monotonico() -> tuple[pd.Series, pd.Series]:
    """x contínuo com relação monotônica crescente clara com y (via prob)."""
    rng = np.random.default_rng(0)
    n = 3000
    x = rng.uniform(0, 100, n)
    p = 1 / (1 + np.exp(-(x - 50) / 10))
    y = rng.binomial(1, p)
    return pd.Series(x, name="x"), pd.Series(y, name="y")


def test_bins_largura_igual_cobre_o_intervalo_todo(x_y_monotonico):
    x, _ = x_y_monotonico
    edges = bins_largura_igual(x, n_bins=5)
    assert len(edges) == 6
    assert edges[0] <= x.min()
    assert edges[-1] >= x.max()
    assert np.allclose(np.diff(edges), np.diff(edges)[0])  # largura constante


def test_bins_frequencia_igual_da_contagem_aproximadamente_igual(x_y_monotonico):
    x, _ = x_y_monotonico
    edges = bins_frequencia_igual(x, n_bins=5)
    bin_idx = aplicar_bins(x, edges)
    contagens = bin_idx.value_counts().sort_index()
    # tolerância generosa: quantis podem não ser perfeitamente iguais com duplicatas
    assert contagens.std() / contagens.mean() < 0.1


def test_bins_arvore_produz_quebras_dentro_do_dominio(x_y_monotonico):
    x, y = x_y_monotonico
    edges = bins_arvore(x, y, max_folhas=5, min_amostras_folha=100)
    assert edges[0] <= x.min()
    assert edges[-1] >= x.max()
    assert len(edges) >= 2


def test_bins_monotonicos_produz_taxa_de_evento_monotonica(x_y_monotonico):
    x, y = x_y_monotonico
    resultado = bins_monotonicos(x, y, n_bins_inicial=20)
    taxas = resultado.taxa_evento_por_bin
    assert len(taxas) >= 2
    assert np.all(np.diff(taxas) >= -1e-9) or np.all(np.diff(taxas) <= 1e-9)


def test_bins_monotonicos_com_ruido_puro_colapsa_bastante(x_y_monotonico):
    """Sem relação real entre x e y, forçar monotonicidade deve exigir muitos
    merges (a taxa de evento oscila por acaso amostral sem tendência real).
    """
    rng = np.random.default_rng(1)
    n = 2000
    x = pd.Series(rng.uniform(0, 100, n))
    y = pd.Series(rng.binomial(1, 0.2, n))  # y independente de x

    resultado = bins_monotonicos(x, y, n_bins_inicial=20)
    assert resultado.n_merges > 0
    assert len(resultado.taxa_evento_por_bin) < 20


def test_aplicar_bins_cobre_todos_os_valores_sem_nulos(x_y_monotonico):
    x, _ = x_y_monotonico
    edges = bins_frequencia_igual(x, n_bins=8)
    bin_idx = aplicar_bins(x, edges)
    assert bin_idx.isna().sum() == 0
    assert bin_idx.min() >= 0
    assert bin_idx.max() < len(edges) - 1 + 1  # último bin válido


def test_aplicar_bins_lida_com_valores_fora_do_range_de_ajuste(x_y_monotonico):
    """edges vindas de um dataset de treino aplicadas a um novo x com valores
    fora do range original (comum entre dev/teste) não devem gerar NaN.
    """
    x, _ = x_y_monotonico
    edges = bins_frequencia_igual(x.iloc[:1000], n_bins=5)  # edges de uma subamostra
    bin_idx = aplicar_bins(x, edges)  # aplicado no x inteiro (pode extrapolar)
    assert bin_idx.isna().sum() == 0
