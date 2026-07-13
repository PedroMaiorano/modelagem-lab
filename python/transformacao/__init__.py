"""Módulo de transformação de variáveis — um dos 4 módulos de modelagem do
lab (ver docs/planos/expansao-modulos-2026-07-08.md).

`woe`: Weight of Evidence + Information Value, a transformação canônica de
scorecards — fecha a lacuna da convenção `_woe` já usada em todo o lab.
`potencia`: Box-Cox / Yeo-Johnson, fit/transform anti-leakage.
"""

from transformacao.potencia import (
    TransformacaoPotencia,
    ajustar_box_cox,
    ajustar_yeo_johnson,
    aplicar_potencia,
)
from transformacao.potencias_fixas import gerar_transformacoes_fixas
from transformacao.woe import TabelaWOE, ajustar_woe, aplicar_woe, avaliar_iv, classificar_iv

__all__ = [
    "TabelaWOE",
    "TransformacaoPotencia",
    "ajustar_box_cox",
    "ajustar_woe",
    "ajustar_yeo_johnson",
    "aplicar_potencia",
    "aplicar_woe",
    "avaliar_iv",
    "classificar_iv",
    "gerar_transformacoes_fixas",
]
