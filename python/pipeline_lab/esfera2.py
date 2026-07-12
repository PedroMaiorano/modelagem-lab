"""Esfera 2 — descoberta de interação (RuleFit-style, ver
`python/interacao`). Roda DEPOIS da esfera 1/Construção e ANTES de
Categorização de propósito: as transformações de potência (log/raiz/quad/
cubo/inversa) só existem a partir da Categorização, então nesse ponto do
pipeline elas ainda não existem -- o GBM nunca vê `idade` e `idade_log` ao
mesmo tempo, não precisa de filtro extra pra evitar regra redundante entre
escalas da mesma variável.
"""

from __future__ import annotations

import pandas as pd
from interacao import avaliar_estabilidade, extrair_candidatas, regras_para_colunas
from transformacao.woe import ajustar_woe, aplicar_woe


def transformar_categoricas_woe(
    dev: pd.DataFrame,
    teste: pd.DataFrame,
    colunas_x: list[str],
    colunas_categoricas: list[str] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    """WOE-codifica colunas categóricas antes de entrar na esfera 2 --
    `GradientBoostingClassifier` (o motor de extração de regra) só aceita
    entrada numérica, e uma coluna de texto (ou um código numérico sem
    ordem real, tipo um campo de "tipo de defeito" com valores 3/6/7 sem
    relação de ordem) nunca deveria virar corte `<=`/`>` sobre o valor
    bruto -- WOE resolve isso mapeando cada categoria pro seu log-odds, uma
    escala onde threshold faz sentido de novo. Ajusta a tabela WOE só no
    dev (nunca no teste -- reajustar lá seria vazamento) e reaplica no
    teste. Colunas de texto (dtype não-numérico) em `colunas_x` são
    tratadas como categórica automaticamente, mesmo sem estar em
    `colunas_categoricas` -- não têm outro jeito de entrar num
    classificador numérico.
    """
    auto_categoricas = [
        c for c in colunas_x if c in dev.columns and not pd.api.types.is_numeric_dtype(dev[c])
    ]
    alvo = sorted(set(colunas_categoricas or []) | set(auto_categoricas))
    if not alvo:
        return dev, teste, colunas_x

    dev, teste = dev.copy(), teste.copy()
    mapa_nomes = {c: c for c in colunas_x}
    for coluna in alvo:
        if coluna not in dev.columns:
            continue
        tabela = ajustar_woe(dev[coluna], dev["y"])
        nome_woe = f"{coluna}_woe"
        dev[nome_woe] = aplicar_woe(dev[coluna], tabela)
        teste[nome_woe] = aplicar_woe(teste[coluna], tabela) if coluna in teste.columns else 0.0
        mapa_nomes[coluna] = nome_woe

    colunas_x_transformadas = [mapa_nomes.get(c, c) for c in colunas_x]
    return dev, teste, colunas_x_transformadas


def aplicar(
    df_dev: pd.DataFrame,
    df_teste: pd.DataFrame,
    colunas_categoricas: list[str] | None = None,
    profundidade_maxima: int = 2,
    n_arvores: int = 60,
    min_suporte: float = 0.02,
    max_suporte: float = 0.5,
    max_regras: int = 10,
    permitir_cruzamento_entre_bases: bool = True,
    proporcao_variaveis_por_split: float | None = None,
    iv_minimo: float = 0.02,
) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    """Descobre regras de interação estáveis e as materializa como coluna
    0/1 nas tabelas originais (dev/teste ORIGINAIS, não as WOE-codificadas
    internamente -- essas são só um passo interno pra gerar threshold de
    regra sensato, nunca substituem a coluna original que a Categorização
    vai processar do jeito de sempre). Só as regras estáveis (IV teste >=
    `iv_minimo` -- nunca o IV de dev, que já foi usado pra escolher a regra
    e está inflado por construção) viram coluna nova."""
    colunas_x = [c for c in df_dev.columns if c != "y"]
    if not colunas_x:
        return df_dev, df_teste, []

    dev_t, teste_t, colunas_x_transformadas = transformar_categoricas_woe(
        df_dev, df_teste, colunas_x, colunas_categoricas
    )

    regras = extrair_candidatas(
        dev_t[colunas_x_transformadas],
        dev_t["y"],
        profundidade_maxima=profundidade_maxima,
        n_arvores=n_arvores,
        min_suporte=min_suporte,
        max_suporte=max_suporte,
        max_regras=max_regras,
        permitir_cruzamento_entre_bases=permitir_cruzamento_entre_bases,
        proporcao_variaveis_por_split=proporcao_variaveis_por_split,
    )
    if not regras:
        return df_dev, df_teste, []

    tabela_estabilidade = avaliar_estabilidade(
        regras, dev_t[colunas_x_transformadas], dev_t["y"], teste_t[colunas_x_transformadas], teste_t["y"]
    )
    por_nome = {r.nome: r for r in regras}
    regras_estaveis = [
        por_nome[linha["regra"]]
        for _, linha in tabela_estabilidade.iterrows()
        if linha["iv_teste"] >= iv_minimo
    ]
    if not regras_estaveis:
        return df_dev, df_teste, []

    colunas_regra_dev = regras_para_colunas(regras_estaveis, dev_t)
    colunas_regra_teste = regras_para_colunas(regras_estaveis, teste_t)
    df_dev = pd.concat([df_dev, colunas_regra_dev], axis=1)
    df_teste = pd.concat([df_teste, colunas_regra_teste], axis=1)
    return df_dev, df_teste, list(colunas_regra_dev.columns)
