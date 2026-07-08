"""Nível 2 (forward duplo) e nível 2.5 (forward triplo) da seleção stepwise.

Port de `forward_duplo`, `forward_triplo` e dos blocos `nivel_atual == 2` /
`nivel_atual == 2.5` em `Pedro_Wise_3.0` (R). Reaproveita `transformacao_simples`
e `backward_simples` do nível 1 (mesma lógica, aplicada sobre o estado do nível 2).

Diferença de design em relação ao R: aqui cada `tentar_nivel*` faz uma única
passada (fiel ao original) e devolve se melhorou; quem decide voltar ao nível 1
ou escalar para o próximo nível é o pipeline (pipeline.py), não um estado global
mutável com variável `nivel_atual`.
"""

from __future__ import annotations

import logging

import pandas as pd
from joblib import Parallel, delayed

from pedro_wise.base import variaveis_disponiveis
from pedro_wise.selection import (
    PARALLEL_BACKEND,
    _melhor,
    _tentar_fit_score,
    backward_simples,
    forward_simples,
    transformacao_simples,
)
from pedro_wise.types import CandidateResult, Estimator, Level2Config, Metric, SearchTrace, SelectionState

logger = logging.getLogger(__name__)


def forward_duplo(
    estimator: Estimator,
    metric: Metric,
    df_dev: pd.DataFrame,
    df_teste: pd.DataFrame,
    variaveis_no_modelo: tuple[str, ...],
    n_best_duplo: int = 5,
    n_jobs: int = 1,
) -> list[CandidateResult]:
    """Pega as `n_best_duplo` melhores candidatas do forward simples e testa
    cada uma combinada em par com as demais variáveis disponíveis (evitando
    combinações repetidas/base duplicada). Port de `forward_duplo` (R).
    """
    simples = forward_simples(estimator, metric, df_dev, df_teste, variaveis_no_modelo, n_jobs)
    if not simples:
        logger.info("Forward duplo: sem resultado do forward simples para combinar")
        return []

    top = sorted(simples, key=lambda c: c.score, reverse=True)[:n_best_duplo]
    disponiveis = variaveis_disponiveis(variaveis_no_modelo, list(df_dev.columns))

    pares: list[tuple[str, str]] = []
    historico: list[str] = []
    for cand in top:
        v = cand.added[0]
        restantes = [w for w in disponiveis if w not in historico]
        candidatas_w = variaveis_disponiveis((v,), restantes)
        historico.append(v)
        pares.extend((v, w) for w in candidatas_w)

    if not pares:
        logger.info("Forward duplo: nenhum par disponível")
        return []

    def _avaliar(par: tuple[str, str]) -> CandidateResult | None:
        v, w = par
        resultado = _tentar_fit_score(estimator, metric, df_dev, df_teste, (*variaveis_no_modelo, v, w))
        if resultado is None:
            return None
        modelo, score = resultado
        return CandidateResult(added=(v, w), score=score, model=modelo)

    resultados = Parallel(n_jobs=n_jobs, backend=PARALLEL_BACKEND)(delayed(_avaliar)(p) for p in pares)
    return [r for r in resultados if r is not None]


def forward_triplo(
    estimator: Estimator,
    metric: Metric,
    df_dev: pd.DataFrame,
    df_teste: pd.DataFrame,
    variaveis_no_modelo: tuple[str, ...],
    n_best_duplo: int = 5,
    n_best_triplo_1: int = 2,
    n_best_triplo_2: int = 2,
    n_jobs: int = 1,
) -> list[CandidateResult]:
    """Combina os melhores pares do forward duplo em triplas: top
    `n_best_triplo_1` valores distintos de var1 (por ordem de melhor score),
    cada um com até `n_best_triplo_2` pares. Port de `forward_triplo` (R).
    """
    duplos = forward_duplo(estimator, metric, df_dev, df_teste, variaveis_no_modelo, n_best_duplo, n_jobs)
    if not duplos:
        logger.info("Forward triplo: sem resultado do forward duplo para combinar")
        return []

    duplos_ordenados = sorted(duplos, key=lambda c: c.score, reverse=True)
    var1_ordenados: list[str] = []
    for c in duplos_ordenados:
        v1 = c.added[0]
        if v1 not in var1_ordenados:
            var1_ordenados.append(v1)
        if len(var1_ordenados) >= n_best_triplo_1:
            break

    triplas: list[tuple[str, str, str]] = []
    for v1 in var1_ordenados:
        melhores_pares_v1 = [c for c in duplos_ordenados if c.added[0] == v1][:n_best_triplo_2]
        for c in melhores_pares_v1:
            v2 = c.added[1]
            vars_atuais = (*variaveis_no_modelo, v1, v2)
            for z in variaveis_disponiveis(vars_atuais, list(df_dev.columns)):
                triplas.append((v1, v2, z))

    if not triplas:
        logger.info("Forward triplo: nenhuma tripla disponível")
        return []

    def _avaliar(tripla: tuple[str, str, str]) -> CandidateResult | None:
        v1, v2, z = tripla
        resultado = _tentar_fit_score(
            estimator, metric, df_dev, df_teste, (*variaveis_no_modelo, v1, v2, z)
        )
        if resultado is None:
            return None
        modelo, score = resultado
        return CandidateResult(added=(v1, v2, z), score=score, model=modelo)

    resultados = Parallel(n_jobs=n_jobs, backend=PARALLEL_BACKEND)(delayed(_avaliar)(t) for t in triplas)
    return [r for r in resultados if r is not None]


