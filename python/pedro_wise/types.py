"""Protocolos plugáveis (Estimator/Metric) e dataclasses de resultado.

Correção do maior anti-padrão do R original: o algoritmo lá está acoplado a
GLM binomial + KS. Aqui, o estimador e a métrica são injetados — a lógica de
seleção (selection.py) não conhece a implementação de nenhum dos dois.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

import numpy as np
import pandas as pd


class FittedModel(Protocol):
    """Modelo já ajustado. `variables` preserva a ordem usada no fit."""

    @property
    def variables(self) -> tuple[str, ...]: ...

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray: ...


class Estimator(Protocol):
    """Fábrica de modelos ajustados a partir de um subconjunto de colunas."""

    def fit(self, X: pd.DataFrame, y: pd.Series) -> FittedModel: ...


class Metric(Protocol):
    """Métrica de seleção: recebe o modelo ajustado e as bases dev/teste.

    Reproduz a semântica dev/teste do `calc_ks_score` original — a métrica
    decide internamente se usa dev, teste, ou uma combinação penalizada por
    overfit (anti-leakage: nunca decidir com base só no treino).
    """

    def __call__(
        self,
        model: FittedModel,
        X_dev: pd.DataFrame,
        y_dev: pd.Series,
        X_test: pd.DataFrame,
        y_test: pd.Series,
    ) -> float: ...


@dataclass(frozen=True)
class CandidateResult:
    """Resultado de testar uma candidata (variável, par, tripla ou troca).

    Substitui os `data.frame` acumulados via `rbind` no R — os candidatos são
    coletados em uma lista e viram DataFrame de uma vez só, se necessário.

    Carrega o `model` já ajustado (não só o score): corrige o anti-padrão do R
    de refitar o modelo inteiro de novo depois de escolher a melhor candidata.
    """

    added: tuple[str, ...] = ()
    removed: tuple[str, ...] = ()
    score: float = float("-inf")
    model: FittedModel | None = field(default=None, repr=False, compare=False)

    @property
    def is_valid(self) -> bool:
        return self.score != float("-inf")


@dataclass
class SelectionState:
    """Estado corrente da busca: modelo, variáveis e score."""

    variables: tuple[str, ...]
    model: FittedModel
    score: float


#: Default de `n_jobs` calibrado por benchmark (scripts/benchmark_paralelizacao.py):
#: threading com 3-4 workers ganha ~25% em bases de dezenas de milhares de linhas;
#: em bases pequenas (milhares de linhas) o ganho não aparece mas também não há
#: regressão relevante (overhead de thread é sub-segundo). Ajuste para 1 se estiver
#: iterando em datasets de desenvolvimento minúsculos e quiser o mínimo de overhead.
N_JOBS_PADRAO = 4


@dataclass(frozen=True)
class ShadowProbingConfig:
    """Critério de parada opt-in via shadow-variable probing (Thomas et al. 2017)
    — ver `docs/literatura/shadow-variable-probing.md` e `shadow_probing.py`.

    `ativado=False` por padrão: sem custo extra a menos que explicitamente ligado.
    Quando ligado, cada rodada do forward simples paga um scan extra (variáveis
    reais disponíveis + suas sombras) antes de aceitar a candidata vencedora.
    """

    ativado: bool = False
    sufixo: str = "__shadow"
    semente: int | None = None
    n_jobs: int = N_JOBS_PADRAO


@dataclass(frozen=True)
class Level1Config:
    """Flags liga/desliga do nível 1, análogas aos parâmetros `*_nivel_1` do R."""

    forward_simples: bool = True
    transformacao_simples: bool = True
    backward_simples: bool = True
    min_vars_para_backward: int = 5
    n_jobs: int = N_JOBS_PADRAO
    shadow_probing: ShadowProbingConfig = field(default_factory=ShadowProbingConfig)
    # Restrição (não objetivo — quem manda continua sendo o KS): candidatas
    # que ADICIONAM variável só são elegíveis se o p-valor do coeficiente
    # ficar <= isto. `None` desliga (comportamento de sempre). Nunca se
    # aplica a remoções (backward). Ver `selection._passa_significancia`.
    p_valor_maximo: float | None = None


@dataclass(frozen=True)
class Level2Config:
    """Flags e tamanhos do nível 2 (forward duplo) e 2.5 (forward triplo),
    análogas a `*_nivel_2`, `n_best_duplo`, `n_best_triplo_1/2` do R.
    """

    forward_duplo: bool = True
    transformacao_simples: bool = True
    backward_simples: bool = True
    forward_triplo: bool = True
    n_best_duplo: int = 5
    n_best_triplo_1: int = 2
    n_best_triplo_2: int = 2
    min_vars_para_backward: int = 5
    n_jobs: int = N_JOBS_PADRAO
    p_valor_maximo: float | None = None


@dataclass(frozen=True)
class Level3Config:
    """Liga/desliga e limites do nível 3 (backward complexo recursivo),
    análogo a `backward_complexo_nivel_3`/`n_best_backward` do R.

    `ativado=False` por padrão: o próprio script R original chamava
    `Pedro_Wise_3.0(..., backward_complexo_nivel_3 = FALSE)` na prática — é a
    etapa mais cara e combinatorialmente arriscada, opt-in deliberado.
    """

    ativado: bool = False
    n_best_backward: int = 2
    profundidade_maxima: int = 2


@dataclass
class SearchTrace:
    """Histórico de atualizações aceitas nesta rodada — substitui `cat()`/`trace`."""

    eventos: list[str] = field(default_factory=list)

    def registrar(self, evento: str) -> None:
        self.eventos.append(evento)


# Alias: mantido pelo nome usado no nível 1; o mesmo tipo serve para nível 2 e pipeline.
Level1Trace = SearchTrace
