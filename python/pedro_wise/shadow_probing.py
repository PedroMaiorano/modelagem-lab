"""Critério de parada por shadow-variable probing (Thomas, Hepp, Mayr & Bischl,
2017 — ver `docs/literatura/shadow-variable-probing.md`).

Motivação concreta: a validação numérica do port contra o R original
(`docs/algoritmos-originais/pedro-wise-resumo.md`) mostrou o algoritmo aceitando
`x_ruido2_woe` — puro ruído — só por acaso amostral, porque "score não melhorou
mais" é o único critério de parada do nível 1. Shadow-variable probing ataca
exatamente esse ponto cego: aumenta o conjunto de candidatas com cópias
permutadas ("sombra") das variáveis reais e para assim que uma sombra venceria
a rodada — sinal de que a busca está no limite do ruído.

Não é uma `Metric` (protocolo por candidata avaliada) — é uma regra de parada
do laço em `selection.run_level1`, opt-in via `ShadowProbingConfig`.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from pedro_wise.base import variaveis_disponiveis
from pedro_wise.types import Estimator, Metric, ShadowProbingConfig

logger = logging.getLogger(__name__)

_RESPOSTA = "y"


def eh_sombra(variavel: str, sufixo: str = "__shadow") -> bool:
    """Uma variável sombra nunca deve compor o modelo final — só serve de sentinela."""
    return variavel.endswith(sufixo)


def adicionar_variaveis_sombra(
    df: pd.DataFrame, variaveis: list[str], rng: np.random.Generator, sufixo: str = "__shadow"
) -> pd.DataFrame:
    """Anexa uma cópia embaralhada (permutada) de cada variável em `variaveis`,
    com nome `{variavel}{sufixo}`. A permutação quebra toda relação com `y` por
    construção — é o que torna a sombra um sentinela de ruído confiável.

    `extrair_base` nunca confunde uma sombra com sua variável de origem: o
    sufixo `__shadow` (duplo underscore) faz `rsplit("_", 1)` extrair uma base
    própria por sombra (ex.: base de `x1_woe__shadow` é `x1_woe_`, não `x1`),
    então sombras nunca bloqueiam nem são bloqueadas pela semântica de base das
    variáveis reais.
    """
    df_aumentado = df.copy()
    for variavel in variaveis:
        valores = df[variavel].to_numpy(copy=True)
        rng.shuffle(valores)
        df_aumentado[f"{variavel}{sufixo}"] = valores
    return df_aumentado


def deve_parar(
    estimator: Estimator,
    metric: Metric,
    df_dev: pd.DataFrame,
    df_teste: pd.DataFrame,
    variaveis_no_modelo: tuple[str, ...],
    config: ShadowProbingConfig,
) -> bool:
    """`True` se, entre as variáveis reais disponíveis e suas sombras, uma
    sombra teria o melhor score nesta rodada — nunca adiciona a sombra ao
    modelo, só sinaliza que é hora de parar o forward.
    """
    if not config.ativado:
        return False

    from pedro_wise.selection import _melhor, forward_simples  # import tardio evita ciclo

    candidatas_reais = variaveis_disponiveis(variaveis_no_modelo, list(df_dev.columns), _RESPOSTA)
    if not candidatas_reais:
        return False

    rng = np.random.default_rng(config.semente)
    colunas_necessarias = [*variaveis_no_modelo, _RESPOSTA, *candidatas_reais]
    df_dev_aug = adicionar_variaveis_sombra(df_dev[colunas_necessarias], candidatas_reais, rng, config.sufixo)
    df_teste_aug = adicionar_variaveis_sombra(
        df_teste[colunas_necessarias], candidatas_reais, np.random.default_rng(config.semente), config.sufixo
    )

    resultados = forward_simples(
        estimator, metric, df_dev_aug, df_teste_aug, variaveis_no_modelo, config.n_jobs
    )
    melhor = _melhor(resultados)
    if melhor is None:
        return False

    (vencedora,) = melhor.added
    parar = eh_sombra(vencedora, config.sufixo)
    if parar:
        origem = vencedora[: -len(config.sufixo)]
        logger.info("Shadow probing: sombra de %s venceria a rodada — parando", origem)
    return parar
