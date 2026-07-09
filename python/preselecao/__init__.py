"""Módulo de pré-seleção de variáveis — reduz o volume de candidatas antes
do treinamento (Pedro_Wise). Ver `preselecao.filtros` para os 3 critérios
(variância, IV, correlação) e o raciocínio por trás de cada um.
"""

from preselecao.filtros import filtrar_correlacao, filtrar_iv, filtrar_variancia, pre_selecionar

__all__ = ["filtrar_correlacao", "filtrar_iv", "filtrar_variancia", "pre_selecionar"]
