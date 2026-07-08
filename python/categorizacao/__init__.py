"""Módulo de categorização (binning/discretização) — um dos 4 módulos de
modelagem do lab (ver docs/planos/expansao-modulos-2026-07-08.md).

Produz `edges` (quebras de bin) que alimentam `transformacao.woe` — o fluxo
típico é `bins_monotonicos(x, y)` -> `aplicar_bins(x, edges)` -> `calcular_woe(...)`.
"""

from categorizacao.binning import (
    ResultadoMonotonico,
    aplicar_bins,
    bins_arvore,
    bins_frequencia_igual,
    bins_largura_igual,
    bins_monotonicos,
)

__all__ = [
    "ResultadoMonotonico",
    "aplicar_bins",
    "bins_arvore",
    "bins_frequencia_igual",
    "bins_largura_igual",
    "bins_monotonicos",
]
