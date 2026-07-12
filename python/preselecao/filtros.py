"""Pré-seleção de variáveis — reduz o volume de candidatas antes do
treinamento (Pedro_Wise). Motivação: depois que Construção (razões
customizadas, sem limite) e as transformações de potência passaram a gerar
dezenas/centenas de colunas extras por variável-base, o volume de candidatas
pode explodir — mais lento pro Pedro_Wise e maior risco de selecionar ruído
por acaso (multiple testing). Três filtros, aplicados em sequência (do mais
barato ao mais informativo):

1. `filtrar_variancia`: descarta colunas quase constantes.
2. `filtrar_iv`: descarta TODAS as versões de uma variável-base com IV baixo
   (o IV mede o poder preditivo da variável em si, não muda entre
   WOE/bin/log/quad/etc. da mesma base).
3. `filtrar_correlacao`: entre pares muito correlacionados, mantém só o de
   maior IV.

Cada filtro é independente e pode ser pulado (limiar `None`).
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from pedro_wise.base import extrair_base


def filtrar_variancia(df: pd.DataFrame, colunas: list[str], limiar: float = 1e-6) -> list[str]:
    """Mantém colunas com variância > limiar — descarta quase-constantes,
    comuns entre transformações de potência quando a variável original tem
    pouca variação (ex.: `1/x` quando `x` é quase constante).
    """
    return [c for c in colunas if df[c].var(ddof=0) > limiar]


def filtrar_iv(colunas: list[str], iv_por_base: dict[str, float], limiar: float = 0.02) -> list[str]:
    """Mantém colunas cuja variável-base (`pedro_wise.base.extrair_base`) tem
    IV >= limiar. Bases sem entrada em `iv_por_base` são tratadas como
    IV=0 (descartadas) — evita manter candidatas "órfãs" por engano.
    """
    return [c for c in colunas if iv_por_base.get(extrair_base(c), 0.0) >= limiar]


def filtrar_correlacao(
    df: pd.DataFrame, colunas: list[str], iv_por_base: dict[str, float], limiar: float = 0.9
) -> tuple[list[str], list[tuple[str, str, float]]]:
    """Entre pares de colunas com correlação de Pearson |r| >= limiar, mantém
    só a de maior IV (empate: ordem alfabética, determinístico). Retorna
    `(colunas mantidas, pares descartados com a correlação)`.

    **Pares da MESMA variável-base são ignorados aqui de propósito**
    (ex.: `renda_woe` vs. `renda_bin` vs. `renda_log`) — são sempre
    correlacionadas entre si por construção (mesma variável, encoding
    diferente) e IV idêntico (calculado por base, não por derivada), então
    filtrar por correlação aqui colapsaria a família inteira num só
    sobrevivente ANTES do Pedro_Wise (`transformacao_simples`) sequer ter a
    chance de escolher a melhor versão pra esse modelo — justamente o
    mecanismo que essas derivadas foram geradas pra alimentar. Correlação só
    é sinal de redundância real entre bases DIFERENTES.
    """
    if len(colunas) < 2:
        return list(colunas), []

    matriz = df[colunas].corr().abs().to_numpy()
    indice = {c: i for i, c in enumerate(colunas)}
    descartadas: set[str] = set()
    pares_descartados: list[tuple[str, str, float]] = []
    ordenadas = sorted(colunas, key=lambda c: (-iv_por_base.get(extrair_base(c), 0.0), c))

    for i, a in enumerate(ordenadas):
        if a in descartadas:
            continue
        for b in ordenadas[i + 1 :]:
            if b in descartadas or extrair_base(a) == extrair_base(b):
                continue
            r = float(matriz[indice[a], indice[b]])
            if not np.isnan(r) and r >= limiar:
                descartadas.add(b)
                pares_descartados.append((a, b, r))

    mantidas = [c for c in colunas if c not in descartadas]
    return mantidas, pares_descartados


def pre_selecionar(
    df: pd.DataFrame,
    iv_por_base: dict[str, float],
    limiar_variancia: float | None = 1e-6,
    limiar_iv: float | None = 0.02,
    limiar_correlacao: float | None = 0.9,
) -> dict[str, Any]:
    """Aplica os 3 filtros em sequência (cada um opcional via `None`) e
    resume o funil — quantas candidatas sobraram em cada etapa, e QUAIS
    colunas saíram em cada uma (`colunas_descartadas_variancia`,
    `colunas_descartadas_iv`, `pares_correlacionados_descartados` — este
    último já vem com o par completo e o `r` de correlação, não só o nome
    da descartada), útil pra auditar exatamente por que uma variável sumiu.
    """
    colunas = [c for c in df.columns if c != "y"]
    n_inicial = len(colunas)

    colunas_antes_variancia = colunas
    if limiar_variancia is not None:
        colunas = filtrar_variancia(df, colunas, limiar_variancia)
    colunas_descartadas_variancia = [c for c in colunas_antes_variancia if c not in colunas]
    n_apos_variancia = len(colunas)

    colunas_antes_iv = colunas
    if limiar_iv is not None:
        colunas = filtrar_iv(colunas, iv_por_base, limiar_iv)
    colunas_descartadas_iv = [c for c in colunas_antes_iv if c not in colunas]
    n_apos_iv = len(colunas)

    pares_descartados: list[tuple[str, str, float]] = []
    if limiar_correlacao is not None:
        colunas, pares_descartados = filtrar_correlacao(df, colunas, iv_por_base, limiar_correlacao)

    return {
        "colunas_mantidas": colunas,
        "colunas_descartadas_variancia": colunas_descartadas_variancia,
        "colunas_descartadas_iv": colunas_descartadas_iv,
        "n_inicial": n_inicial,
        "n_apos_variancia": n_apos_variancia,
        "n_apos_iv": n_apos_iv,
        "n_final": len(colunas),
        "pares_correlacionados_descartados": pares_descartados,
    }
