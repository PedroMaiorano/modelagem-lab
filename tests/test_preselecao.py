"""Testes de python/preselecao/filtros.py."""

from __future__ import annotations

import numpy as np
import pandas as pd
from preselecao import filtrar_correlacao, filtrar_iv, filtrar_variancia, pre_selecionar


def test_filtrar_variancia_descarta_quase_constante():
    df = pd.DataFrame({"a": [1.0] * 100, "b": np.random.default_rng(0).normal(size=100)})
    resultado = filtrar_variancia(df, ["a", "b"], limiar=1e-6)
    assert resultado == ["b"]


def test_filtrar_iv_usa_base_semantica_nao_o_nome_da_coluna():
    """`renda_woe`, `renda_log`, `renda_bin` compartilham a base "renda" —
    o filtro deve tratar todas com o mesmo IV, não olhar pra IV por coluna
    (que nem existe pras derivadas, só a base tem IV calculado)."""
    colunas = ["renda_woe", "renda_log", "renda_bin", "idade_woe"]
    iv_por_base = {"renda": 0.15, "idade": 0.01}
    resultado = filtrar_iv(colunas, iv_por_base, limiar=0.02)
    assert set(resultado) == {"renda_woe", "renda_log", "renda_bin"}


def test_filtrar_iv_trata_base_ausente_como_zero():
    resultado = filtrar_iv(["fantasma_woe"], {}, limiar=0.02)
    assert resultado == []


def test_filtrar_correlacao_mantem_a_de_maior_iv():
    rng = np.random.default_rng(0)
    base = rng.normal(size=500)
    df = pd.DataFrame(
        {
            "a_woe": base,
            "b_woe": base + rng.normal(scale=0.001, size=500),  # quase idêntica a a_woe
            "c_woe": rng.normal(size=500),  # independente
        }
    )
    iv_por_base = {"a": 0.05, "b": 0.30, "c": 0.10}  # b tem IV maior que a
    mantidas, descartados = filtrar_correlacao(df, ["a_woe", "b_woe", "c_woe"], iv_por_base, limiar=0.9)
    assert "b_woe" in mantidas
    assert "a_woe" not in mantidas
    assert "c_woe" in mantidas
    assert len(descartados) == 1
    assert descartados[0][:2] == ("b_woe", "a_woe")


def test_filtrar_correlacao_nunca_descarta_par_da_mesma_base():
    """`renda_woe`/`renda_bin`/`renda_quad` são a MESMA variável em encodings
    diferentes — sempre super correlacionadas entre si por construção, e IV
    idêntico (calculado por base). Se o filtro de correlação as tratasse
    como redundância normal, colapsaria a família inteira num só
    sobrevivente antes do Pedro_Wise poder escolher a melhor versão pra
    aquele modelo específico — o próprio motivo delas existirem.
    """
    rng = np.random.default_rng(0)
    x = rng.normal(size=500)
    df = pd.DataFrame(
        {
            "renda_woe": x,
            "renda_bin": x + rng.normal(scale=0.001, size=500),  # quase idêntica (mesma base)
            "idade_woe": rng.normal(size=500),  # base diferente, independente
        }
    )
    iv_por_base = {"renda": 0.20, "idade": 0.10}
    mantidas, descartados = filtrar_correlacao(
        df, ["renda_woe", "renda_bin", "idade_woe"], iv_por_base, limiar=0.9
    )
    assert "renda_woe" in mantidas
    assert "renda_bin" in mantidas  # as duas sobrevivem, mesma base não é filtrada
    assert descartados == []


def test_filtrar_correlacao_com_menos_de_2_colunas_nao_quebra():
    df = pd.DataFrame({"a": [1.0, 2.0, 3.0]})
    mantidas, descartados = filtrar_correlacao(df, ["a"], {}, limiar=0.9)
    assert mantidas == ["a"]
    assert descartados == []


def test_pre_selecionar_funil_completo():
    rng = np.random.default_rng(1)
    n = 500
    base = rng.normal(size=n)
    df = pd.DataFrame(
        {
            "y": (base > 0).astype(int),
            "forte_woe": base + rng.normal(scale=0.1, size=n),
            "forte_duplicada_woe": base + rng.normal(scale=0.1, size=n),  # correlacionada com forte
            "fraca_woe": rng.normal(size=n),  # sem relação com y, IV baixo
            "constante_woe": np.ones(n),  # variância zero
        }
    )
    iv_por_base = {"forte": 0.5, "forte_duplicada": 0.5, "fraca": 0.001, "constante": 0.0}
    resultado = pre_selecionar(
        df, iv_por_base, limiar_variancia=1e-6, limiar_iv=0.02, limiar_correlacao=0.9
    )
    assert "constante_woe" not in resultado["colunas_mantidas"]
    assert "fraca_woe" not in resultado["colunas_mantidas"]
    # uma das duas correlacionadas sobrevive (mesmo IV -> desempate alfabético), nunca as duas
    assert len(resultado["colunas_mantidas"]) == 1
    assert resultado["colunas_mantidas"][0] in {"forte_woe", "forte_duplicada_woe"}
    assert resultado["n_inicial"] == 4
    assert resultado["n_final"] == 1


def test_pre_selecionar_com_todos_os_limiares_none_nao_filtra_nada():
    df = pd.DataFrame({"y": [0, 1, 0, 1], "a_woe": [1.0, 2.0, 1.0, 2.0], "b_woe": [1.0, 1.0, 1.0, 1.0]})
    resultado = pre_selecionar(df, {}, limiar_variancia=None, limiar_iv=None, limiar_correlacao=None)
    assert set(resultado["colunas_mantidas"]) == {"a_woe", "b_woe"}
