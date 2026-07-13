"""Categorização + transformação — binning monotônico (`categorizacao`) +
WOE (`transformacao.woe`), com Information Value por variável. Roda depois
de Construção/Esfera 2, sobre qualquer coluna que sobrar nas tabelas
(numérica contínua, categórica/texto, ou binária 0/1 -- ex.: uma regra da
esfera 2).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from categorizacao import aplicar_bins, bins_monotonicos
from transformacao import ajustar_woe, aplicar_woe, avaliar_iv, classificar_iv, gerar_transformacoes_fixas

__all__ = ["ResultadoCategorizacao", "categorizar_e_transformar", "classificar_iv"]


@dataclass(frozen=True)
class ResultadoCategorizacao:
    woe_dev: pd.DataFrame
    woe_teste: pd.DataFrame
    iv_dev_por_variavel: dict[str, float]
    iv_teste_por_variavel: dict[str, float]
    """IV calculado no teste usando os WOEs já ajustados em dev (nunca
    reajustados) -- ver `transformacao.woe.avaliar_iv`. Comparar com
    `iv_dev_por_variavel`: uma variável com IV alto em dev e muito menor em
    teste é sinal de bin overfitado em dev, não de poder preditivo real.
    Diagnóstico apenas -- `preselecao.pre_selecionar` filtra só por
    `iv_dev_por_variavel`."""


def categorizar_e_transformar(
    df_dev: pd.DataFrame,
    df_teste: pd.DataFrame,
    gerar_transformacoes_potencia: bool = True,
    gerar_bin_ordinal: bool = True,
    ao_processar_coluna: Callable[[str, float], None] | None = None,
) -> ResultadoCategorizacao:
    """Pra cada coluna (exceto `y`): decide numérica contínua (binning
    monotônico antes do WOE) vs. categórica/binária (cada valor já é o
    "bin", sem discretizar) e ajusta WOE (só no dev, reaplicado no teste --
    nunca reajustado lá, seria vazamento). Opcionalmente também gera
    log/raiz/quad/cubo/inversas e o índice do bin (faixa) como candidatas
    extras -- o Pedro_Wise (nível 1, transformação simples) já sabe testar
    trocar a versão WOE por uma dessas via `pedro_wise.base.extrair_base`,
    desde que compartilhem o mesmo prefixo de base, que é o que
    garantimos aqui.

    `ao_processar_coluna(coluna, iv)`, se passado, é chamado depois de cada
    coluna processada com sucesso -- gancho pra quem quer progresso em
    tempo real (ex.: `app/backend/logica.py` publica isso numa fila SSE)
    sem essa biblioteca precisar saber o que é uma fila ou um WebSocket.
    `iv` aqui é sempre o IV de dev (o mesmo que vai pra
    `iv_dev_por_variavel`) -- ver `ResultadoCategorizacao.iv_teste_por_variavel`
    pro IV de teste, só disponível depois que a função termina.

    Devolve `ResultadoCategorizacao` -- `woe_dev`/`woe_teste` prontos pra
    `pre_selecionar`/`treinar`.
    """
    colunas_candidatas = [c for c in df_dev.columns if c != "y"]

    woe_dev: dict[str, Any] = {"y": df_dev["y"]}
    woe_teste: dict[str, Any] = {"y": df_teste["y"]}
    iv_por_variavel: dict[str, float] = {}
    iv_teste_por_variavel: dict[str, float] = {}

    for coluna in colunas_candidatas:
        try:
            # datasets sintéticos do lab já nomeiam a variável crua com sufixo
            # "_woe" por convenção -- usamos a base semântica (sem esse
            # sufixo) tanto pro nome WOE quanto pras transformações de
            # potência, senão elas ficariam com bases diferentes e o
            # Pedro_Wise nunca as veria como alternativas.
            base_semantica = coluna[:-4] if coluna.endswith("_woe") else coluna
            # binário (ex.: flag 0/1 de uma regra da esfera 2) não tem o que
            # categorizar -- só 2 valores possíveis já É o bin. Tratado como
            # "não numérica" pra esse propósito: `bins_monotonicos` numa
            # coluna com só 2 valores gera só 2 edges, insuficiente pra
            # discretizar (o filtro abaixo evitaria a coluna sendo
            # descartada silenciosamente).
            eh_numerica = (
                pd.api.types.is_numeric_dtype(df_dev[coluna]) and df_dev[coluna].nunique(dropna=True) > 2
            )

            if eh_numerica:
                resultado_bin = bins_monotonicos(df_dev[coluna], df_dev["y"], n_bins_inicial=15)
                if len(resultado_bin.edges) < 3:
                    continue
                bin_dev = aplicar_bins(df_dev[coluna], resultado_bin.edges)
                bin_teste = aplicar_bins(df_teste[coluna], resultado_bin.edges)
            else:
                # Categórica (texto) OU numérica binária: sem binning --
                # cada categoria/valor já é o "bin".
                bin_dev = df_dev[coluna]
                bin_teste = df_teste[coluna]

            tabela = ajustar_woe(bin_dev, df_dev["y"])
            nome_woe = f"{base_semantica}_woe"
            woe_dev[nome_woe] = aplicar_woe(bin_dev, tabela)
            woe_teste[nome_woe] = aplicar_woe(bin_teste, tabela, nome_coluna=coluna)
            iv_por_variavel[base_semantica] = tabela.iv_total
            iv_teste_por_variavel[base_semantica] = avaliar_iv(bin_teste, df_teste["y"], tabela)
            if ao_processar_coluna is not None:
                ao_processar_coluna(coluna, tabela.iv_total)

            if gerar_bin_ordinal and eh_numerica:
                nome_bin = f"{base_semantica}_bin"
                woe_dev[nome_bin] = bin_dev.astype(float)
                woe_teste[nome_bin] = bin_teste.astype(float)

            if gerar_transformacoes_potencia and eh_numerica:
                extras_dev = gerar_transformacoes_fixas(df_dev[coluna], base_semantica)
                extras_teste = gerar_transformacoes_fixas(df_teste[coluna], base_semantica)
                # só mantém transformações válidas (domínio ok) em dev E
                # teste -- senão a coluna existiria só de um lado.
                for nome_extra in set(extras_dev) & set(extras_teste):
                    serie_dev, serie_teste = extras_dev[nome_extra], extras_teste[nome_extra]
                    if not (np.isfinite(serie_dev).all() and np.isfinite(serie_teste).all()):
                        continue
                    woe_dev[nome_extra] = serie_dev
                    woe_teste[nome_extra] = serie_teste
        except (ValueError, IndexError, TypeError):
            # coluna degenerada (constante, poucos valores distintos etc.)
            # -- não impede o cálculo das outras.
            continue

    return ResultadoCategorizacao(
        woe_dev=pd.DataFrame(woe_dev),
        woe_teste=pd.DataFrame(woe_teste),
        iv_dev_por_variavel=iv_por_variavel,
        iv_teste_por_variavel=iv_teste_por_variavel,
    )
