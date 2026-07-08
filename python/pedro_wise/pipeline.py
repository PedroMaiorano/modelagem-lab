"""Orquestrador da busca completa: nível 1 (repetido até convergir) -> nível 2
-> nível 2.5 -> volta ao nível 1 sempre que algum nível melhora.

Port do laço principal `while (modelo_melhorado)` em `Pedro_Wise_3.0` (R), com
uma simplificação estrutural: o R controla a escalada de nível via uma
variável global mutável (`nivel_atual`) reatribuída em vários pontos; aqui o
mesmo comportamento observável emerge de um laço explícito sem estado
escondido. O nível 3 (backward complexo recursivo) ainda não foi portado —
ver docs/algoritmos-originais/pedro-wise-resumo.md.
"""

from __future__ import annotations

import logging

import pandas as pd

from pedro_wise.level2 import tentar_nivel2, tentar_nivel_triplo
from pedro_wise.selection import run_level1
from pedro_wise.types import Estimator, Level1Config, Level2Config, Metric, SearchTrace, SelectionState

logger = logging.getLogger(__name__)


def run_pedro_wise(
    estimator: Estimator,
    metric: Metric,
    df_dev: pd.DataFrame,
    df_teste: pd.DataFrame,
    estado_inicial: SelectionState,
    config1: Level1Config | None = None,
    config2: Level2Config | None = None,
) -> tuple[SelectionState, SearchTrace]:
    """Alterna nível 1 (repetido até convergir) com upgrades de nível 2 e 2.5.

    Sempre que um upgrade de nível 2/2.5 melhora o score, volta para o nível 1
    — mesma semântica do `nivel_atual <- 1` no R após qualquer melhora. Para
    quando nenhum dos níveis portados melhora mais.
    """
    config1 = config1 or Level1Config()
    config2 = config2 or Level2Config()
    trace = SearchTrace()

    estado = estado_inicial
    while True:
        estado, trace_l1 = run_level1(estimator, metric, df_dev, df_teste, estado, config1)
        trace.eventos.extend(trace_l1.eventos)

        estado, melhorou_l2, trace_l2 = tentar_nivel2(estimator, metric, df_dev, df_teste, estado, config2)
        trace.eventos.extend(trace_l2.eventos)
        if melhorou_l2:
            logger.info("Nível 2 melhorou — voltando ao nível 1")
            continue

        estado, melhorou_l25, trace_l25 = tentar_nivel_triplo(
            estimator, metric, df_dev, df_teste, estado, config2
        )
        trace.eventos.extend(trace_l25.eventos)
        if melhorou_l25:
            logger.info("Nível 2.5 melhorou — voltando ao nível 1")
            continue

        break

    return estado, trace
