"""Testes de app/backend/logica.py -- IV univariado no preview do dataset
(aba Dataset, ver `_iv_univariado_preview`/`preview_dataset`). Rodar via:
python -m pytest app/backend/test_logica_preview.py (não está em tests/
porque não é core do lab, é orquestração específica da interface).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import ingestao
import logica
import numpy as np
import pandas as pd
import pytest


def test_preview_inclui_iv_por_coluna(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    rng = np.random.default_rng(0)
    n = 2000
    forte = rng.normal(0, 1, n)
    ruido = rng.normal(0, 1, n)
    flag = rng.choice([0, 1], size=n)
    # efeitos grandes e amostra maior -- robusto contra ruído de amostragem
    # marginal (o ponto do teste é "binária não é zerada pelo bug de bin",
    # não medir um tamanho de efeito exato).
    p = 1 / (1 + np.exp(-(2.0 * forte + 2.5 * flag)))
    y = rng.binomial(1, p)
    df = pd.DataFrame({"forte": forte, "ruido": ruido, "flag": flag, "y": y})
    metade = n // 2

    monkeypatch.setattr(logica, "DIR_DADOS", tmp_path)
    monkeypatch.setattr(ingestao, "DIR_DADOS", tmp_path)
    ingestao.gravar_dataset_preparado(
        "base_iv", df.iloc[:metade].reset_index(drop=True), df.iloc[metade:].reset_index(drop=True)
    )

    resultado = logica.preview_dataset("base_iv")

    iv_forte = resultado["resumo_colunas"]["forte"]["iv"]
    iv_ruido = resultado["resumo_colunas"]["ruido"]["iv"]
    iv_flag = resultado["resumo_colunas"]["flag"]["iv"]

    assert iv_forte > iv_ruido  # sinal real deve superar ruído
    assert iv_flag > 0.02  # coluna binária não pode ser descartada/zerada
