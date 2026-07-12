"""Módulo de construção de variáveis — um dos 4 módulos de modelagem do lab
(ver docs/planos/expansao-modulos-2026-07-08.md). Escopo v1 deliberadamente
mínimo: razões/diferenças interpretáveis, não busca automática — ver
docs/literatura/construcao-variaveis.md para o raciocínio completo.
"""

from construcao.razoes import (
    construir_diferenca,
    construir_razao,
    construir_razoes_em_lote,
    construir_todas_as_razoes,
)

__all__ = [
    "construir_diferenca",
    "construir_razao",
    "construir_razoes_em_lote",
    "construir_todas_as_razoes",
]
