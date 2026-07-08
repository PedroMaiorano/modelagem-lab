"""Box-Cox e Yeo-Johnson — transformações de potência para corrigir
assimetria antes de um modelo linear (ver `docs/literatura/transformacao.md`,
Atkinson et al. 2021).

Mesmo padrão fit/transform (anti-leakage) do `woe.py`: o parâmetro `lambda`
é estimado uma vez no dev (`ajustar_*`) e reaplicado no teste (`aplicar_*`),
nunca reestimado lá.

**Box-Cox exige dados estritamente positivos** (é uma limitação da
transformação, não do código) — para variáveis com zero/negativos, use
Yeo-Johnson (extensão que aceita qualquer valor real).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import pandas as pd
from scipy import stats


@dataclass(frozen=True)
class TransformacaoPotencia:
    lambda_: float
    metodo: Literal["box-cox", "yeo-johnson"]


def ajustar_box_cox(x: pd.Series) -> TransformacaoPotencia:
    """Estima o `lambda` ótimo (máxima verossimilhança) no `x` de dev.
    Levanta `ValueError` claro se houver valor <= 0 (exigência da própria
    transformação, não uma limitação arbitrária de implementação).
    """
    if (x <= 0).any():
        raise ValueError(
            "Box-Cox exige valores estritamente positivos — use ajustar_yeo_johnson "
            "para variáveis com zero ou negativos"
        )
    _, lambda_ = stats.boxcox(x.to_numpy())
    return TransformacaoPotencia(lambda_=float(lambda_), metodo="box-cox")


def ajustar_yeo_johnson(x: pd.Series) -> TransformacaoPotencia:
    """Estima o `lambda` ótimo no `x` de dev — aceita qualquer valor real
    (zero e negativos incluídos), ao contrário do Box-Cox.
    """
    _, lambda_ = stats.yeojohnson(x.to_numpy())
    return TransformacaoPotencia(lambda_=float(lambda_), metodo="yeo-johnson")


def aplicar_potencia(x: pd.Series, transformacao: TransformacaoPotencia) -> pd.Series:
    """Aplica o `lambda` já ajustado (nunca reestima) — mesmo `lambda` do dev
    usado no teste, por construção.
    """
    if transformacao.metodo == "box-cox":
        if (x <= 0).any():
            raise ValueError("Box-Cox ajustado no dev, mas x aqui tem valor <= 0 — dev/teste inconsistentes")
        valores = stats.boxcox(x.to_numpy(), lmbda=transformacao.lambda_)
    else:
        valores = stats.yeojohnson(x.to_numpy(), lmbda=transformacao.lambda_)
    return pd.Series(valores, index=x.index, name=f"{x.name}_pot" if x.name else "pot")
