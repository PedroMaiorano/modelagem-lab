"""Testes de python/pipeline_lab -- funções soltas que montam o funil
completo (divisão → esfera 1 → esfera 2 → categorização → treinamento) em
cima de um DataFrame qualquer, sem disco/FastAPI.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from pipeline_lab import categorizar, divisao, esfera1, esfera2, treinamento


def test_dividir_por_amostra_aceita_rotulos_arbitrarios() -> None:
    df = pd.DataFrame(
        {
            "amostra": ["DES", "DES", "OOT", "OOT", "validacao"],
            "x": [1, 2, 3, 4, 5],
            "y": [0, 1, 0, 1, 1],
        }
    )
    dev, teste = divisao.dividir_por_amostra(df, "amostra", valores_dev=["DES"], valores_teste=["OOT"])
    assert len(dev) == 2
    assert len(teste) == 2
    assert "validacao" not in dev["amostra"].tolist() + teste["amostra"].tolist()


def test_dividir_por_amostra_split_vazio_leva_erro() -> None:
    df = pd.DataFrame({"amostra": ["DES"] * 5, "y": [0, 1, 0, 1, 0]})
    with pytest.raises(ValueError):
        divisao.dividir_por_amostra(df, "amostra", valores_dev=["DES"], valores_teste=["OOT"])


def test_dividir_aleatorio_e_reproduzivel() -> None:
    df = pd.DataFrame({"x": range(100), "y": [0, 1] * 50})
    dev1, teste1 = divisao.dividir_aleatorio(df, proporcao_teste=0.3, semente=7)
    dev2, teste2 = divisao.dividir_aleatorio(df, proporcao_teste=0.3, semente=7)
    assert dev1["x"].tolist() == dev2["x"].tolist()
    assert len(teste1) == 30


def _painel_sintetico(n_chaves: int = 60, periodos: int = 5, semente: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(semente)
    linhas = []
    for chave in range(n_chaves):
        y = int(rng.binomial(1, 0.4))
        amostra = "DES" if chave < n_chaves * 0.6 else "OOT"
        for periodo in range(periodos):
            linhas.append(
                {
                    "id_cliente": chave,
                    "safra": periodo,
                    "valor": float(rng.normal(50 + 10 * y, 5)),
                    "amostra": amostra,
                    "y": y,
                }
            )
    return pd.DataFrame(linhas)


def test_fluxo_completo_ate_pedro_wise() -> None:
    """Ponta a ponta: um DataFrame com coluna de amostra e várias linhas
    por chave, passando por todas as etapas até o treinamento -- o cenário
    descrito como uso pretendido da biblioteca."""
    df = _painel_sintetico()

    df_dev, df_teste = divisao.dividir_por_amostra(
        df, coluna_amostra="amostra", valores_dev=["DES"], valores_teste=["OOT"]
    )
    n_chaves_dev_esperado = df_dev["id_cliente"].nunique()
    n_chaves_teste_esperado = df_teste["id_cliente"].nunique()

    df_dev, df_teste, colunas_geradas = esfera1.aplicar(
        df_dev, df_teste, chave="id_cliente", coluna_tempo="safra", colunas_valor=["valor"], janelas=[3]
    )
    assert len(df_dev) == n_chaves_dev_esperado  # uma linha por chave agora
    assert len(df_teste) == n_chaves_teste_esperado
    assert "valor_media_3m" in colunas_geradas

    df_dev, df_teste, colunas_regra = esfera2.aplicar(df_dev, df_teste, n_arvores=20, max_regras=5)
    assert isinstance(colunas_regra, list)  # pode ou não achar regra, não é o ponto do teste

    woe_dev, woe_teste, iv_por_variavel = categorizar.categorizar_e_transformar(df_dev, df_teste)
    assert "y" in woe_dev.columns
    assert len(iv_por_variavel) > 0

    resultado = treinamento.treinar(woe_dev, woe_teste, criterio="teste")
    assert resultado.ks_teste >= 0.0
    assert resultado.taxa_evento_dev > 0
    assert isinstance(resultado.coeficientes, dict)
