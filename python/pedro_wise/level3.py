"""Nível 3: backward complexo recursivo.

Port do bloco `if (nivel_atual == 3)` em `Pedro_Wise_3.0` (R): para cada uma das
`n_best_backward` variáveis mais promissoras de remover (rankeadas por
`backward_simples`), a variável é removida do **universo de dados** — não só do
modelo — e a busca completa (níveis 1, 2 e 2.5) é re-executada do zero a partir
dali. Os ramos resultantes são comparados; o melhor substitui o modelo atual se
superar o score de entrada.

Anti-padrões do R corrigidos aqui (ver docs/algoritmos-originais/pedro-wise-resumo.md):

- **Bug do R**: ao aceitar o melhor ramo, o original recalculava `ks_atual` a
  partir do *último* `modelo_bwc` da variável de laço (`calc_ks_local(modelo_bwc)`),
  não do melhor ramo de fato escolhido (`Resultado_backward_complexo$modelo[[1]]`).
  Aqui o score aceito é sempre, por construção, o do ramo vencedor.
- **Recursão sem memoização**: cada nível 3 gera até `n_best_backward` sub-buscas
  completas, cada uma podendo gerar outras — risco de explosão combinatorial.
  Aqui memoizamos por `(colunas disponíveis, variáveis no modelo)` e limitamos a
  `profundidade_maxima`.
"""

from __future__ import annotations

import logging

import pandas as pd

from pedro_wise.pipeline import run_pedro_wise
from pedro_wise.selection import backward_simples
from pedro_wise.types import (
    Estimator,
    Level1Config,
    Level2Config,
    Level3Config,
    Metric,
    SearchTrace,
    SelectionState,
)

logger = logging.getLogger(__name__)

# Chave de memoização: universo de colunas ainda disponíveis + variáveis já no modelo.
_CacheKey = tuple[frozenset[str], frozenset[str]]
_Cache = dict[_CacheKey, tuple[SelectionState, SearchTrace]]


def _chave_cache(colunas_disponiveis: frozenset[str], variaveis_modelo: tuple[str, ...]) -> _CacheKey:
    return colunas_disponiveis, frozenset(variaveis_modelo)


def run_pedro_wise_completo(
    estimator: Estimator,
    metric: Metric,
    df_dev: pd.DataFrame,
    df_teste: pd.DataFrame,
    estado_inicial: SelectionState,
    config1: Level1Config | None = None,
    config2: Level2Config | None = None,
    config3: Level3Config | None = None,
    cache: _Cache | None = None,
    _profundidade: int = 0,
) -> tuple[SelectionState, SearchTrace]:
    """Busca completa: níveis 1/2/2.5 (`run_pedro_wise`) seguidos, se
    `config3.ativado`, do nível 3 (backward complexo). Port do laço principal
    completo de `Pedro_Wise_3.0` (R), incluindo a recursão do nível 3.

    `cache` pode ser passado explicitamente para reaproveitar sub-buscas entre
    chamadas top-level (ex.: comparando `n_best_backward` diferentes sobre o
    mesmo dataset); por padrão cada chamada usa um cache novo.
    """
    config1 = config1 or Level1Config()
    config2 = config2 or Level2Config()
    config3 = config3 or Level3Config()
    cache = cache if cache is not None else {}

    estado, trace = run_pedro_wise(estimator, metric, df_dev, df_teste, estado_inicial, config1, config2)

    pode_recursar = (
        config3.ativado
        and _profundidade < config3.profundidade_maxima
        and len(estado.variables) > config1.min_vars_para_backward
    )
    if not pode_recursar:
        return estado, trace

    candidatos_remover = backward_simples(
        estimator, metric, df_dev, df_teste, estado.variables, config1.n_jobs
    )
    if not candidatos_remover:
        return estado, trace

    candidatos_remover = sorted(candidatos_remover, key=lambda c: c.score, reverse=True)
    candidatos_remover = candidatos_remover[: config3.n_best_backward]

    # Marcador de início — cada candidato dispara uma sub-busca completa
    # (1+2+2.5) que também loga forward_simples/transformacao_simples/etc.
    # através do MESMO logger global. Sem esse marcador (e o de fechamento
    # logo abaixo, nos dois desfechos possíveis), quem consome o log ao vivo
    # não tem como distinguir "isso é exploração de um ramo que pode ser
    # descartado" de "isso é uma atualização real aceita no modelo".
    logger.info(
        "Nível 3: avaliando %d candidato(s) de remoção (profundidade %d)",
        len(candidatos_remover),
        _profundidade + 1,
    )

    melhor_ramo: SelectionState | None = None
    melhor_trace_ramo = SearchTrace()

    for candidato in candidatos_remover:
        var_remover = candidato.removed[0]
        if candidato.model is None:
            continue

        df_dev_reduzido = df_dev.drop(columns=[var_remover])
        df_teste_reduzido = df_teste.drop(columns=[var_remover])
        variaveis_ramo = tuple(v for v in estado.variables if v != var_remover)

        chave = _chave_cache(frozenset(df_dev_reduzido.columns) - {"y"}, variaveis_ramo)
        if chave in cache:
            estado_ramo, trace_ramo = cache[chave]
            logger.debug("Nível 3: cache hit ao remover %s", var_remover)
        else:
            estado_ramo_inicial = SelectionState(
                variables=variaveis_ramo, model=candidato.model, score=candidato.score
            )
            estado_ramo, trace_ramo = run_pedro_wise_completo(
                estimator,
                metric,
                df_dev_reduzido,
                df_teste_reduzido,
                estado_ramo_inicial,
                config1,
                config2,
                config3,
                cache=cache,
                _profundidade=_profundidade + 1,
            )
            cache[chave] = (estado_ramo, trace_ramo)

        if melhor_ramo is None or estado_ramo.score > melhor_ramo.score:
            melhor_ramo, melhor_trace_ramo = estado_ramo, trace_ramo

    if melhor_ramo is not None and melhor_ramo.score > estado.score:
        # O ramo vencedor roda uma busca completa (1+2+2.5) num universo sem a
        # variável removida — o conjunto final pode ser totalmente diferente
        # do modelo anterior, não só "+1/-1" variável. Sem listar as
        # variáveis aqui, quem consome o log (ex.: a UI, pra mostrar "modelo
        # atual" ao vivo) não tem como saber o estado real após este evento.
        variaveis_ramo_vencedor = ",".join(melhor_ramo.variables)
        logger.info(
            "Nível 3: ramo vencedor supera o modelo atual => score=%.4f | variaveis=%s",
            melhor_ramo.score,
            variaveis_ramo_vencedor,
        )
        trace.registrar(
            "backward_complexo: ramo vencedor => "
            f"score={melhor_ramo.score:.4f} | variaveis={variaveis_ramo_vencedor}"
        )
        trace.eventos.extend(melhor_trace_ramo.eventos)
        return melhor_ramo, trace

    # Marcador de fechamento do outro desfecho possível: nenhum candidato
    # superou o modelo atual, então tudo que os ramos exploraram (e já foi
    # logado ao vivo) deve ser descartado — sem esta linha, o consumidor do
    # log não tem como saber que a exploração acabou sem produzir nada.
    logger.info("Nível 3: nenhum ramo superou o modelo atual => score=%.4f", estado.score)
    return estado, trace
