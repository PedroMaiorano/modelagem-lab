"""Construção de variáveis (razões/diferenças) -- reexportado aqui só por
descoberta (`from pipeline_lab import construcao`); a implementação de
verdade mora em `construcao.razoes` porque também é usada fora do
pipeline_lab (ex.: Feature-lab). Ver `construcao.razoes` pro raciocínio
completo de escopo.
"""

from __future__ import annotations

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
