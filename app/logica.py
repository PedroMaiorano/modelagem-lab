"""Camada de lógica do dashboard: só consome `python/pedro_wise` (o core) —
nunca reimplementa seleção/métricas aqui. Interface fina entre Streamlit e o
port.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "python"))

import pandas as pd
from pedro_wise.estimators import LogisticGLM
from pedro_wise.metrics import KSGaussianMetric
from pedro_wise.pipeline import run_pedro_wise
from pedro_wise.types import Level1Config, Level2Config, SelectionState, ShadowProbingConfig

_RAIZ = Path(__file__).resolve().parent.parent
DIR_DADOS = _RAIZ / "data"


def listar_datasets() -> list[str]:
    """Pastas em data/ com dev.csv + teste.csv (gerados pelos scripts/gerar_*)."""
    if not DIR_DADOS.exists():
        return []

    def _tem_dev_e_teste(p: Path) -> bool:
        return p.is_dir() and (p / "dev.csv").exists() and (p / "teste.csv").exists()

    return sorted(p.name for p in DIR_DADOS.iterdir() if _tem_dev_e_teste(p))


def carregar_dataset(nome: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    pasta = DIR_DADOS / nome
    return pd.read_csv(pasta / "dev.csv"), pd.read_csv(pasta / "teste.csv")


@dataclass
class ResultadoSelecao:
    variaveis: tuple[str, ...]
    ks_dev: float
    ks_teste: float
    auc_teste: float
    eventos: list[str]
    ks_por_passo: list[float]


def _extrair_ks_dos_eventos(eventos: list[str]) -> list[float]:
    """Regex sobre o texto do trace (`"... => score=0.1234"`) para desenhar a
    curva de progresso — só para exibição; a lógica de seleção em si não
    expõe uma série temporal estruturada (não é necessária pro core).
    """
    valores = []
    for evento in eventos:
        m = re.search(r"score=([\d.]+)", evento)
        if m:
            valores.append(float(m.group(1)))
    return valores


def rodar_selecao(
    df_dev: pd.DataFrame,
    df_teste: pd.DataFrame,
    *,
    criterio: str = "teste",
    forward_simples: bool = True,
    transformacao_simples: bool = True,
    backward_simples: bool = True,
    forward_duplo: bool = True,
    forward_triplo: bool = True,
    shadow_probing: bool = False,
    n_best_duplo: int = 5,
    n_best_triplo_1: int = 3,
    n_best_triplo_2: int = 3,
) -> ResultadoSelecao:
    from sklearn.metrics import roc_auc_score

    estimator = LogisticGLM()
    metric = KSGaussianMetric(criterio=criterio)  # type: ignore[arg-type]

    modelo_nulo = estimator.fit(df_dev[[]], df_dev["y"])
    score_nulo = metric(modelo_nulo, df_dev[[]], df_dev["y"], df_teste[[]], df_teste["y"])
    estado_inicial = SelectionState(variables=(), model=modelo_nulo, score=score_nulo)

    config1 = Level1Config(
        forward_simples=forward_simples,
        transformacao_simples=transformacao_simples,
        backward_simples=backward_simples,
        shadow_probing=ShadowProbingConfig(ativado=shadow_probing, semente=7),
    )
    config2 = Level2Config(
        forward_duplo=forward_duplo,
        forward_triplo=forward_triplo,
        n_best_duplo=n_best_duplo,
        n_best_triplo_1=n_best_triplo_1,
        n_best_triplo_2=n_best_triplo_2,
    )

    estado_final, trace = run_pedro_wise(
        estimator, metric, df_dev, df_teste, estado_inicial, config1, config2
    )

    metric_teste = KSGaussianMetric(criterio="teste")
    metric_dev = KSGaussianMetric(criterio="dev")
    variaveis = list(estado_final.variables)
    if variaveis:
        X_dev, y_dev = df_dev[variaveis], df_dev["y"]
        X_teste, y_teste = df_teste[variaveis], df_teste["y"]
        ks_teste = metric_teste(estado_final.model, X_dev, y_dev, X_teste, y_teste)
        ks_dev = metric_dev(estado_final.model, X_dev, y_dev, X_teste, y_teste)
        prob_teste = estado_final.model.predict_proba(X_teste)
        auc_teste = float(roc_auc_score(df_teste["y"], prob_teste))
    else:
        ks_teste = ks_dev = 0.0
        auc_teste = 0.5

    return ResultadoSelecao(
        variaveis=estado_final.variables,
        ks_dev=ks_dev,
        ks_teste=ks_teste,
        auc_teste=auc_teste,
        eventos=trace.eventos,
        ks_por_passo=_extrair_ks_dos_eventos(trace.eventos),
    )
