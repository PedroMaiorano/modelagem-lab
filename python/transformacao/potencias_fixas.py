"""Família de transformações de potência fixas — log, raiz quadrada,
quadrática, cúbica, e suas inversas. Diferente de `potencia.py`
(Box-Cox/Yeo-Johnson, que ajusta um `lambda` ótimo no dev), aqui cada
transformação é uma função fixa de `x`, sem parâmetro ajustado — não há
risco de vazamento dev/teste porque não há "fit" (aplicar em dev ou teste
dá exatamente a mesma fórmula).

Motivação: o Pedro_Wise (`pedro_wise.selection.transformacao_simples`) já
sabe testar trocar uma variável no modelo por outra versão da MESMA base
(`renda_woe` -> `renda_log`, por exemplo — ver `pedro_wise.base.extrair_base`).
Ele não GERA essas versões sozinho, só escolhe entre as que já existem como
coluna. Esta função é o que preenche esse pool de candidatas pro Pedro_Wise
escolher, além do WOE.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def gerar_transformacoes_fixas(x: pd.Series, nome_base: str) -> dict[str, pd.Series]:
    """Gera as transformações de `x` cujo domínio é compatível (nunca
    levanta erro — só omite a transformação que não se aplica):
    - `log`, `raiz`: exigem x > 0 em todos os valores.
    - `quad`, `cubo`: sempre definidas.
    - `inv`, `invquad`, `invcubo`: exigem x != 0 em todos os valores.

    Nomeadas `{nome_base}_{sufixo}` — o mesmo prefixo usado pela versão WOE
    (`{nome_base}_woe`), pra que `extrair_base` as reconheça como versões
    alternativas da mesma variável.
    """
    resultado: dict[str, pd.Series] = {}

    if (x > 0).all():
        resultado[f"{nome_base}_log"] = np.log(x)
        resultado[f"{nome_base}_raiz"] = np.sqrt(x)

    resultado[f"{nome_base}_quad"] = x**2
    resultado[f"{nome_base}_cubo"] = x**3

    if (x != 0).all():
        resultado[f"{nome_base}_inv"] = 1 / x
        resultado[f"{nome_base}_invquad"] = 1 / (x**2)
        resultado[f"{nome_base}_invcubo"] = 1 / (x**3)

    for nome, serie in resultado.items():
        serie.name = nome
    return resultado
