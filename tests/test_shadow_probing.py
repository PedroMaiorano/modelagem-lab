"""Testes do critério de parada por shadow-variable probing.

O teste central (`test_shadow_probing_elimina_ruido_que_o_greedy_puro_aceitaria`)
recria o cenário observado na validação contra o R (`docs/algoritmos-originais/
pedro-wise-resumo.md`): uma variável de puro ruído (`x_ruido2_woe`) foi aceita
por acaso amostral porque "score não melhorou mais" é o único critério de
parada. Com shadow probing ligado, uma seed onde o greedy puro aceita 2
variáveis de ruído passa a aceitar 0. `test_shadow_probing_nunca_piora_
contagem_de_ruido_em_varias_sementes` mostra que isso nunca piora (mas também
não garante zero ruído em toda seed — é heurística, não prova formal).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from pedro_wise.base import extrair_base
from pedro_wise.estimators import LogisticGLM
from pedro_wise.metrics import KSGaussianMetric
from pedro_wise.selection import run_level1
from pedro_wise.shadow_probing import adicionar_variaveis_sombra, eh_sombra
from pedro_wise.types import Level1Config, SelectionState, ShadowProbingConfig


def test_eh_sombra():
    assert eh_sombra("x1_woe__shadow")
    assert not eh_sombra("x1_woe")


def test_adicionar_variaveis_sombra_preserva_marginal_mas_quebra_relacao_com_y():
    rng = np.random.default_rng(0)
    n = 5000
    x = rng.normal(0, 1, n)
    y = rng.binomial(1, 1 / (1 + np.exp(-1.5 * x)))
    df = pd.DataFrame({"y": y, "x_woe": x})

    df_aug = adicionar_variaveis_sombra(df, ["x_woe"], rng, sufixo="__shadow")

    assert "x_woe__shadow" in df_aug.columns
    # mesma distribuição marginal (é uma permutação, não um novo sorteio)
    assert sorted(df_aug["x_woe__shadow"]) == pytest.approx(sorted(df["x_woe"]))
    # mas a correlação com y deve ser muito mais fraca que a da variável real
    corr_real = np.corrcoef(df["x_woe"], df["y"])[0, 1]
    corr_sombra = np.corrcoef(df_aug["x_woe__shadow"], df["y"])[0, 1]
    assert abs(corr_sombra) < abs(corr_real) / 3


def _construir_dataset_ruido(seed: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    """x1_woe é informativo. x_ruido0..x_ruido7 são puro ruído, mas com N
    variáveis de ruído altas o bastante para que, por acaso amostral em uma
    base pequena, alguma pareça melhorar o KS de teste — reproduzindo o
    tipo de falso positivo observado na validação contra o R.
    """
    rng = np.random.default_rng(seed)
    n = 600  # base pequena de propósito: acaso amostral é mais provável

    x1 = rng.normal(0, 1, n)
    logit_p = 1.0 * x1
    p = 1 / (1 + np.exp(-logit_p))
    y = rng.binomial(1, p)

    dados = {"y": y, "x1_woe": x1}
    for i in range(8):
        dados[f"x_ruido{i}_woe"] = rng.normal(0, 1, n)

    df = pd.DataFrame(dados)
    metade = n // 2
    return df.iloc[:metade].reset_index(drop=True), df.iloc[metade:].reset_index(drop=True)


@pytest.fixture
def dataset_com_ruido_forte() -> tuple[pd.DataFrame, pd.DataFrame]:
    return _construir_dataset_ruido(seed=123)


@pytest.fixture
def dataset_onde_ruido_e_eliminado() -> tuple[pd.DataFrame, pd.DataFrame]:
    """seed=2: varrendo sementes (ver `test_shadow_probing_nunca_piora_contagem_
    de_ruido_em_varias_sementes`), este é um caso onde o greedy puro aceita 2
    variáveis de ruído puro e o shadow probing elimina as duas — a
    demonstração mais forte e honesta do ganho (não é garantido em toda seed).
    """
    return _construir_dataset_ruido(seed=2)


def _estado_nulo(estimator, metric, df_dev, df_teste):
    modelo_nulo = estimator.fit(df_dev[[]], df_dev["y"])
    score_nulo = metric(modelo_nulo, df_dev[[]], df_dev["y"], df_teste[[]], df_teste["y"])
    return SelectionState(variables=(), model=modelo_nulo, score=score_nulo)


def test_shadow_probing_nunca_adiciona_variavel_sombra_ao_modelo_final(dataset_com_ruido_forte):
    df_dev, df_teste = dataset_com_ruido_forte
    estimator = LogisticGLM()
    metric = KSGaussianMetric(criterio="teste")
    config = Level1Config(
        backward_simples=False,
        shadow_probing=ShadowProbingConfig(ativado=True, semente=7),
    )

    estado_final, trace = run_level1(
        estimator, metric, df_dev, df_teste, _estado_nulo(estimator, metric, df_dev, df_teste), config
    )

    assert not any(eh_sombra(v) for v in estado_final.variables)
    assert any("shadow_probing" in evento for evento in trace.eventos)


def test_shadow_probing_elimina_ruido_que_o_greedy_puro_aceitaria(dataset_onde_ruido_e_eliminado):
    """Comparação direta, mesma base: sem shadow probing o greedy aceita 2
    variáveis de ruído puro; com shadow probing, nenhuma entra. Essa é a
    demonstração forte — `test_shadow_probing_nunca_adiciona_variavel_sombra_ao_modelo_final`
    só garante que a SOMBRA em si nunca é aceita (trivial por construção), não
    que o ruído real é evitado.
    """
    df_dev, df_teste = dataset_onde_ruido_e_eliminado
    estimator = LogisticGLM()
    metric = KSGaussianMetric(criterio="teste")
    estado_inicial = _estado_nulo(estimator, metric, df_dev, df_teste)

    estado_sem, _ = run_level1(
        estimator, metric, df_dev, df_teste, estado_inicial, Level1Config(backward_simples=False)
    )
    estado_com, _ = run_level1(
        estimator,
        metric,
        df_dev,
        df_teste,
        estado_inicial,
        Level1Config(backward_simples=False, shadow_probing=ShadowProbingConfig(ativado=True, semente=7)),
    )

    n_ruido_sem = sum(1 for v in estado_sem.variables if "ruido" in v)
    n_ruido_com = sum(1 for v in estado_com.variables if "ruido" in v)

    assert n_ruido_sem > 0, "pré-condição do teste: o greedy puro precisa aceitar ruído aqui"
    assert n_ruido_com == 0
    assert "x1" in {extrair_base(v) for v in estado_com.variables}  # a variável informativa não se perde


def test_shadow_probing_nunca_piora_contagem_de_ruido_em_varias_sementes():
    """Não é garantido eliminar 100% do ruído em toda semente (é heurística, não
    prova formal — ver docs/literatura/shadow-variable-probing.md), mas nunca
    deve SELECIONAR MAIS ruído que o greedy puro. Varre várias sementes.
    """
    estimator = LogisticGLM()
    metric = KSGaussianMetric(criterio="teste")

    for seed in range(8):
        df_dev, df_teste = _construir_dataset_ruido(seed)
        estado_inicial = _estado_nulo(estimator, metric, df_dev, df_teste)

        estado_sem, _ = run_level1(
            estimator, metric, df_dev, df_teste, estado_inicial, Level1Config(backward_simples=False)
        )
        estado_com, _ = run_level1(
            estimator,
            metric,
            df_dev,
            df_teste,
            estado_inicial,
            Level1Config(backward_simples=False, shadow_probing=ShadowProbingConfig(ativado=True, semente=7)),
        )
        n_ruido_sem = sum(1 for v in estado_sem.variables if "ruido" in v)
        n_ruido_com = sum(1 for v in estado_com.variables if "ruido" in v)
        msg = f"seed={seed}: shadow probing piorou ({n_ruido_com} > {n_ruido_sem})"
        assert n_ruido_com <= n_ruido_sem, msg


def test_shadow_probing_desligado_e_o_default_e_nao_muda_comportamento(dataset_com_ruido_forte):
    """Sem shadow probing (default), o comportamento é idêntico ao já validado
    contra o R — greedy puro, sem a nova regra de parada.
    """
    df_dev, df_teste = dataset_com_ruido_forte
    estimator = LogisticGLM()
    metric = KSGaussianMetric(criterio="teste")

    estado_com_config_default, trace = run_level1(
        estimator, metric, df_dev, df_teste, _estado_nulo(estimator, metric, df_dev, df_teste)
    )

    assert not any("shadow_probing" in evento for evento in trace.eventos)
    # base "x1" (a informativa) deve entrar independente do shadow probing
    assert "x1" in {extrair_base(v) for v in estado_com_config_default.variables}
