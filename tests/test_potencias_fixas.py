"""Testes de python/transformacao/potencias_fixas.py — família de
transformações de potência fixas (log/raiz/quad/cubo/inversas)."""

from __future__ import annotations

import numpy as np
import pandas as pd
from pedro_wise.base import extrair_base
from transformacao import gerar_transformacoes_fixas


def test_gera_todas_para_serie_positiva_sem_zero():
    x = pd.Series([1.0, 2.0, 3.0, 4.0])
    resultado = gerar_transformacoes_fixas(x, "renda")
    esperadas = {
        "renda_log",
        "renda_raiz",
        "renda_quad",
        "renda_cubo",
        "renda_inv",
        "renda_invquad",
        "renda_invcubo",
    }
    assert set(resultado.keys()) == esperadas


def test_omite_log_e_raiz_se_houver_valor_nao_positivo():
    x = pd.Series([-1.0, 0.0, 2.0, 3.0])
    resultado = gerar_transformacoes_fixas(x, "saldo")
    assert "saldo_log" not in resultado
    assert "saldo_raiz" not in resultado
    # quad/cubo sempre definidas, mesmo com negativos/zero
    assert "saldo_quad" in resultado
    assert "saldo_cubo" in resultado


def test_omite_inversas_se_houver_zero():
    x = pd.Series([0.0, 1.0, 2.0])
    resultado = gerar_transformacoes_fixas(x, "idade")
    assert "idade_inv" not in resultado
    assert "idade_invquad" not in resultado
    assert "idade_invcubo" not in resultado


def test_valores_batem_com_a_formula():
    x = pd.Series([2.0, 4.0])
    resultado = gerar_transformacoes_fixas(x, "v")
    assert np.allclose(resultado["v_log"].to_numpy(), np.log(x.to_numpy()))
    assert np.allclose(resultado["v_quad"].to_numpy(), x.to_numpy() ** 2)
    assert np.allclose(resultado["v_inv"].to_numpy(), 1 / x.to_numpy())


def test_nomes_geram_a_mesma_base_da_versao_woe():
    """Motivação do módulo: `pedro_wise.base.extrair_base` precisa
    reconhecer as transformações fixas como a MESMA base de `renda_woe`,
    senão o Pedro_Wise nunca as considera candidatas de troca simples."""
    x = pd.Series([1.0, 2.0, 3.0])
    resultado = gerar_transformacoes_fixas(x, "renda")
    for nome in resultado:
        assert extrair_base(nome) == extrair_base("renda_woe") == "renda"


def test_series_resultantes_tem_o_nome_certo():
    x = pd.Series([1.0, 2.0])
    resultado = gerar_transformacoes_fixas(x, "v")
    for nome, serie in resultado.items():
        assert serie.name == nome
