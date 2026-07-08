"""Semântica de "base" de variável e regra de não-coexistência de transformações.

Preserva a lógica do R original: cada variável tem um sufixo de transformação
(ex.: `renda_woe`, `renda_log`) e a "base" é o prefixo antes do último `_`.
A seleção nunca deixa duas versões da mesma base no modelo ao mesmo tempo.
"""

from __future__ import annotations

from collections.abc import Sequence


def extrair_base(variavel: str) -> str:
    """Prefixo antes do último '_' — identifica a variável-base por trás de uma
    versão transformada (`renda_woe` -> `renda`). Sem '_', a base é a própria variável.
    """
    if "_" not in variavel:
        return variavel
    return variavel.rsplit("_", 1)[0]


def bases_no_modelo(variaveis: Sequence[str]) -> set[str]:
    return {extrair_base(v) for v in variaveis}


def variaveis_disponiveis(
    variaveis_no_modelo: Sequence[str], todas_variaveis: Sequence[str], resposta: str = "y"
) -> list[str]:
    """Variáveis fora do modelo cuja base ainda não está representada.

    Equivalente a `filtrar_variaveis_fora_modelo` no R: uma base só pode entrar
    no modelo em uma versão por vez.
    """
    usadas = bases_no_modelo(variaveis_no_modelo)
    return [
        v
        for v in todas_variaveis
        if v != resposta and v not in variaveis_no_modelo and extrair_base(v) not in usadas
    ]


def versoes_alternativas(variavel_no_modelo: str, todas_variaveis: Sequence[str]) -> list[str]:
    """Outras versões (transformações) da MESMA base de `variavel_no_modelo`.

    Usado pela "troca simples": candidatas a substituir `variavel_no_modelo`
    mantendo a mesma base semântica.
    """
    base = extrair_base(variavel_no_modelo)
    return [v for v in todas_variaveis if v != variavel_no_modelo and extrair_base(v) == base]
