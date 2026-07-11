"""Testes de normalização de safra em formatos heterogêneos."""

from __future__ import annotations

import pandas as pd
import pytest
from agregacao_temporal import normalizar_safra


def test_anomes_inteiro():
    serie = pd.Series([202401, 202412])
    assert normalizar_safra(serie).tolist() == [202401, 202412]


def test_anomes_string():
    serie = pd.Series(["202401", "202412"])
    assert normalizar_safra(serie).tolist() == [202401, 202412]


def test_ano_mes_com_hifen():
    serie = pd.Series(["2024-01", "2024-12"])
    assert normalizar_safra(serie).tolist() == [202401, 202412]


def test_ano_mes_dia():
    serie = pd.Series(["2024-01-15", "2024-12-31"])
    assert normalizar_safra(serie).tolist() == [202401, 202412]


def test_timestamp_pandas():
    serie = pd.Series(pd.to_datetime(["2024-01-15", "2024-12-01"]))
    assert normalizar_safra(serie).tolist() == [202401, 202412]


def test_formatos_mistos_na_mesma_serie():
    """Cenário real citado: fontes diferentes do mesmo painel trazem safra
    em formatos diferentes -- precisa normalizar pra comparar/ordenar junto.
    """
    serie = pd.Series(["202401", "2024-02", "2024-03-15"])
    assert normalizar_safra(serie).tolist() == [202401, 202402, 202403]


def test_formato_invalido_levanta_erro_claro():
    serie = pd.Series(["não é uma data"])
    with pytest.raises(ValueError, match="não reconhecido"):
        normalizar_safra(serie)


def test_resultado_e_ordenavel_apos_normalizacao():
    painel = pd.DataFrame({"safra": ["2024-03", "202401", "2024-02-10"]})
    painel["safra_norm"] = normalizar_safra(painel["safra"])
    ordenado = painel.sort_values("safra_norm")["safra_norm"].tolist()
    assert ordenado == [202401, 202402, 202403]
