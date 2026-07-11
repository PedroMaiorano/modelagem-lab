"""Validação out-of-time das regras descobertas — separado de `regras.py`
por responsabilidade (extração/aplicação vs. avaliação de generalização).

Uma regra extraída de árvores treinadas em dev pode ser puro artefato de
overfitting local (a árvore sempre acha ALGUM corte que separa bem os dados
que ela viu — a pergunta é se esse corte é sinal real ou ruído memorizado).
`avaliar_estabilidade` recalcula suporte e IV da mesma regra (mesmos
limiares, nunca reajustados) em dev e teste — espelha o padrão
`ajustar_woe`/`aplicar_woe` do resto do lab: a regra é "ajustada" (descoberta)
uma vez em dev, e só reaplicada (nunca redescoberta) em teste.
"""

from __future__ import annotations

import pandas as pd
from transformacao.woe import ajustar_woe

from interacao.regras import Regra


def avaliar_estabilidade(
    regras: list[Regra],
    X_dev: pd.DataFrame,
    y_dev: pd.Series,
    X_teste: pd.DataFrame,
    y_teste: pd.Series,
) -> pd.DataFrame:
    """Uma linha por regra: suporte e IV em dev vs. teste, ordenado por
    `iv_teste` (o que importa pra decidir se a regra generaliza, não o IV de
    dev — que já era usado pra escolher a regra em `extrair_candidatas` e
    portanto está inflado por construção).

    `iv_teste` vira 0.0 (não erro) quando o teste não tem variação
    suficiente pra calcular IV (ex.: a regra nunca é satisfeita em teste, ou
    só captura um `y` de uma classe só ali) — sinaliza instabilidade em vez
    de quebrar a avaliação das outras regras.
    """
    linhas = []
    for regra in regras:
        mascara_dev = regra.aplicar(X_dev)
        mascara_teste = regra.aplicar(X_teste)
        suporte_dev = float(mascara_dev.mean())
        suporte_teste = float(mascara_teste.mean())

        try:
            iv_dev = ajustar_woe(mascara_dev.astype(str), y_dev).iv_total
        except ValueError:
            iv_dev = 0.0
        try:
            iv_teste = ajustar_woe(mascara_teste.astype(str), y_teste).iv_total
        except ValueError:
            iv_teste = 0.0

        linhas.append(
            {
                "regra": regra.nome,
                "suporte_dev": suporte_dev,
                "suporte_teste": suporte_teste,
                "iv_dev": iv_dev,
                "iv_teste": iv_teste,
            }
        )

    return pd.DataFrame(linhas).sort_values("iv_teste", ascending=False).reset_index(drop=True)
