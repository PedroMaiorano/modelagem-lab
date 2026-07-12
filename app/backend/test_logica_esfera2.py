"""Testes de app/backend/logica.py -- integração da esfera 2 (descoberta de
interação) no pipeline principal, entre Construção e Categorização (ver
`_construir_e_esfera2`/`_rodar_esfera2`/`ConfigEsfera2`). Rodar via:
python -m pytest app/backend/test_logica_esfera2.py (não está em tests/
porque não é core do lab, é orquestração específica da interface).
"""

from __future__ import annotations

import queue
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
import pandas as pd
from logica import ConfigEsfera2, _construir_e_esfera2


def _base_dev_teste(n: int = 400, semente: int = 0) -> tuple[pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(semente)
    a = rng.normal(0, 1, n)
    b = rng.normal(0, 1, n)
    tipo = rng.choice(["X", "Y", "Z"], size=n, p=[0.4, 0.4, 0.2])
    # risco alto só quando a E b são altos ao mesmo tempo (interação de
    # verdade, não capturada por um termo linear simples) -- exatamente o
    # tipo de padrão que a esfera 2 deveria conseguir achar.
    interacao = (a > 0.5) & (b > 0.5)
    p = np.where(interacao, 0.85, 0.15)
    y = rng.binomial(1, p)
    df = pd.DataFrame({"a": a, "b": b, "tipo": tipo, "y": y})
    metade = n // 2
    return df.iloc[:metade].reset_index(drop=True), df.iloc[metade:].reset_index(drop=True)


def _fila() -> queue.Queue[dict[str, Any]]:
    return queue.Queue()


def test_esfera2_desligada_nao_muda_nada() -> None:
    df_dev, df_teste = _base_dev_teste()
    colunas_antes = list(df_dev.columns)

    dev2, teste2, colunas_novas = _construir_e_esfera2(df_dev, df_teste, _fila(), esfera2=ConfigEsfera2())

    assert colunas_novas == []
    assert list(dev2.columns) == colunas_antes
    assert list(teste2.columns) == colunas_antes


def test_esfera2_ligada_adiciona_coluna_de_regra() -> None:
    df_dev, df_teste = _base_dev_teste()
    colunas_antes = set(df_dev.columns)

    dev2, teste2, colunas_novas = _construir_e_esfera2(
        df_dev,
        df_teste,
        _fila(),
        esfera2=ConfigEsfera2(ativo=True, n_arvores=30, max_regras=10, iv_minimo=0.02),
    )

    assert colunas_novas, "esperava pelo menos uma regra estável pro padrão de interação sintético"
    assert all(c.endswith("_regra") for c in colunas_novas)
    assert set(colunas_novas) <= (set(dev2.columns) - colunas_antes)
    assert set(colunas_novas) <= (set(teste2.columns) - colunas_antes)
    for c in colunas_novas:
        assert set(dev2[c].unique()) <= {0, 1}


def test_esfera2_woe_codifica_categorica_marcada() -> None:
    df_dev, df_teste = _base_dev_teste()

    dev2, teste2, colunas_novas = _construir_e_esfera2(
        df_dev,
        df_teste,
        _fila(),
        esfera2=ConfigEsfera2(
            ativo=True, colunas_categoricas=["tipo"], n_arvores=30, max_regras=10, iv_minimo=0.0
        ),
    )

    # as colunas ORIGINAIS (incluindo `tipo`, cru) devem seguir intactas pro
    # módulo de categorização processar do jeito de sempre -- a esfera 2 só
    # usa a versão WOE internamente pra gerar o threshold da regra.
    assert "tipo" in dev2.columns
    assert dev2["tipo"].tolist() == df_dev["tipo"].tolist()
    assert "tipo_woe" not in dev2.columns
    # nenhuma regra estável é garantida aqui (evento não depende de `tipo`
    # no dataset sintético) -- só verificamos que não quebra e que, se
    # alguma regra saiu, ela é uma coluna 0/1 válida.
    for c in colunas_novas:
        assert set(dev2[c].unique()) <= {0, 1}
