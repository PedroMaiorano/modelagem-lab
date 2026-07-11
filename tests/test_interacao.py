"""Testes da descoberta de interação (esfera 3): extração de regras via
ensemble de árvores rasas, sobre um caso sintético com interação conhecida.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from interacao import Condicao, Regra, extrair_candidatas, regras_para_colunas


def _dataset_interacao_xor(n: int = 3000, semente: int = 0) -> tuple[pd.DataFrame, pd.Series]:
    """y=1 só quando a>0 E b>0 (interação pura -- nenhuma combinação linear
    de a,b sozinhas separa bem as classes, só a conjunção separa).
    """
    rng = np.random.default_rng(semente)
    a = rng.normal(0, 1, n)
    b = rng.normal(0, 1, n)
    logit_p = -3.0 + 6.0 * ((a > 0) & (b > 0)).astype(float)
    p = 1 / (1 + np.exp(-logit_p))
    y = pd.Series(rng.binomial(1, p))
    return pd.DataFrame({"a": a, "b": b}), y


def test_regra_aplicar_mascara_conjuncao():
    df = pd.DataFrame({"a": [1.0, 5.0, 1.0, 5.0], "b": [1.0, 1.0, 5.0, 5.0]})
    regra = Regra((Condicao("a", ">", 3.0), Condicao("b", ">", 3.0)))
    assert regra.aplicar(df).tolist() == [False, False, False, True]


def test_regra_nome_legivel():
    regra = Regra((Condicao("tendencia", ">", 1.5), Condicao("maximo", "<=", 25.3333)))
    assert regra.nome == "tendencia>1.5 & maximo<=25.33"


def test_extrai_a_interacao_verdadeira_do_caso_xor():
    X, y = _dataset_interacao_xor()
    regras = extrair_candidatas(X, y, profundidade_maxima=2, n_arvores=30, semente=0)

    assert len(regras) > 0
    melhor = regras[0]
    features_da_melhor = {c.feature for c in melhor.condicoes}
    assert features_da_melhor == {"a", "b"}  # a melhor regra usa as duas variáveis, não só uma


def test_todas_as_regras_tem_pelo_menos_duas_condicoes():
    X, y = _dataset_interacao_xor()
    regras = extrair_candidatas(X, y, profundidade_maxima=3, n_arvores=20, semente=1)
    assert all(len(r.condicoes) >= 2 for r in regras)


def test_regras_sem_duplicatas():
    X, y = _dataset_interacao_xor()
    regras = extrair_candidatas(X, y, profundidade_maxima=2, n_arvores=40, semente=2)
    nomes = [r.nome for r in regras]
    assert len(nomes) == len(set(nomes))


def test_respeita_max_regras():
    X, y = _dataset_interacao_xor()
    regras = extrair_candidatas(X, y, profundidade_maxima=3, n_arvores=40, max_regras=5, semente=3)
    assert len(regras) <= 5


def test_filtro_de_suporte_descarta_regras_triviais():
    X, y = _dataset_interacao_xor()
    regras = extrair_candidatas(
        X, y, profundidade_maxima=2, n_arvores=30, min_suporte=0.3, max_suporte=0.7, semente=4
    )
    for regra in regras:
        suporte = regra.aplicar(X).mean()
        assert 0.3 <= suporte <= 0.7


def test_regras_para_colunas_materializa_binario():
    df = pd.DataFrame({"a": [1.0, 5.0], "b": [1.0, 5.0]})
    regra = Regra((Condicao("a", ">", 3.0), Condicao("b", ">", 3.0)))
    colunas = regras_para_colunas([regra], df)

    assert colunas.shape == (2, 1)
    assert colunas.iloc[:, 0].tolist() == [0, 1]
    assert colunas.columns[0] == f"{regra.nome}_regra"


def test_y_constante_nao_quebra_extracao():
    """GradientBoostingClassifier não aceita y com uma classe só -- deve
    falhar de forma clara, não silenciosa."""
    X = pd.DataFrame({"a": [1.0, 2.0, 3.0], "b": [1.0, 2.0, 3.0]})
    y = pd.Series([0, 0, 0])
    with pytest.raises(ValueError):
        extrair_candidatas(X, y, n_arvores=5)
