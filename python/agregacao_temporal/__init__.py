"""Agregação temporal — primeira esfera do feature-lab (ver
docs/planos/ — sucessora do módulo de pré-seleção). Constrói features de
comportamento (máximo/média/mínimo/desvio-padrão/tendência sobre janela
móvel) a partir de um painel mensal por chave, replicando de forma
sistemática o padrão manual usado para o atraso (tendência_3m × máximo_3m).
"""

from agregacao_temporal.primitivas import (
    PRIMITIVAS_JANELA,
    construir_agregados_janela,
    extrair_base_agregado,
)
from agregacao_temporal.safra import normalizar_safra

__all__ = [
    "PRIMITIVAS_JANELA",
    "construir_agregados_janela",
    "extrair_base_agregado",
    "normalizar_safra",
]
