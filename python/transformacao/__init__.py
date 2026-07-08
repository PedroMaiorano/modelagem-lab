"""Módulo de transformação de variáveis — um dos 4 módulos de modelagem do
lab (ver docs/planos/expansao-modulos-2026-07-08.md).

`woe`: Weight of Evidence + Information Value, a transformação canônica de
scorecards — fecha a lacuna da convenção `_woe` já usada em todo o lab.
"""

from transformacao.woe import TabelaWOE, ajustar_woe, aplicar_woe, classificar_iv

__all__ = ["TabelaWOE", "aplicar_woe", "ajustar_woe", "classificar_iv"]
