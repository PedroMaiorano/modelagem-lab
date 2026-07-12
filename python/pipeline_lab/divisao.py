"""Divisão dev/teste — dois jeitos, ambos devolvendo `(df_dev, df_teste)`.

Puro pandas, sem estado escondido: cada função recebe um DataFrame e devolve
dois novos, nunca muta o original.
"""

from __future__ import annotations

import pandas as pd


def _renomear_y(df: pd.DataFrame, coluna_y: str | None) -> pd.DataFrame:
    """Todo o resto de `pipeline_lab` (esfera1/esfera2/categorizar/treinamento)
    exige a variável resposta numa coluna chamada literalmente `"y"`. Passar
    `coluna_y` aqui já deixa a saída de `divisao` pronta pro resto do funil,
    sem precisar de um `.rename` manual em todo lugar que usa a biblioteca.
    """
    if coluna_y is None or coluna_y == "y":
        return df
    if coluna_y not in df.columns:
        raise ValueError(f"Coluna de resposta '{coluna_y}' não existe no dataframe")
    return df.rename(columns={coluna_y: "y"})


def dividir_por_amostra(
    df: pd.DataFrame,
    coluna_amostra: str,
    valores_dev: list[str],
    valores_teste: list[str],
    coluna_y: str | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split por uma coluna de amostra que já existe no dataframe (ex.:
    valores tipo "DES"/"OOT"/"treino"/"teste"/"OUT" -- o nome e os rótulos
    são livres, você diz quais valores contam como dev e quais contam como
    teste). Linhas com valor fora das duas listas são descartadas -- não
    aparecem nem em dev nem em teste (ex.: uma terceira amostra tipo
    "validação" que você não quer usar agora).

    `coluna_y`, se passado, renomeia sua coluna de resposta pra `"y"` (o
    nome que o resto do pipeline exige) -- evita precisar renomear na mão
    antes de cada etapa seguinte.
    """
    if coluna_amostra not in df.columns:
        raise ValueError(f"Coluna de amostra '{coluna_amostra}' não existe no dataframe")
    df = _renomear_y(df, coluna_y)
    df_dev = df[df[coluna_amostra].isin(valores_dev)].reset_index(drop=True)
    df_teste = df[df[coluna_amostra].isin(valores_teste)].reset_index(drop=True)
    if df_dev.empty or df_teste.empty:
        raise ValueError(
            f"Split vazio -- confira se os valores em valores_dev/valores_teste existem na coluna "
            f"'{coluna_amostra}' (valores encontrados: {sorted(df[coluna_amostra].unique())})"
        )
    return df_dev, df_teste


def dividir_aleatorio(
    df: pd.DataFrame, proporcao_teste: float = 0.5, semente: int = 42, coluna_y: str | None = None
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split aleatório simples -- embaralha e corta. `semente` garante que o
    mesmo dataframe sempre produz o mesmo split (reprodutibilidade).

    `coluna_y`, se passado, renomeia sua coluna de resposta pra `"y"` (ver
    `dividir_por_amostra`).
    """
    df = _renomear_y(df, coluna_y)
    embaralhado = df.sample(frac=1.0, random_state=semente).reset_index(drop=True)
    corte = int(len(embaralhado) * (1 - proporcao_teste))
    return embaralhado.iloc[:corte].reset_index(drop=True), embaralhado.iloc[corte:].reset_index(drop=True)
