"""Pré-seleção de variáveis -- reexportado aqui só por descoberta
(`from pipeline_lab import preselecao`); a implementação de verdade mora em
`preselecao.filtros` (variância → IV → correlação, ver lá pro raciocínio
completo). Recebe `iv_por_variavel`, que é exatamente o terceiro retorno de
`categorizar.categorizar_e_transformar`.
"""

from __future__ import annotations

from preselecao.filtros import filtrar_correlacao, filtrar_iv, filtrar_variancia, pre_selecionar

__all__ = ["filtrar_correlacao", "filtrar_iv", "filtrar_variancia", "pre_selecionar"]