def tentar_nivel2(
    estimator: Estimator,
    metric: Metric,
    df_dev: pd.DataFrame,
    df_teste: pd.DataFrame,
    estado: SelectionState,
    config: Level2Config,
) -> tuple[SelectionState, bool, SearchTrace]:
    """Uma passada de nível 2: forward duplo, troca simples, backward simples,
    cada etapa só aplicada se melhora o score corrente. Port do bloco
    `if (nivel_atual == 2)` (R).
    """
    trace = SearchTrace()
    novo_estado = estado
    melhorou_algo = False

    if config.forward_duplo:
        candidatos = forward_duplo(
            estimator, metric, df_dev, df_teste, novo_estado.variables, config.n_best_duplo, config.n_jobs
        )
        melhor = _melhor(candidatos)
        if melhor is not None and melhor.score > novo_estado.score and melhor.model is not None:
            v, w = melhor.added
            novo_estado = SelectionState(
                variables=(*novo_estado.variables, v, w), model=melhor.model, score=melhor.score
            )
            melhorou_algo = True
            trace.registrar(f"forward_duplo: +{v} +{w} => score={melhor.score:.4f}")
            logger.info("forward_duplo: +%s +%s => score=%.4f", v, w, melhor.score)

    if config.transformacao_simples:
        candidatos = transformacao_simples(
            estimator, metric, df_dev, df_teste, novo_estado.variables, config.n_jobs
        )
        melhor = _melhor(candidatos)
        if melhor is not None and melhor.score > novo_estado.score and melhor.model is not None:
            var_out, var_in = melhor.removed[0], melhor.added[0]
            novas_variaveis = tuple(v for v in novo_estado.variables if v != var_out) + (var_in,)
            novo_estado = SelectionState(variables=novas_variaveis, model=melhor.model, score=melhor.score)
            melhorou_algo = True
            evento = f"transformacao_simples[nivel2]: -{var_out} +{var_in} => score={melhor.score:.4f}"
            trace.registrar(evento)
            logger.info("transformacao_simples[nivel2]: -%s +%s => score=%.4f", var_out, var_in, melhor.score)

    if config.backward_simples and len(novo_estado.variables) > config.min_vars_para_backward:
        candidatos = backward_simples(
            estimator, metric, df_dev, df_teste, novo_estado.variables, config.n_jobs
        )
        melhor = _melhor(candidatos)
        if melhor is not None and melhor.score > novo_estado.score and melhor.model is not None:
            var_removida = melhor.removed[0]
            novas_variaveis = tuple(v for v in novo_estado.variables if v != var_removida)
            novo_estado = SelectionState(variables=novas_variaveis, model=melhor.model, score=melhor.score)
            melhorou_algo = True
            trace.registrar(f"backward_simples[nivel2]: -{var_removida} => score={melhor.score:.4f}")
            logger.info("backward_simples[nivel2]: -%s => score=%.4f", var_removida, melhor.score)

    return novo_estado, melhorou_algo, trace


def tentar_nivel_triplo(
    estimator: Estimator,
    metric: Metric,
    df_dev: pd.DataFrame,
    df_teste: pd.DataFrame,
    estado: SelectionState,
    config: Level2Config,
) -> tuple[SelectionState, bool, SearchTrace]:
    """Uma passada de nível 2.5: forward triplo. Port do bloco
    `if (nivel_atual == 2.5)` (R).
    """
    trace = SearchTrace()
    if not config.forward_triplo:
        return estado, False, trace

    candidatos = forward_triplo(
        estimator,
        metric,
        df_dev,
        df_teste,
        estado.variables,
        config.n_best_duplo,
        config.n_best_triplo_1,
        config.n_best_triplo_2,
        config.n_jobs,
    )
    melhor = _melhor(candidatos)
    if melhor is not None and melhor.score > estado.score and melhor.model is not None:
        v1, v2, v3 = melhor.added
        novo_estado = SelectionState(
            variables=(*estado.variables, v1, v2, v3), model=melhor.model, score=melhor.score
        )
        trace.registrar(f"forward_triplo: +{v1} +{v2} +{v3} => score={melhor.score:.4f}")
        logger.info("forward_triplo: +%s +%s +%s => score=%.4f", v1, v2, v3, melhor.score)
        return novo_estado, True, trace

    return estado, False, trace
