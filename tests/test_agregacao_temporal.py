"""Testes das primitivas de agregação temporal (janela móvel por chave)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from agregacao_temporal import construir_agregados_janela, extrair_base_agregado
from agregacao_temporal.primitivas import _slope


def _painel(valores: dict[str, list[float]]) -> pd.DataFrame:
    """Monta um painel de duas chaves com o mesmo número de meses cada."""
    linhas = []
    for chave, serie in valores.items():
        for mes, v in enumerate(serie, start=1):
            linhas.append({"contrato": chave, "mes": mes, "atraso": v})
    return pd.DataFrame(linhas)


def test_maximo_e_media_janela_basico():
    painel = _painel({"A": [0, 10, 5, 30, 2]})
    resultado = construir_agregados_janela(painel, "contrato", "mes", "atraso", janelas=[3])

    assert resultado["atraso_maximo_3m"].tolist() == [0, 10, 10, 30, 30]
    assert resultado["atraso_media_3m"].tolist() == pytest.approx([0, 5, 5, 15, 37 / 3])


def test_janela_incompleta_no_inicio_usa_o_que_existe():
    """min_periods=1: no primeiro mês, a janela de 3 meses só tem 1 observação
    — não deve virar NaN, deve refletir a própria observação.
    """
    painel = _painel({"A": [7, 8]})
    resultado = construir_agregados_janela(painel, "contrato", "mes", "atraso", janelas=[3])

    assert resultado["atraso_maximo_3m"].iloc[0] == 7
    assert resultado["atraso_minimo_3m"].iloc[0] == 7
    assert resultado["atraso_desvio_padrao_3m"].iloc[0] == 0.0


def test_nunca_olha_para_o_futuro_da_mesma_chave():
    """Bug possível: se a janela olhasse o painel inteiro em vez de só até o
    tempo corrente, o máximo no mês 1 incluiria o pico do mês 4 (leakage).
    """
    painel = _painel({"A": [1, 1, 1, 99, 1]})
    resultado = construir_agregados_janela(painel, "contrato", "mes", "atraso", janelas=[3])

    assert resultado["atraso_maximo_3m"].iloc[0] == 1  # mês 1 não pode ver o 99 do mês 4
    assert resultado["atraso_maximo_3m"].iloc[3] == 99  # mês 4 já vê o próprio pico
    assert resultado["atraso_maximo_3m"].iloc[4] == 99  # mês 5 ainda vê o pico dentro da janela de 3


def test_chaves_diferentes_nao_vazam_uma_na_outra():
    painel = _painel({"A": [0, 0, 0], "B": [100, 100, 100]})
    resultado = construir_agregados_janela(painel, "contrato", "mes", "atraso", janelas=[3])

    assert (resultado.loc[resultado["contrato"] == "A", "atraso_maximo_3m"] == 0).all()
    assert (resultado.loc[resultado["contrato"] == "B", "atraso_maximo_3m"] == 100).all()


def test_tendencia_positiva_para_serie_crescente_e_negativa_para_decrescente():
    crescente = construir_agregados_janela(
        _painel({"A": [0, 5, 10, 15]}), "contrato", "mes", "atraso", janelas=[4]
    )
    decrescente = construir_agregados_janela(
        _painel({"A": [15, 10, 5, 0]}), "contrato", "mes", "atraso", janelas=[4]
    )

    assert crescente["atraso_tendencia_4m"].iloc[-1] > 0
    assert decrescente["atraso_tendencia_4m"].iloc[-1] < 0


def test_slope_serie_constante_e_zero():
    assert _slope(np.array([5.0, 5.0, 5.0])) == 0.0


def test_slope_ponto_unico_e_zero_sem_erro():
    assert _slope(np.array([5.0])) == 0.0


def test_seleciona_apenas_primitivas_pedidas():
    painel = _painel({"A": [1, 2, 3]})
    resultado = construir_agregados_janela(
        painel, "contrato", "mes", "atraso", janelas=[3], primitivas=("maximo",)
    )

    assert "atraso_maximo_3m" in resultado.columns
    assert "atraso_media_3m" not in resultado.columns
    assert "atraso_tendencia_3m" not in resultado.columns


def test_multiplas_janelas_geram_colunas_independentes():
    painel = _painel({"A": [1, 2, 3, 4, 5, 6]})
    resultado = construir_agregados_janela(painel, "contrato", "mes", "atraso", janelas=[3, 6])

    assert "atraso_maximo_3m" in resultado.columns
    assert "atraso_maximo_6m" in resultado.columns
    assert resultado["atraso_maximo_3m"].iloc[-1] == 6  # só últimos 3 meses
    assert resultado["atraso_maximo_6m"].iloc[-1] == 6  # janela cobre tudo, mesmo valor aqui


def test_coluna_ausente_levanta_erro_claro():
    painel = pd.DataFrame({"contrato": ["A"], "mes": [1]})
    with pytest.raises(ValueError, match="atraso"):
        construir_agregados_janela(painel, "contrato", "mes", "atraso", janelas=[3])


def test_nao_modifica_painel_original():
    painel = _painel({"A": [1, 2, 3]})
    colunas_antes = list(painel.columns)
    construir_agregados_janela(painel, "contrato", "mes", "atraso", janelas=[3])
    assert list(painel.columns) == colunas_antes


def test_extrair_base_agregado_reverte_a_convencao_de_nomes():
    assert extrair_base_agregado("dias_atraso_tendencia_3m") == "dias_atraso"
    assert extrair_base_agregado("renda_maximo_12m") == "renda"
    assert extrair_base_agregado("saldo_devedor_desvio_padrao_6m") == "saldo_devedor"


def test_extrair_base_agregado_coluna_sem_sufixo_volta_igual():
    assert extrair_base_agregado("renda") == "renda"
    assert extrair_base_agregado("dias_atraso") == "dias_atraso"
