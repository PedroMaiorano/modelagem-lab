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

from itertools import permutations

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


def construir_todas_as_razoes(
    df: pd.DataFrame,
    colunas: list[str] | None = None,
    incluir_diferenca: bool = True,
    epsilon: float = 1e-6,
) -> pd.DataFrame:
    """Gera razão (e, opcionalmente, diferença) para TODO par ordenado de
    colunas numéricas -- nome genérico automático (`"{a}_sobre_{b}"`,
    `"{a}_menos_{b}"`), sem precisar listar os pares na mão. Contraponto
    deliberado ao resto do módulo: `construir_razao`/`construir_razoes_em_lote`
    existem porque razão de negócio BEM ESCOLHIDA (ex.: `pago/fatura`) é mais
    interpretável que gerar tudo -- ver o raciocínio de escopo v1 mínimo no
    docstring do módulo. Esta função é o escape hatch pra quando você não
    tem esse conhecimento de domínio ainda e quer deixar a pré-seleção
    (`preselecao.pre_selecionar`) filtrar o que sobra depois.

    Ordem importa (`a/b` != `b/a`) -- por isso `permutations`, não
    `combinations`: gera as duas direções. Um dataset com `n` colunas
    numéricas produz `n*(n-1)` razões (e o dobro se `incluir_diferenca`,
    embora `a-b` e `b-a` sejam redundantes por sinal -- mantidas mesmo assim
    por simetria de nome com a razão, a pré-seleção descarta a redundante
    via `filtrar_correlacao`). Cresce quadraticamente: com dezenas de
    colunas numéricas já gera centenas/milhares de candidatas -- rode
    `preselecao.pre_selecionar` logo em seguida.
    """
    colunas_numericas = colunas or [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    construidas: dict[str, pd.Series] = {}
    for a, b in permutations(colunas_numericas, 2):
        nome_razao = f"{a}_sobre_{b}"
        construidas[nome_razao] = construir_razao(df[a], df[b], nome_razao, epsilon)
        if incluir_diferenca:
            nome_diferenca = f"{a}_menos_{b}"
            construidas[nome_diferenca] = construir_diferenca(df[a], df[b], nome_diferenca)
    return pd.DataFrame(construidas, index=df.index)
