"""Testes de `pipeline_lab.esteira.Esteira` -- builder mutável encadeável
que resolve a inconsistência de retorno entre as etapas soltas do funil
(ver `python/pipeline_lab/REFERENCIA.md`, seção 1).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from pipeline_lab import Esteira, EtapaForaDeOrdemError


def _dataset_flat(n: int = 200, semente: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(semente)
    y = rng.binomial(1, 0.4, size=n)
    return pd.DataFrame(
        {
            "amostra": ["train"] * (n // 2) + ["test"] * (n - n // 2),
            "renda": rng.normal(1000 + 200 * y, 100),
            "pago": rng.normal(500 + 50 * y, 30),
            "fatura": rng.normal(600, 40),
            "Churn": y,
        }
    )


def _painel(n_chaves: int = 60, periodos: int = 5, semente: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(semente)
    linhas = []
    for chave in range(n_chaves):
        y = int(rng.binomial(1, 0.4))
        amostra = "train" if chave < n_chaves * 0.6 else "test"
        for periodo in range(periodos):
            linhas.append(
                {
                    "id_cliente": chave,
                    "safra": periodo,
                    "dias_atraso": float(rng.normal(10 + 5 * y, 3)),
                    "amostra": amostra,
                    "y": y,
                }
            )
    return pd.DataFrame(linhas)


def test_fluxo_completo_via_esteira_ate_treinamento() -> None:
    df = _dataset_flat()

    resultado = (
        Esteira.dividir_por_amostra(
            df, coluna_amostra="amostra", valores_dev=["train"], valores_teste=["test"], coluna_y="Churn"
        )
        .construir_razoes(pares=[("pago", "fatura", "pct_pago")])
        .categorizar_e_transformar()
        .pre_selecionar(limiar_iv=0.0)
        .treinar(criterio="teste")
    )

    assert resultado.ks_teste >= 0.0
    assert isinstance(resultado.coeficientes, dict)


def test_construir_razoes_gera_colunas_em_dev_e_teste() -> None:
    df = _dataset_flat()
    esteira = Esteira.dividir_por_amostra(
        df, coluna_amostra="amostra", valores_dev=["train"], valores_teste=["test"], coluna_y="Churn"
    ).construir_razoes(pares=[("pago", "fatura", "pct_pago")])

    assert "pct_pago" in esteira.df_dev.columns
    assert "pct_pago" in esteira.df_teste.columns
    assert esteira.colunas_geradas["construcao"] == ["pct_pago"]


def test_agregar_temporal_reduz_painel_a_uma_linha_por_chave() -> None:
    df = _painel()
    esteira = Esteira.dividir_por_amostra(
        df, coluna_amostra="amostra", valores_dev=["train"], valores_teste=["test"]
    )
    n_chaves_dev = esteira.df_dev["id_cliente"].nunique()

    esteira.agregar_temporal(
        chave="id_cliente", coluna_tempo="safra", colunas_valor=["dias_atraso"], janelas=[3]
    )

    assert len(esteira.df_dev) == n_chaves_dev
    assert "dias_atraso_media_3m" in esteira.colunas_geradas["agregacao_temporal"]


def test_dividir_aleatorio_funciona_como_ponto_de_entrada() -> None:
    df = pd.DataFrame({"x": range(100), "y": [0, 1] * 50})
    esteira = Esteira.dividir_aleatorio(df, proporcao_teste=0.3, semente=7)

    assert len(esteira.df_teste) == 30
    assert esteira.iv_por_variavel is None


@pytest.mark.parametrize(
    "nome_etapa",
    ["construir_razoes", "agregar_temporal", "descobrir_interacoes"],
)
def test_etapas_pre_categorizacao_bloqueadas_depois_de_categorizar(nome_etapa: str) -> None:
    df = _dataset_flat()
    esteira = Esteira.dividir_por_amostra(
        df, coluna_amostra="amostra", valores_dev=["train"], valores_teste=["test"], coluna_y="Churn"
    ).categorizar_e_transformar()

    with pytest.raises(EtapaForaDeOrdemError):
        if nome_etapa == "construir_razoes":
            esteira.construir_razoes(pares=[("renda", "fatura", "razao_x")])
        elif nome_etapa == "agregar_temporal":
            esteira.agregar_temporal(
                chave="id_cliente", coluna_tempo="safra", colunas_valor=["x"], janelas=[3]
            )
        else:
            esteira.descobrir_interacoes()


def test_pre_selecionar_antes_de_categorizar_leva_erro() -> None:
    df = _dataset_flat()
    esteira = Esteira.dividir_por_amostra(
        df, coluna_amostra="amostra", valores_dev=["train"], valores_teste=["test"], coluna_y="Churn"
    )

    with pytest.raises(EtapaForaDeOrdemError):
        esteira.pre_selecionar(limiar_iv=0.0)
