"""Construção de variáveis — escopo v1 deliberadamente mínimo (ver
docs/planos/expansao-modulos-2026-07-08.md e docs/literatura/construcao-variaveis.md
para a discussão de por quê): razões e diferenças entre pares de variáveis
relacionadas, não busca automática (GP/RL/DFS) — mais barato, interpretável, e
testável de imediato contra o Pedro_Wise já existente.

Exemplo motivador real (`credito_real`): `PAYAMT1/BILLAMT1` = "proporção paga
da fatura" — uma feature de negócio óbvia que não existe nas colunas
originais. Nenhuma das 23 colunas cruas captura isso diretamente.
"""

from __future__ import annotations

import pandas as pd


def construir_razao(
    numerador: pd.Series, denominador: pd.Series, nome: str, epsilon: float = 1e-6
) -> pd.Series:
    """`numerador / denominador`, com denominador exatamente zero substituído
    por `epsilon` (mantém o sinal em todo o resto — só evita divisão por
    zero literal). Comum em variáveis monetárias reais (ex.: fatura=0).
    """
    denominador_seguro = denominador.where(denominador != 0, epsilon)
    resultado = numerador / denominador_seguro
    resultado.name = nome
    return resultado


def construir_diferenca(a: pd.Series, b: pd.Series, nome: str) -> pd.Series:
    """`a - b` — útil para variáveis na mesma unidade (ex.: fatura mês atual
    menos fatura mês anterior = "variação de fatura")."""
    resultado = a - b
    resultado.name = nome
    return resultado


def construir_razoes_em_lote(
    df: pd.DataFrame, pares: list[tuple[str, str, str]], epsilon: float = 1e-6
) -> pd.DataFrame:
    """Aplica `construir_razao` para uma lista de `(numerador, denominador, nome)`.
    Retorna só as colunas construídas (não copia `df` inteiro) — junte com
    `pd.concat([df, resultado], axis=1)` se quiser tudo junto.
    """
    construidas = {
        nome: construir_razao(df[numerador], df[denominador], nome, epsilon)
        for numerador, denominador, nome in pares
    }
    return pd.DataFrame(construidas, index=df.index)
