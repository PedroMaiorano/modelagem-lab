"""Testes de app/backend/logica.py -- `_categorizar_e_transformar` não pode
descartar coluna binária (0/1) silenciosamente. Bug real: `bins_monotonicos`
numa coluna com só 2 valores gera só 2 edges, e o filtro `len(edges) < 3`
descartava a coluna inteira -- uma regra da esfera 2 (sempre 0/1) nunca
chegava a virar candidata de verdade pro Pedro_Wise. Rodar via:
python -m pytest app/backend/test_logica_categorizacao.py (não está em
tests/ porque não é core do lab, é orquestração específica da interface).
"""

from __future__ import annotations

import queue
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
import pandas as pd
from logica import _categorizar_e_transformar


def _base_com_flag_binaria(n: int = 400, semente: int = 0) -> tuple[pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(semente)
    idade = rng.normal(40, 10, n)
    flag = rng.choice([0, 1], size=n, p=[0.6, 0.4])
    p = np.where(flag == 1, 0.7, 0.2)
    y = rng.binomial(1, p)
    df = pd.DataFrame({"idade": idade, "flag_regra": flag, "y": y})
    metade = n // 2
    return df.iloc[:metade].reset_index(drop=True), df.iloc[metade:].reset_index(drop=True)


def test_coluna_binaria_nao_e_descartada() -> None:
    df_dev, df_teste = _base_com_flag_binaria()
    fila: queue.Queue[dict[str, Any]] = queue.Queue()

    woe_dev, woe_teste, iv_por_variavel = _categorizar_e_transformar(df_dev, df_teste, fila)

    assert "flag_regra" in iv_por_variavel
    assert "flag_regra_woe" in woe_dev.columns
    assert "flag_regra_woe" in woe_teste.columns
    assert iv_por_variavel["flag_regra"] > 0.02  # sinal real construído no fixture


def test_coluna_continua_ainda_e_categorizada_normalmente() -> None:
    df_dev, df_teste = _base_com_flag_binaria()
    fila: queue.Queue[dict[str, Any]] = queue.Queue()

    woe_dev, _, iv_por_variavel = _categorizar_e_transformar(df_dev, df_teste, fila)

    assert "idade" in iv_por_variavel
    assert "idade_woe" in woe_dev.columns
