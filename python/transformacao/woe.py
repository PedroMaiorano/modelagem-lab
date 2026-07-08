"""WOE (Weight of Evidence) e Information Value (IV) — a transformação
canônica de scorecards (Siddiqi, *Credit Risk Scorecards*, ver
`docs/referencias/livros.md`). Fecha a lacuna mais óbvia do lab: `_woe` já é
a convenção de nomenclatura usada em todo dataset sintético e no
`credito_real`, mas nunca havia sido implementada — só o nome.

## Convenção de sinal (documentada porque a literatura não é unânime)

```
WOE_i = ln( %não-evento_i / %evento_i )
```

Bin com mais não-eventos (ex.: "bom pagador") que eventos, relativo à
distribuição total, tem WOE **positivo** — convenção de Siddiqi, a mais
comum em scorecards de crédito. Um coeficiente positivo na regressão
logística sobre `_woe` então significa "aumenta a chance de ser bom
pagador", legível diretamente por quem não é estatístico.

## Fluxo (anti-leakage por construção)

```
ajustar_woe(bin_idx_dev, y_dev)  -> TabelaWOE   # só olha dev
aplicar_woe(bin_idx_dev, tabela)  -> woe_dev     # aplica a tabela ajustada
aplicar_woe(bin_idx_teste, tabela) -> woe_teste  # MESMA tabela, nunca reajustada
```

Espelha o padrão fit/transform do scikit-learn — a tabela é ajustada uma
vez no dev e reaplicada no teste, nunca recalculada lá (repetir o cálculo no
teste seria vazamento: usar a variável-resposta de teste para construir o
preditor).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TabelaWOE:
    """Tabela ajustada: WOE e estatísticas por bin. `suavizacao` fica
    registrada para documentar como zeros foram evitados no cálculo.
    """

    woe_por_bin: pd.Series  # index = bin, valores = WOE
    # index = bin; colunas: count, count_evento, count_nao_evento, taxa_evento, woe, iv_parcial
    resumo: pd.DataFrame
    iv_total: float
    suavizacao: float


def ajustar_woe(bin_idx: pd.Series, y: pd.Series, suavizacao: float = 0.5) -> TabelaWOE:
    """Ajusta a tabela de WOE a partir de `bin_idx` (categorias/bins já
    definidos, ex.: saída de `categorizacao.aplicar_bins`) e `y` (0/1).

    `suavizacao` (Laplace-like): soma-se esse valor à contagem de evento e
    não-evento de cada bin antes de calcular proporções — evita `WOE = ±inf`
    quando um bin tem zero eventos ou zero não-eventos (comum em bins raros
    de dados reais; sem suavização, um único bin quebraria o WOE inteiro).
    """
    if not set(y.unique()) <= {0, 1}:
        raise ValueError("y precisa ser binário (0/1)")

    df = pd.DataFrame({"bin": bin_idx, "y": y}).dropna(subset=["bin"])
    # pandas-stubs tipa agg(**named) em SeriesGroupBy como Series, mas em runtime
    # com múltiplos kwargs nomeados o retorno é DataFrame (comportamento documentado do pandas).
    agrupado: pd.DataFrame = df.groupby("bin", observed=True)["y"].agg(
        count="count", count_evento="sum"
    )  # type: ignore[assignment]
    agrupado["count_nao_evento"] = agrupado["count"] - agrupado["count_evento"]
    agrupado["taxa_evento"] = agrupado["count_evento"] / agrupado["count"]

    total_evento = agrupado["count_evento"].sum()
    total_nao_evento = agrupado["count_nao_evento"].sum()
    if total_evento == 0 or total_nao_evento == 0:
        raise ValueError("y precisa ter ao menos um evento e um não-evento")

    prop_evento = (agrupado["count_evento"] + suavizacao) / (total_evento + suavizacao * len(agrupado))
    prop_nao_evento = (agrupado["count_nao_evento"] + suavizacao) / (
        total_nao_evento + suavizacao * len(agrupado)
    )

    agrupado["woe"] = np.log(prop_nao_evento / prop_evento)
    agrupado["iv_parcial"] = (prop_nao_evento - prop_evento) * agrupado["woe"]

    bins_com_zero = agrupado[(agrupado["count_evento"] == 0) | (agrupado["count_nao_evento"] == 0)]
    if len(bins_com_zero) > 0:
        logger.warning(
            "%d bin(s) com contagem zero de evento ou não-evento — WOE calculado só com suavização",
            len(bins_com_zero),
        )

    return TabelaWOE(
        woe_por_bin=agrupado["woe"],
        resumo=agrupado[["count", "count_evento", "count_nao_evento", "taxa_evento", "woe", "iv_parcial"]],
        iv_total=float(agrupado["iv_parcial"].sum()),
        suavizacao=suavizacao,
    )


def aplicar_woe(bin_idx: pd.Series, tabela: TabelaWOE) -> pd.Series:
    """Mapeia cada bin para seu WOE ajustado. Bins presentes aqui mas
    ausentes na tabela ajustada (categoria nova em teste/produção que não
    apareceu no dev) recebem WOE=0 (neutro) — não descartam a linha, mas
    também não inventam informação que a tabela de dev não tinha.
    """
    mapeado = bin_idx.map(tabela.woe_por_bin)
    n_ausentes = mapeado.isna().sum() - bin_idx.isna().sum()
    if n_ausentes > 0:
        logger.warning("%d valor(es) com bin ausente da tabela de WOE — atribuído WOE=0", n_ausentes)
    return mapeado.fillna(0.0)


def classificar_iv(iv_total: float) -> str:
    """Régua de interpretação de IV comum na prática de scorecards (Siddiqi):
    < 0.02 sem poder preditivo, 0.02-0.1 fraco, 0.1-0.3 médio, 0.3-0.5 forte,
    > 0.5 suspeito (provável vazamento/overfitting).
    """
    if iv_total < 0.02:
        return "sem poder preditivo"
    if iv_total < 0.1:
        return "fraco"
    if iv_total < 0.3:
        return "médio"
    if iv_total < 0.5:
        return "forte"
    return "suspeito (possível vazamento)"
