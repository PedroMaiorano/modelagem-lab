"""Testes de app/backend/ingestao.py — detecção de tipo/data e splits.
Rodar via: python -m pytest app/backend/test_ingestao.py (não está em
tests/ porque não é core do lab, é específico da interface).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd
from ingestao import (
    calcular_corte_por_percentual,
    detectar_colunas,
    dividir_aleatorio,
    dividir_por_amostra_existente,
    dividir_por_data_oot,
)


def test_detecta_data_yyyymmdd():
    df = pd.DataFrame({"dt": [20250101, 20250215, 20250320, 20250601]})
    colunas = detectar_colunas(df)
    assert colunas[0].tipo == "data"
    assert colunas[0].formato_data == "%Y%m%d"


def test_detecta_data_yyyymm():
    df = pd.DataFrame({"safra": [202501, 202502, 202503, 202504]})
    colunas = detectar_colunas(df)
    assert colunas[0].tipo == "data"
    assert colunas[0].formato_data == "%Y%m"


def test_detecta_data_com_barra():
    df = pd.DataFrame({"dt": ["2025/01/15", "2025/02/20", "2025/03/10"]})
    colunas = detectar_colunas(df)
    assert colunas[0].tipo == "data"
    assert colunas[0].formato_data == "%Y/%m/%d"


def test_detecta_data_com_hifen_dia_mes_ano():
    df = pd.DataFrame({"dt": ["15-01-2025", "20-02-2025", "10-03-2025"]})
    colunas = detectar_colunas(df)
    assert colunas[0].tipo == "data"
    assert colunas[0].formato_data == "%d-%m-%Y"


def test_idade_curta_nao_e_confundida_com_data():
    """Regressão do design: uma coluna de 2 dígitos (idade) não deve bater
    com nenhum formato de data (todos exigem 6-10 caracteres).
    """
    df = pd.DataFrame({"idade": [18, 25, 45, 67, 33, 29]})
    colunas = detectar_colunas(df)
    assert colunas[0].tipo == "numerico"
    assert colunas[0].formato_data is None


def test_coluna_categorica_texto():
    df = pd.DataFrame({"uf": ["SP", "RJ", "MG", "SP", "RJ"]})
    colunas = detectar_colunas(df)
    assert colunas[0].tipo == "categorico"
    assert colunas[0].n_distintos == 3


def test_coluna_numerica_continua():
    df = pd.DataFrame({"renda": [1500.0, 2300.5, 4200.0]})
    colunas = detectar_colunas(df)
    assert colunas[0].tipo == "numerico"


def test_dividir_por_amostra_existente():
    df = pd.DataFrame({"AMOSTRA": ["DES", "DES", "OOT", "OOT", "DES"], "x": [1, 2, 3, 4, 5]})
    df_dev, df_teste = dividir_por_amostra_existente(df, "AMOSTRA", ["DES"], ["OOT"])
    assert len(df_dev) == 3
    assert len(df_teste) == 2
    assert set(df_dev["x"]) == {1, 2, 5}
    assert set(df_teste["x"]) == {3, 4}


def test_dividir_por_data_oot_separa_passado_de_futuro():
    df = pd.DataFrame(
        {
            "safra": [202401, 202402, 202403, 202404, 202405, 202406],
            "x": [1, 2, 3, 4, 5, 6],
        }
    )
    df_dev, df_teste = dividir_por_data_oot(df, "safra", "%Y%m", "2024-04-01")
    assert set(df_dev["x"]) == {1, 2, 3}
    assert set(df_teste["x"]) == {4, 5, 6}


def test_dividir_por_data_oot_descarta_datas_invalidas():
    df = pd.DataFrame({"safra": [202401, 202402, 999999], "x": [1, 2, 3]})
    df_dev, df_teste = dividir_por_data_oot(df, "safra", "%Y%m", "2024-02-01")
    total = len(df_dev) + len(df_teste)
    assert total == 2  # a linha com data inválida (999999) não entra em nenhum dos dois


def test_calcular_corte_por_percentual_bate_com_split_real():
    """O corte sugerido por `calcular_corte_por_percentual` para 50% deve
    produzir uma divisão dev/teste aproximadamente equilibrada quando usado
    em `dividir_por_data_oot`.
    """
    df = pd.DataFrame({"safra": list(range(202401, 202413)), "x": list(range(12))})
    corte = calcular_corte_por_percentual(df, "safra", "%Y%m", proporcao_teste=0.5)
    df_dev, df_teste = dividir_por_data_oot(df, "safra", "%Y%m", corte)
    assert abs(len(df_dev) - len(df_teste)) <= 1


def test_dividir_aleatorio_e_reprodutivel_com_semente():
    df = pd.DataFrame({"x": range(100)})
    dev1, teste1 = dividir_aleatorio(df, proporcao_teste=0.3, semente=42)
    dev2, teste2 = dividir_aleatorio(df, proporcao_teste=0.3, semente=42)
    assert dev1["x"].tolist() == dev2["x"].tolist()
    assert teste1["x"].tolist() == teste2["x"].tolist()
    assert len(teste1) == 30


def test_dividir_aleatorio_sem_sobreposicao():
    df = pd.DataFrame({"x": range(50)})
    dev, teste = dividir_aleatorio(df, proporcao_teste=0.4, semente=1)
    assert set(dev["x"]) & set(teste["x"]) == set()
    assert set(dev["x"]) | set(teste["x"]) == set(range(50))


def test_detecta_colunas_mistas_no_mesmo_dataframe():
    df = pd.DataFrame(
        {
            "safra": [202401, 202402, 202403],
            "uf": ["SP", "RJ", "MG"],
            "renda": [1500.0, 2300.0, 4200.0],
            "y": [0, 1, 0],
        }
    )
    colunas = {c.nome: c.tipo for c in detectar_colunas(df)}
    assert colunas["safra"] == "data"
    assert colunas["uf"] == "categorico"
    assert colunas["renda"] == "numerico"
    # binário 0/1 é tratado como numérico, não categórico — decisão de escopo
    assert colunas["y"] == "numerico"
