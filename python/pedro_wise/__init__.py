"""Port Python do Pedro_Wise — seleção stepwise multi-nível de variáveis.

Níveis 1 (forward/troca/backward simples), 2 (forward duplo), 2.5 (forward
triplo) e 3 (backward complexo recursivo, opt-in) implementados — ver
docs/algoritmos-originais/pedro-wise-resumo.md.
"""

from pedro_wise.base import extrair_base, variaveis_disponiveis, versoes_alternativas
from pedro_wise.estimators import LogisticGLM
from pedro_wise.level2 import forward_duplo, forward_triplo, tentar_nivel2, tentar_nivel_triplo
from pedro_wise.level3 import run_pedro_wise_completo
from pedro_wise.metrics import AUCMetric, KSGaussianMetric
from pedro_wise.pipeline import run_pedro_wise
from pedro_wise.selection import backward_simples, forward_simples, run_level1, transformacao_simples
from pedro_wise.types import (
    CandidateResult,
    Estimator,
    Level1Config,
    Level1Trace,
    Level2Config,
    Level3Config,
    Metric,
    SearchTrace,
    SelectionState,
)

__all__ = [
    "extrair_base",
    "variaveis_disponiveis",
    "versoes_alternativas",
    "LogisticGLM",
    "forward_duplo",
    "forward_triplo",
    "tentar_nivel2",
    "tentar_nivel_triplo",
    "run_pedro_wise_completo",
    "AUCMetric",
    "KSGaussianMetric",
    "run_pedro_wise",
    "backward_simples",
    "forward_simples",
    "run_level1",
    "transformacao_simples",
    "CandidateResult",
    "Estimator",
    "Level1Config",
    "Level1Trace",
    "Level2Config",
    "Level3Config",
    "Metric",
    "SearchTrace",
    "SelectionState",
]
