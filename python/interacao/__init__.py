"""Descoberta de interação — terceira esfera do feature-lab. Extrai regras
de interação (RuleFit-style) a partir de um ensemble de árvores rasas,
formalizando padrões como "tendência alta E severidade alta" que uma busca
de combinações lineares (Pedro_Wise) não descobre sozinha. Ver
`interacao.regras` para o raciocínio completo.
"""

from interacao.estabilidade import avaliar_estabilidade
from interacao.regras import Condicao, Regra, extrair_candidatas, regras_para_colunas

__all__ = [
    "Condicao",
    "Regra",
    "avaliar_estabilidade",
    "extrair_candidatas",
    "regras_para_colunas",
]
