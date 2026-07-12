"""Agregação temporal (ex-"esfera 1"). Reduz um dataset com várias linhas
por chave (painel: uma linha por chave-período) a uma linha por chave, com
máximo/média/mínimo/desvio-padrão/tendência sobre janelas móveis. Roda
ANTES de tudo o resto (Construção, Interação, Categorização) -- ver
`docs/planos/` pra motivação completa.
"""

from __future__ import annotations

import pandas as pd
from agregacao_temporal import construir_agregados_janela, normalizar_safra


def agregar(
    df: pd.DataFrame,
    chave: str,
    coluna_tempo: str,
    colunas_valor: list[str],
    janelas: list[int],
) -> tuple[pd.DataFrame, list[str]]:
    """Núcleo: roda `construir_agregados_janela` pra cada `colunas_valor` e
    reduz a uma linha por chave (último período). Não decide nada sobre a
    coluna resposta -- se `df` já tem `y` (ou qualquer coluna) como valor
    constante por chave, a linha que sobra depois do agrupamento já carrega
    o valor certo automaticamente (é só mais uma coluna que sobrevive ao
    `groupby().tail(1)`).
    """
    if not colunas_valor:
        raise ValueError("Selecione ao menos uma coluna de valor pra agregar")
    if chave not in df.columns or coluna_tempo not in df.columns:
        raise ValueError("Colunas de chave/tempo inválidas")

    # normalizar_safra espera formato de data/safra (unifica "202401"/
    # "2024-01"/"2024-01-15" misturados) -- forçar isso numa coluna de tempo
    # já numérica (comum quando não é um painel de verdade com safra)
    # rejeitava a coluna sem necessidade. Só normaliza quando não é numérica.
    if pd.api.types.is_numeric_dtype(df[coluna_tempo]):
        df = df.assign(_tempo_norm=df[coluna_tempo])
    else:
        df = df.assign(_tempo_norm=normalizar_safra(df[coluna_tempo]))
    df = df.sort_values([chave, "_tempo_norm"]).reset_index(drop=True)

    agregado = df
    colunas_geradas: list[str] = []
    for valor in colunas_valor:
        agregado = construir_agregados_janela(
            agregado, chave=chave, tempo="_tempo_norm", valor=valor, janelas=janelas
        )
        colunas_geradas += [c for c in agregado.columns if c.startswith(f"{valor}_")]

    por_chave = agregado.groupby(chave, sort=False).tail(1).reset_index(drop=True)
    # `_tempo_norm` é coluna de trabalho interna (ordenação pra construir os
    # agregados) -- nunca deveria sobrar na tabela final como candidata.
    por_chave = por_chave.drop(columns=["_tempo_norm"])
    return por_chave, colunas_geradas


def aplicar(
    df_dev: pd.DataFrame,
    df_teste: pd.DataFrame,
    chave: str,
    coluna_tempo: str,
    colunas_valor: list[str],
    janelas: list[int],
) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    """Agrega dev e teste SEPARADAMENTE (nunca junta e re-splita) -- cada
    linha já marcada dev/teste continua do mesmo lado, só colapsada por
    chave. Preserva qualquer split que você já tenha feito antes (ver
    `pipeline_lab.divisao`)."""
    dev_agregado, colunas_geradas = agregar(df_dev, chave, coluna_tempo, colunas_valor, janelas)
    teste_agregado, _ = agregar(df_teste, chave, coluna_tempo, colunas_valor, janelas)
    return dev_agregado, teste_agregado, colunas_geradas
