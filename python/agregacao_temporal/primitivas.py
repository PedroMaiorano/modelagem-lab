"""Primitivas de agregação temporal — constrói features de "comportamento"
a partir de um painel (chave + tempo + variável bruta observada mês a mês),
uma linha por (chave, tempo) na saída, prontas pra entrar no funil que já
existe (categorização → pré-seleção → Pedro_Wise).

Motivação: o ganho observado com o atraso (`tendência_3m` × `máximo_3m` em
faixas) não foi um golpe de sorte pra essa variável — é um padrão de
"behavioral scoring" que se replica pra qualquer variável de painel mensal.
Isto aqui generaliza o catálogo (máximo, média, mínimo, desvio-padrão,
tendência sobre janela móvel), inspirado no catálogo de primitivas de
agregação do Deep Feature Synthesis (Kanter & Veeramachaneni, 2015) — sem
adotar a biblioteca inteira, só o vocabulário de primitivas relevante pro
domínio de crédito.

Sem look-ahead: cada linha de saída usa só observações até e incluindo o
próprio período — nunca dados futuros da mesma chave. É o que torna essas
features seguras de usar num modelo de scoring (senão vazaria informação do
futuro pro ponto de observação).
"""

from __future__ import annotations

import re

import numpy as np
import pandas as pd


def _validar_painel(painel: pd.DataFrame, chave: str, tempo: str, valor: str) -> pd.DataFrame:
    faltando = {chave, tempo, valor} - set(painel.columns)
    if faltando:
        raise ValueError(f"Colunas ausentes no painel: {sorted(faltando)}")
    return painel.sort_values([chave, tempo]).reset_index(drop=True)


def _slope(y: np.ndarray) -> float:
    """Coeficiente angular de `y` contra um índice de tempo 0..n-1 — mede
    tendência de piora (positivo) ou melhora (negativo) dentro da janela.
    Fórmula fechada (cov/var) em vez de `np.polyfit`: mais rápida quando
    aplicada milhares de vezes via `rolling().apply`.
    """
    n = len(y)
    if n < 2:
        return 0.0
    x = np.arange(n, dtype=float)
    x_centrado = x - x.mean()
    variancia_x = (x_centrado**2).sum()
    if variancia_x == 0:
        return 0.0
    y_centrado = y - y.mean()
    return float((x_centrado * y_centrado).sum() / variancia_x)


#: Primitivas disponíveis — cada uma vira uma coluna `{valor}_{primitiva}_{n}m`.
PRIMITIVAS_JANELA = ("maximo", "media", "minimo", "desvio_padrao", "tendencia")

_SUFIXO_AGREGADO = re.compile(r"_(?:" + "|".join(PRIMITIVAS_JANELA) + r")_\d+m$")


def extrair_base_agregado(nome_coluna: str) -> str:
    """Reverte a convenção `{base}_{primitiva}_{janela}m` de
    `construir_agregados_janela` pra recuperar a variável bruta de origem —
    ex.: `dias_atraso_tendencia_3m` -> `dias_atraso`. Usado por
    `interacao.extrair_candidatas` pra saber se uma regra está cruzando
    variáveis brutas diferentes ou combinando primitivas da mesma. Colunas
    que não seguem o padrão (não vieram desta função) voltam inalteradas.
    """
    return _SUFIXO_AGREGADO.sub("", nome_coluna)


def construir_agregados_janela(
    painel: pd.DataFrame,
    chave: str,
    tempo: str,
    valor: str,
    janelas: list[int],
    primitivas: tuple[str, ...] = PRIMITIVAS_JANELA,
) -> pd.DataFrame:
    """Para cada `janela` (em número de períodos) e cada primitiva, adiciona
    uma coluna `{valor}_{primitiva}_{janela}m` ao painel — uma linha por
    (chave, tempo), calculada só com o histórico da própria chave até aquele
    tempo (`min_periods=1`: períodos iniciais sem histórico completo usam o
    que existe, nunca ficam NaN por causa de janela incompleta).

    Retorna o painel ordenado por (chave, tempo) com as colunas novas
    anexadas — o painel original não é modificado.
    """
    df = _validar_painel(painel, chave, tempo, valor)
    grupos = df.groupby(chave, sort=False)[valor]

    for n in janelas:
        janela_movel = grupos.rolling(window=n, min_periods=1)
        if "maximo" in primitivas:
            df[f"{valor}_maximo_{n}m"] = janela_movel.max().reset_index(level=0, drop=True)
        if "media" in primitivas:
            df[f"{valor}_media_{n}m"] = janela_movel.mean().reset_index(level=0, drop=True)
        if "minimo" in primitivas:
            df[f"{valor}_minimo_{n}m"] = janela_movel.min().reset_index(level=0, drop=True)
        if "desvio_padrao" in primitivas:
            df[f"{valor}_desvio_padrao_{n}m"] = (
                janela_movel.std(ddof=0).reset_index(level=0, drop=True).fillna(0.0)
            )
        if "tendencia" in primitivas:
            df[f"{valor}_tendencia_{n}m"] = (
                janela_movel.apply(_slope, raw=True).reset_index(level=0, drop=True)
            )

    return df
