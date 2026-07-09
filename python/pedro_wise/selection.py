"""Nível 1 da seleção stepwise: forward simples, transformação simples, backward simples.

Port de `forward_simples`, `teste_troca_simples`, `backward_simples` e do laço do
"Nível 1" em `Pedro_Wise_3.0` (R). Correções em relação ao original:

- Candidatos são avaliados em paralelo (`joblib.Parallel`) — no R cada fit era
  sequencial apesar de independente.
- Resultados são acumulados em lista + `pd.DataFrame` uma vez, nunca via
  `rbind` em loop (O(n²) -> O(n)).
- O modelo vencedor de cada etapa já vem ajustado do candidato — sem refit.
- Logging estruturado (`logging`) no lugar de `cat()`; nível de verbosidade
  configurável em vez do `trace: bool` binário.
- Métrica e estimador são injetados (`Metric`, `Estimator`) — nada de KS/binomial hardcoded.

## Paralelização: por que `threading`, não o `loky` (processos) default do joblib

Medido em `scripts/benchmark_paralelizacao.py`. Dois cenários importam:

- **Chamada isolada** (uma única `Parallel()`, processo novo): `loky` paga o
  custo de subir o pool de processos e copiar `df_dev`/`df_teste` para cada
  worker a cada chamada — em bases pequenas isso o torna 8-10x mais lento que
  sequencial. `threading` não copia nada (memória compartilhada) e empata com
  sequencial nesse caso (sem ganho, sem perda relevante).
- **Uso real** (`run_level1`/`run_pedro_wise`, dezenas de chamadas a `Parallel()`
  na mesma busca): o pool é reaproveitado entre chamadas, então o custo fixo
  do `loky` amortiza. Medido em `run_level1` completo (30 candidatas, 15k
  linhas, convergindo para 11 variáveis): sequencial 64.7s, `threading
  n_jobs=4` 22.4s (**2.9x**), `loky n_jobs=4` 26.1s (2.5x). `threading` vence
  em ambos os regimes, por isso é o backend fixo aqui.

Ganho real, portanto, aparece no uso normal (buscas completas, não uma
única comparação de candidatas). Para datasets de desenvolvimento minúsculos
com poucas iterações, `n_jobs=1` continua sendo uma opção razoável.
"""

from __future__ import annotations

import logging

import pandas as pd
from joblib import Parallel, delayed

from pedro_wise.base import extrair_base, variaveis_disponiveis, versoes_alternativas
from pedro_wise.types import (
    CandidateResult,
    Estimator,
    FittedModel,
    Level1Config,
    Level1Trace,
    Metric,
    SelectionState,
)

logger = logging.getLogger(__name__)

_RESPOSTA = "y"

# Ver docstring do módulo: threading evita a cópia de df_dev/df_teste por worker
# que torna o backend default (loky, baseado em processos) mais lento que sequencial.
PARALLEL_BACKEND = "threading"


def _tentar_fit_score(
    estimator: Estimator,
    metric: Metric,
    df_dev: pd.DataFrame,
    df_teste: pd.DataFrame,
    variaveis: tuple[str, ...],
) -> tuple[FittedModel, float] | None:
    """Ajusta o modelo com `variaveis` e calcula a métrica. `None` em caso de falha
    de ajuste (singularidade, separação perfeita etc.) — equivalente ao `tryCatch`
    envolvendo cada `glm()` no R.
    """
    try:
        modelo = estimator.fit(df_dev[list(variaveis)], df_dev[_RESPOSTA])
        score = metric(
            modelo,
            df_dev[list(variaveis)],
            df_dev[_RESPOSTA],
            df_teste[list(variaveis)],
            df_teste[_RESPOSTA],
        )
    except Exception:
        logger.debug("Falha ao ajustar candidata %s", variaveis, exc_info=True)
        return None
    return modelo, score


