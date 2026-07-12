"""Testes de app/backend/feature_lab.py -- WOE de categóricas na esfera 2
(ver `_transformar_categoricas_woe`). Rodar via:
python -m pytest app/backend/test_feature_lab.py (não está em tests/ porque
não é core do lab, é orquestração específica da interface).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
import pandas as pd
from feature_lab import (
    _transformar_categoricas_woe,
    comparar_com_pedro_wise,
    descobrir_em_tabela,
    rodar_regressao_manual,
)


def _base_com_categorica(n: int = 400, semente: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(semente)
    # "tipo_defeito" é categórica sem ordem real (como Thallium no dataset
    # Heart Disease: códigos 3/6/7, cada um com taxa de evento própria, não
    # uma escala) -- categoria "C" tem risco bem maior que "A"/"B".
    tipo = rng.choice(["A", "B", "C"], size=n, p=[0.4, 0.4, 0.2])
    ruido = rng.normal(0, 1, n)
    p = np.where(tipo == "C", 0.85, np.where(tipo == "B", 0.4, 0.1))
    y = rng.binomial(1, p)
    return pd.DataFrame({"tipo_defeito": tipo, "ruido": ruido, "y": y})


def test_coluna_texto_vira_woe_automaticamente() -> None:
    df = _base_com_categorica()
    dev, teste = df.iloc[:300].reset_index(drop=True), df.iloc[300:].reset_index(drop=True)

    dev_t, teste_t, colunas_x = _transformar_categoricas_woe(dev, teste, ["tipo_defeito", "ruido"], [])

    assert "tipo_defeito_woe" in colunas_x
    assert "tipo_defeito" not in colunas_x
    assert "ruido" in colunas_x  # numérica sem marcação -- passa direto
    assert pd.api.types.is_numeric_dtype(dev_t["tipo_defeito_woe"])
    assert pd.api.types.is_numeric_dtype(teste_t["tipo_defeito_woe"])
    # categoria de maior risco (C) deve ter WOE mais negativo que a de menor
    # risco (A) -- convenção de sinal do módulo (mais evento = WOE negativo).
    linha_a = dev.assign(woe=dev_t["tipo_defeito_woe"])[dev["tipo_defeito"] == "A"]
    linha_c = dev.assign(woe=dev_t["tipo_defeito_woe"])[dev["tipo_defeito"] == "C"]
    assert linha_a["woe"].iloc[0] > linha_c["woe"].iloc[0]


def test_coluna_numerica_so_vira_woe_se_marcada() -> None:
    df = _base_com_categorica()
    dev, teste = df.iloc[:300].reset_index(drop=True), df.iloc[300:].reset_index(drop=True)
    mapa_codigo = {"A": 3, "B": 6, "C": 7}
    dev = dev.rename(columns={"tipo_defeito": "cod"}).assign(cod=lambda d: d["cod"].map(mapa_codigo))
    teste = teste.rename(columns={"tipo_defeito": "cod"}).assign(cod=lambda d: d["cod"].map(mapa_codigo))

    _, _, sem_marcacao = _transformar_categoricas_woe(dev, teste, ["cod", "ruido"], [])
    assert sem_marcacao == ["cod", "ruido"]  # numérica, não marcada -- fica crua

    _, _, com_marcacao = _transformar_categoricas_woe(dev, teste, ["cod", "ruido"], ["cod"])
    assert com_marcacao == ["cod_woe", "ruido"]


def test_descobrir_em_tabela_aceita_coluna_texto_como_candidata() -> None:
    df = _base_com_categorica()
    registros: list[dict[str, Any]] = df.to_dict(orient="records")  # type: ignore[assignment]

    resultado = descobrir_em_tabela(
        registros=registros,
        colunas_x=["tipo_defeito", "ruido"],
        max_regras=5,
        n_arvores=20,
    )
    assert resultado["n_dev"] > 0
    assert resultado["n_teste"] > 0


def _regra_sobre_woe_de_tipo_defeito(iv_minimo: float = 0.05) -> dict[str, Any]:
    """Roda a esfera 2 marcando `tipo_defeito` como categórica, e devolve a
    primeira regra descoberta que referencia a coluna WOE resultante --
    reproduz exatamente o cenário que quebrava `rodar_regressao_manual`/
    `comparar_com_pedro_wise` (regra referenciando `tipo_defeito_woe`, uma
    coluna que só existe depois do split+WOE, nunca antes)."""
    df = _base_com_categorica()
    registros: list[dict[str, Any]] = df.to_dict(orient="records")  # type: ignore[assignment]
    resultado = descobrir_em_tabela(
        registros=registros,
        colunas_x=["tipo_defeito", "ruido"],
        colunas_categoricas=["tipo_defeito"],
        max_regras=10,
        n_arvores=30,
    )
    regra: dict[str, Any] = next(r for r in resultado["regras"] if r["iv_teste"] >= iv_minimo)
    assert any(c["feature"] == "tipo_defeito_woe" for c in regra["condicoes"])
    return regra


def test_rodar_regressao_manual_aceita_regra_sobre_categorica_woe() -> None:
    regra = _regra_sobre_woe_de_tipo_defeito()
    df = _base_com_categorica()
    registros: list[dict[str, Any]] = df.to_dict(orient="records")  # type: ignore[assignment]

    resultado = rodar_regressao_manual(
        registros=registros,
        colunas_x=["ruido"],
        colunas_categoricas=["tipo_defeito"],
        regras=[{"condicoes": regra["condicoes"]}],
    )
    assert resultado["n_dev"] > 0
    assert any(nome.endswith("_regra") for nome in resultado["coeficientes"])


def test_comparar_com_pedro_wise_aceita_regra_sobre_categorica_woe() -> None:
    regra = _regra_sobre_woe_de_tipo_defeito()
    df = _base_com_categorica()
    registros: list[dict[str, Any]] = df.to_dict(orient="records")  # type: ignore[assignment]

    resultado = comparar_com_pedro_wise(
        registros=registros,
        colunas_base=["tipo_defeito", "ruido"],
        regras=[{"condicoes": regra["condicoes"]}],
        colunas_categoricas=["tipo_defeito"],
    )
    assert resultado["n_dev"] > 0
    assert resultado["n_teste"] > 0
    assert "sem_regras" in resultado and "com_regras" in resultado
