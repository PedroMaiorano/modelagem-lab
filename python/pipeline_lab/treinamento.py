"""Treinamento — o "famigerado" Pedro_Wise (`python/pedro_wise`), a busca
stepwise (forward/backward, níveis 1 a 3) que decide quais variáveis
entram no modelo final. Núcleo nunca reimplementado aqui, só empacotado:
monta o estado inicial (modelo nulo), roda a busca, e devolve um resumo
pronto pra usar (variáveis, KS dev/teste, AUC, coeficientes, tabela de
decis) em vez do objeto `SelectionState` cru.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from pedro_wise.estimators import LogisticGLM
from pedro_wise.level3 import run_pedro_wise_completo
from pedro_wise.metrics import KSGaussianMetric
from pedro_wise.pipeline import run_pedro_wise
from pedro_wise.types import Level1Config, Level2Config, Level3Config, SelectionState
from sklearn.metrics import roc_auc_score


def _tabela_decis(y: pd.Series, prob: np.ndarray, n_faixas: int = 10) -> list[dict[str, Any]]:
    """Tabela de decis (gains/KS table) -- ordena por score decrescente
    (maior risco primeiro), divide em `n_faixas` grupos de tamanho ~igual,
    e acumula % de eventos/não-eventos capturados até cada faixa -- a maior
    diferença entre as duas curvas acumuladas é o próprio KS."""
    n = len(y)
    if n == 0:
        return []
    ordem = np.argsort(-prob)
    y_ordenado = y.to_numpy()[ordem]
    total_eventos = int(y_ordenado.sum())
    total_nao_eventos = n - total_eventos

    tamanho_faixa = max(1, n // n_faixas)
    linhas: list[dict[str, Any]] = []
    eventos_acumulados = 0
    nao_eventos_acumulados = 0
    for i in range(n_faixas):
        inicio = i * tamanho_faixa
        if inicio >= n:
            break
        fim = n if i == n_faixas - 1 else min(n, inicio + tamanho_faixa)
        fatia = y_ordenado[inicio:fim]
        n_fatia = len(fatia)
        eventos = int(fatia.sum())
        eventos_acumulados += eventos
        nao_eventos_acumulados += n_fatia - eventos
        pct_eventos_acum = eventos_acumulados / total_eventos if total_eventos else 0.0
        pct_nao_eventos_acum = nao_eventos_acumulados / total_nao_eventos if total_nao_eventos else 0.0
        linhas.append(
            {
                "faixa": i + 1,
                "n": n_fatia,
                "taxa_evento": eventos / n_fatia if n_fatia else 0.0,
                "pct_eventos_capturados": pct_eventos_acum,
                "pct_nao_eventos_capturados": pct_nao_eventos_acum,
                "ks_acumulado": abs(pct_eventos_acum - pct_nao_eventos_acum),
            }
        )
    return linhas


@dataclass(frozen=True)
class ResultadoTreinamento:
    variaveis: list[str]
    ks_dev: float
    ks_teste: float
    auc_teste: float
    taxa_evento_dev: float
    taxa_evento_teste: float
    coeficientes: dict[str, float]
    estatisticas: dict[str, dict[str, float]]
    tabela_decis: list[dict[str, Any]]


def treinar(
    df_dev: pd.DataFrame,
    df_teste: pd.DataFrame,
    criterio: str = "teste",
    shadow_probing: bool = False,
    forward_simples: bool = True,
    transformacao_simples_nivel1: bool = True,
    backward_simples_nivel1: bool = True,
    min_vars_para_backward: int = 5,
    forward_duplo: bool = True,
    forward_triplo: bool = True,
    transformacao_simples_nivel2: bool = True,
    backward_simples_nivel2: bool = True,
    n_best_duplo: int = 5,
    n_best_triplo_1: int = 3,
    n_best_triplo_2: int = 3,
    nivel3_ativado: bool = False,
    n_best_backward: int = 2,
    profundidade_maxima_nivel3: int = 2,
    p_valor_maximo: float | None = None,
) -> ResultadoTreinamento:
    """Roda o Pedro_Wise (níveis 1-2.5, ou 1-3 se `nivel3_ativado`) sobre
    `df_dev`/`df_teste` já prontos (todas as colunas exceto `y` são
    candidatas). `criterio` ("teste"/"dev"/"min") é o objetivo que o
    forward/backward otimiza em TODA a busca -- não um detalhe cosmético,
    é o que decide se uma variável entra ou sai a cada passo."""
    estimator = LogisticGLM()
    metric = KSGaussianMetric(criterio=criterio)  # type: ignore[arg-type]
    modelo_nulo = estimator.fit(df_dev[[]], df_dev["y"])
    score_nulo = metric(modelo_nulo, df_dev[[]], df_dev["y"], df_teste[[]], df_teste["y"])
    estado_inicial = SelectionState(variables=(), model=modelo_nulo, score=score_nulo)

    config1 = Level1Config(
        forward_simples=forward_simples,
        transformacao_simples=transformacao_simples_nivel1,
        backward_simples=backward_simples_nivel1,
        min_vars_para_backward=min_vars_para_backward,
        p_valor_maximo=p_valor_maximo,
    )
    config2 = Level2Config(
        forward_duplo=forward_duplo,
        forward_triplo=forward_triplo,
        transformacao_simples=transformacao_simples_nivel2,
        backward_simples=backward_simples_nivel2,
        n_best_duplo=n_best_duplo,
        n_best_triplo_1=n_best_triplo_1,
        n_best_triplo_2=n_best_triplo_2,
        p_valor_maximo=p_valor_maximo,
    )
    if nivel3_ativado:
        config3 = Level3Config(
            ativado=True, n_best_backward=n_best_backward, profundidade_maxima=profundidade_maxima_nivel3
        )
        estado_final, _ = run_pedro_wise_completo(
            estimator, metric, df_dev, df_teste, estado_inicial, config1, config2, config3
        )
    else:
        estado_final, _ = run_pedro_wise(
            estimator, metric, df_dev, df_teste, estado_inicial, config1, config2
        )

    variaveis = list(estado_final.variables)
    taxa_evento_dev = float(df_dev["y"].mean())
    taxa_evento_teste = float(df_teste["y"].mean())

    if not variaveis:
        return ResultadoTreinamento(
            variaveis=[],
            ks_dev=0.0,
            ks_teste=0.0,
            auc_teste=0.5,
            taxa_evento_dev=taxa_evento_dev,
            taxa_evento_teste=taxa_evento_teste,
            coeficientes={},
            estatisticas={},
            tabela_decis=[],
        )

    metric_teste = KSGaussianMetric(criterio="teste")
    metric_dev = KSGaussianMetric(criterio="dev")
    X_dev, X_teste = df_dev[variaveis], df_teste[variaveis]
    ks_teste = metric_teste(estado_final.model, X_dev, df_dev["y"], X_teste, df_teste["y"])
    ks_dev = metric_dev(estado_final.model, X_dev, df_dev["y"], X_teste, df_teste["y"])
    prob_teste = estado_final.model.predict_proba(X_teste)
    auc_teste = float(roc_auc_score(df_teste["y"], prob_teste))
    # LogisticGLM (único estimador hoje) tem estatisticas(); FittedModel
    # (Protocol) só garante variables/predict_proba, genérico de propósito.
    estatisticas = estado_final.model.estatisticas()  # type: ignore[attr-defined]
    coeficientes = estado_final.model.coeficientes()  # type: ignore[attr-defined]

    return ResultadoTreinamento(
        variaveis=variaveis,
        ks_dev=ks_dev,
        ks_teste=ks_teste,
        auc_teste=auc_teste,
        taxa_evento_dev=taxa_evento_dev,
        taxa_evento_teste=taxa_evento_teste,
        coeficientes=coeficientes,
        estatisticas=estatisticas,
        tabela_decis=_tabela_decis(df_teste["y"], prob_teste),
    )