def forward_simples(
    estimator: Estimator,
    metric: Metric,
    df_dev: pd.DataFrame,
    df_teste: pd.DataFrame,
    variaveis_no_modelo: tuple[str, ...],
    n_jobs: int = 1,
) -> list[CandidateResult]:
    """Testa adicionar, uma de cada vez, cada variável fora do modelo (base ainda
    não usada). Port de `forward_simples` (R).
    """
    candidatas = variaveis_disponiveis(variaveis_no_modelo, list(df_dev.columns), _RESPOSTA)
    if not candidatas:
        logger.info("Forward simples: sem variáveis disponíveis")
        return []

    def _avaliar(v: str) -> CandidateResult | None:
        resultado = _tentar_fit_score(estimator, metric, df_dev, df_teste, (*variaveis_no_modelo, v))
        if resultado is None:
            return None
        modelo, score = resultado
        return CandidateResult(added=(v,), score=score, model=modelo)

    resultados = Parallel(n_jobs=n_jobs, backend=PARALLEL_BACKEND)(delayed(_avaliar)(v) for v in candidatas)
    return [r for r in resultados if r is not None]


def transformacao_simples(
    estimator: Estimator,
    metric: Metric,
    df_dev: pd.DataFrame,
    df_teste: pd.DataFrame,
    variaveis_no_modelo: tuple[str, ...],
    n_jobs: int = 1,
) -> list[CandidateResult]:
    """Para cada variável no modelo, testa trocar por outra versão (transformação)
    da MESMA base. Port de `teste_troca_simples` (R).
    """
    pares: list[tuple[str, str]] = []
    for var_out in variaveis_no_modelo:
        for var_in in versoes_alternativas(var_out, list(df_dev.columns)):
            if extrair_base(var_in) == extrair_base(var_out):
                pares.append((var_out, var_in))

    if not pares:
        logger.info("Transformação simples: sem versões alternativas disponíveis")
        return []

    def _avaliar(par: tuple[str, str]) -> CandidateResult | None:
        var_out, var_in = par
        novas_variaveis = tuple(v for v in variaveis_no_modelo if v != var_out) + (var_in,)
        resultado = _tentar_fit_score(estimator, metric, df_dev, df_teste, novas_variaveis)
        if resultado is None:
            return None
        modelo, score = resultado
        return CandidateResult(added=(var_in,), removed=(var_out,), score=score, model=modelo)

    resultados = Parallel(n_jobs=n_jobs, backend=PARALLEL_BACKEND)(delayed(_avaliar)(p) for p in pares)
    return [r for r in resultados if r is not None]


def backward_simples(
    estimator: Estimator,
    metric: Metric,
    df_dev: pd.DataFrame,
    df_teste: pd.DataFrame,
    variaveis_no_modelo: tuple[str, ...],
    n_jobs: int = 1,
) -> list[CandidateResult]:
    """Testa remover, uma de cada vez, cada variável do modelo. Port de
    `backward_simples` (R).
    """
    if not variaveis_no_modelo:
        return []

    def _avaliar(v: str) -> CandidateResult | None:
        novas_variaveis = tuple(x for x in variaveis_no_modelo if x != v)
        if not novas_variaveis:
            return None
        resultado = _tentar_fit_score(estimator, metric, df_dev, df_teste, novas_variaveis)
        if resultado is None:
            return None
        modelo, score = resultado
        return CandidateResult(removed=(v,), score=score, model=modelo)

    resultados = Parallel(n_jobs=n_jobs, backend=PARALLEL_BACKEND)(
        delayed(_avaliar)(v) for v in variaveis_no_modelo
    )
    return [r for r in resultados if r is not None]


def _passa_significancia(candidato: CandidateResult, p_valor_maximo: float) -> bool:
    """`p_valor_maximo` é uma RESTRIÇÃO, não um critério de otimização — o KS
    continua mandando (`_melhor` ainda escolhe por `score`), isto só reduz o
    conjunto de candidatas elegíveis. Só se aplica a candidatas que
    ADICIONAM variável (`candidato.added` não vazio) — remoções (backward)
    nunca são bloqueadas por p-valor, faz sentido sempre poder simplificar
    o modelo. Reavaliado a cada rodada do laço (`run_level1`/`run_level2`
    chamam isto de novo a cada iteração): uma variável não-significativa
    agora pode passar a ser significativa numa rodada futura, conforme o
    conjunto de covariáveis muda — nunca fica banida permanentemente.

    `FittedModel` (Protocol) não garante `estatisticas()` — só
    `LogisticGLM` (o único estimador linear hoje) tem; pra outros
    estimadores (hipotéticos, sem p-valor), a restrição é ignorada (não
    filtra) em vez de quebrar.
    """
    if not candidato.added or candidato.model is None:
        return True
    estatisticas = getattr(candidato.model, "estatisticas", None)
    if estatisticas is None:
        return True
    stats = estatisticas()
    return all(stats.get(v, {}).get("p_valor", 0.0) <= p_valor_maximo for v in candidato.added)


