"""Testes de app/backend/logica.py -- esfera 1 (agregação temporal) como
tratamento em memória, mesmo padrão da esfera 2 (`_aplicar_esfera1`/
`ConfigEsfera1`) -- nunca grava/sobrescreve dataset, dev/teste agregados
SEPARADAMENTE (preserva o split já existente). Rodar via:
python -m pytest app/backend/test_logica_esfera1.py (não está em tests/
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
from logica import ConfigEsfera1, _aplicar_esfera1


def _painel_dev_teste(
    n_chaves_dev: int = 30, n_chaves_teste: int = 20, periodos: int = 5, semente: int = 0
) -> tuple[pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(semente)

    def _gerar(n_chaves: int, offset: int) -> pd.DataFrame:
        linhas = []
        for i in range(n_chaves):
            chave = offset + i
            y = int(rng.binomial(1, 0.4))
            for periodo in range(periodos):
                linhas.append(
                    {
                        "id_cliente": chave,
                        "safra": periodo,
                        "valor": float(rng.normal(50 + 10 * y, 5)),
                        "y": y,
                    }
                )
        return pd.DataFrame(linhas)

    return _gerar(n_chaves_dev, 0), _gerar(n_chaves_teste, 10_000)


def _fila() -> queue.Queue[dict[str, Any]]:
    return queue.Queue()


def test_esfera1_desligada_nao_muda_nada() -> None:
    df_dev, df_teste = _painel_dev_teste()

    dev2, teste2, colunas_novas = _aplicar_esfera1(df_dev, df_teste, _fila(), ConfigEsfera1())

    assert colunas_novas == []
    assert len(dev2) == len(df_dev)
    assert len(teste2) == len(df_teste)


def test_esfera1_ligada_reduz_a_uma_linha_por_chave_preservando_split() -> None:
    df_dev, df_teste = _painel_dev_teste(n_chaves_dev=30, n_chaves_teste=20, periodos=5)
    n_dev_antes = len(df_dev)

    config = ConfigEsfera1(
        ativo=True, chave="id_cliente", coluna_tempo="safra", colunas_valor=["valor"], janelas=[3]
    )
    dev2, teste2, colunas_novas = _aplicar_esfera1(df_dev, df_teste, _fila(), config)

    assert n_dev_antes == 30 * 5  # confirma que o fixture tinha várias linhas por chave
    assert len(dev2) == 30  # uma linha por chave, split dev preservado (30 chaves)
    assert len(teste2) == 20  # split teste preservado (20 chaves), nunca re-misturado com dev
    assert "valor_media_3m" in colunas_novas
    assert "valor_media_3m" in dev2.columns
    assert "y" in dev2.columns and "y" in teste2.columns
    assert "_tempo_norm" not in dev2.columns  # coluna de trabalho não pode vazar


def test_esfera1_ligada_sem_config_completa_leva_erro() -> None:
    df_dev, df_teste = _painel_dev_teste()
    config = ConfigEsfera1(ativo=True, chave="id_cliente")  # falta coluna_tempo/colunas_valor/janelas

    try:
        _aplicar_esfera1(df_dev, df_teste, _fila(), config)
        raise AssertionError("esperava ValueError por config incompleta")
    except ValueError:
        pass
