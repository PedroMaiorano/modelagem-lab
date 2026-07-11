"""Descoberta de interação — terceira esfera do feature-lab. Extrai regras
de interação (RuleFit-style) a partir de um ensemble de árvores rasas,
formalizando padrões como "tendência alta E severidade alta" que uma busca
de combinações lineares (Pedro_Wise) não descobre sozinha. Ver
`interacao.regras` para o raciocínio completo.
"""

from interacao.regras import Condicao, Regra, extrair_candidatas, regras_para_colunas

__all__ = ["Condicao", "Regra", "extrair_candidatas", "regras_para_colunas"]