def _melhor(
    candidatos: list[CandidateResult], p_valor_maximo: float | None = None
) -> CandidateResult | None:
    validos = [c for c in candidatos if c.is_valid]
    if p_valor_maximo is not None:
        validos = [c for c in validos if _passa_significancia(c, p_valor_maximo)]
    if not validos:
        return None
    return max(validos, key=lambda c: c.score)


def run_level1(
    estimator: Estimator,
    metric: Metric,
    df_dev: pd.DataFrame,
    df_teste: pd.DataFrame,
    estado_inicial: SelectionState,
    config: Level1Config | None = None,
) -> tuple[SelectionState, Level1Trace]:
    """Laço do Nível 1: aplica forward simples, transformação simples e backward
    simples repetidamente enquanto a métrica melhorar. Port do bloco
    `if (nivel_atual == 1)` em `Pedro_Wise_3.0` (R), sem a escalada para os
    níveis 2/2.5/3 (ainda não portados).
    """
    config = config or Level1Config()
    trace = Level1Trace()

    estado = estado_inicial
    melhorou = True

    while melhorou:
        melhorou = False

        if config.forward_simples:
            from pedro_wise.shadow_probing import deve_parar  # import tardio evita ciclo

            parar_por_sombra = deve_parar(
                estimator, metric, df_dev, df_teste, estado.variables, config.shadow_probing
            )
            if parar_por_sombra:
                trace.registrar("shadow_probing: parada do forward — próxima candidata seria ruído")
                logger.info("Shadow probing: forward_simples suspenso nesta rodada (limite de ruído)")

            if not parar_por_sombra:
                candidatos = forward_simples(
                    estimator, metric, df_dev, df_teste, estado.variables, config.n_jobs
                )
                melhor = _melhor(candidatos, config.p_valor_maximo)
                if melhor is not None and melhor.score > estado.score and melhor.model is not None:
                    nova_var = melhor.added[0]
                    estado = SelectionState(
                        variables=(*estado.variables, nova_var), model=melhor.model, score=melhor.score
                    )
                    melhorou = True
                    trace.registrar(f"forward_simples: +{nova_var} => score={melhor.score:.4f}")
                    logger.info("forward_simples: +%s => score=%.4f", nova_var, melhor.score)

        if config.transformacao_simples:
            candidatos = transformacao_simples(
                estimator, metric, df_dev, df_teste, estado.variables, config.n_jobs
            )
            melhor = _melhor(candidatos, config.p_valor_maximo)
            if melhor is not None and melhor.score > estado.score and melhor.model is not None:
                var_out, var_in = melhor.removed[0], melhor.added[0]
                novas_variaveis = tuple(v for v in estado.variables if v != var_out) + (var_in,)
                estado = SelectionState(variables=novas_variaveis, model=melhor.model, score=melhor.score)
                melhorou = True
                trace.registrar(f"transformacao_simples: -{var_out} +{var_in} => score={melhor.score:.4f}")
                logger.info("transformacao_simples: -%s +%s => score=%.4f", var_out, var_in, melhor.score)

        if config.backward_simples and len(estado.variables) > config.min_vars_para_backward:
            candidatos = backward_simples(
                estimator, metric, df_dev, df_teste, estado.variables, config.n_jobs
            )
            melhor = _melhor(candidatos)
            if melhor is not None and melhor.score > estado.score and melhor.model is not None:
                var_removida = melhor.removed[0]
                novas_variaveis = tuple(v for v in estado.variables if v != var_removida)
                estado = SelectionState(variables=novas_variaveis, model=melhor.model, score=melhor.score)
                melhorou = True
                trace.registrar(f"backward_simples: -{var_removida} => score={melhor.score:.4f}")
                logger.info("backward_simples: -%s => score=%.4f", var_removida, melhor.score)

    return estado, trace
