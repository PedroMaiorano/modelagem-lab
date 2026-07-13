"""Testes da descoberta de interação (esfera 3): extração de regras via
ensemble de árvores rasas, sobre um caso sintético com interação conhecida.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from agregacao_temporal import extrair_base_agregado
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


def _dataset_interacao_cruzada(n: int = 3000, semente: int = 0) -> tuple[pd.DataFrame, pd.Series]:
    """Sinal de verdade é uma interação ENTRE bases (atraso x renda) -- nomes
    de coluna seguem a convenção `{base}_{primitiva}_{n}m` de
    agregacao_temporal, então `extrair_base_agregado` (usado por padrão)
    reconhece "atraso" e "renda" como bases diferentes.
    """
    rng = np.random.default_rng(semente)
    atraso_maximo = rng.normal(0, 1, n)
    renda_tendencia = rng.normal(0, 1, n)
    logit_p = -3.0 + 6.0 * ((atraso_maximo > 0) & (renda_tendencia < 0)).astype(float)
    p = 1 / (1 + np.exp(-logit_p))
    y = pd.Series(rng.binomial(1, p))
    X = pd.DataFrame(
        {
            "atraso_maximo_3m": atraso_maximo,
            "renda_tendencia_3m": renda_tendencia,
        }
    )
    return X, y


def test_permite_cruzamento_entre_bases_por_padrao():
    X, y = _dataset_interacao_cruzada()
    regras = extrair_candidatas(X, y, profundidade_maxima=2, n_arvores=30, semente=0)

    assert len(regras) > 0
    bases_da_melhor = {extrair_base_agregado(c.feature) for c in regras[0].condicoes}
    assert bases_da_melhor == {"atraso", "renda"}  # cruzou as duas bases, como esperado


def test_restringir_a_mesma_base_bloqueia_regra_cruzada():
    X, y = _dataset_interacao_cruzada()
    regras = extrair_candidatas(
        X, y, profundidade_maxima=2, n_arvores=30, semente=0, permitir_cruzamento_entre_bases=False
    )

    for regra in regras:
        bases = {extrair_base_agregado(c.feature) for c in regra.condicoes}
        assert len(bases) == 1  # nenhuma regra devolvida mistura atraso com renda


def test_nao_devolve_quase_duplicatas_de_limiar():
    """Bug real observado: a mesma combinação de variáveis+direção reaparece
    com limiar levemente diferente em árvores treinadas em subamostras
    diferentes (ex.: "cloud<=61.5 & X" e "cloud<=64.5 & X") -- a tabela final
    não deve ter duas regras com a mesma "assinatura" (mesmas variáveis e
    mesmos operadores, só o número do limiar mudando).
    """
    X, y = _dataset_interacao_xor(n=4000)
    regras = extrair_candidatas(X, y, profundidade_maxima=2, n_arvores=80, max_regras=30, semente=0)

    assinaturas = [frozenset((c.feature, c.operador) for c in r.condicoes) for r in regras]
    assert len(assinaturas) == len(set(assinaturas))


def test_nenhuma_regra_repete_a_mesma_variavel():
    """Bug real: uma árvore pode cortar a mesma variável duas vezes no
    mesmo caminho (ex.: x>28.5 depois x>57.5, refinando o mesmo corte) --
    isso passa no filtro de "2+ condições" mas não é interação nenhuma, só
    binning univariado disfarçado (o corte mais apertado já implica o
    outro). Cenário: uma variável dominante (`x`) e uma fraca/irrelevante
    (`ruido`) -- profundidade 3 dá espaço de sobra pra árvore cortar `x`
    mais de uma vez no mesmo ramo. Nenhuma regra devolvida deve usar menos
    de 2 variáveis distintas.
    """
    rng = np.random.default_rng(6)
    n = 3000
    x = rng.normal(0, 1, n)
    ruido = rng.normal(0, 1, n)
    p = 1 / (1 + np.exp(-(3.0 * x)))
    y = pd.Series(rng.binomial(1, p))
    X = pd.DataFrame({"x": x, "ruido": ruido})

    regras = extrair_candidatas(X, y, profundidade_maxima=3, n_arvores=40, min_suporte=0.01, semente=6)
    for regra in regras:
        assert len({c.feature for c in regra.condicoes}) >= 2


def test_proporcao_variaveis_por_split_deixa_variavel_fraca_aparecer():
    """Feedback real: uma variável muito mais forte que as outras pode
    "sufocar" o espaço de splits -- toda árvore vence a disputa nela, e
    interações envolvendo variáveis mais fracas nunca chegam a ser
    testadas. Cenário: 4 variáveis fortes (isoladas) + uma interação fraca
    entre duas variáveis fracas -- sem `proporcao_variaveis_por_split`, a
    interação fraca não aparece em NENHUMA regra; limitando as variáveis
    candidatas por split, ela aparece em boa parte das regras.
    """
    rng = np.random.default_rng(5)
    n = 6000
    fortes = {f"forte{i}": rng.normal(0, 1, n) for i in range(4)}
    fraca1 = rng.normal(0, 1, n)
    fraca2 = rng.normal(0, 1, n)

    logit_p = sum(2.5 * v for v in fortes.values()) + 1.3 * ((fraca1 > 0) & (fraca2 > 0)).astype(float)
    p = 1 / (1 + np.exp(-logit_p))
    y = pd.Series(rng.binomial(1, p))
    X = pd.DataFrame({**fortes, "fraca1": fraca1, "fraca2": fraca2})

    def _n_regras_com_variavel_fraca(regras: list[Regra]) -> int:
        return sum(1 for r in regras if any(c.feature in ("fraca1", "fraca2") for c in r.condicoes))

    sem_limite = extrair_candidatas(
        X, y, profundidade_maxima=2, n_arvores=40, max_regras=200, semente=0, min_suporte=0.01
    )
    com_limite = extrair_candidatas(
        X,
        y,
        profundidade_maxima=2,
        n_arvores=40,
        max_regras=200,
        semente=0,
        min_suporte=0.01,
        proporcao_variaveis_por_split=0.3,
    )

    assert _n_regras_com_variavel_fraca(sem_limite) == 0
    assert _n_regras_com_variavel_fraca(com_limite) > 0
