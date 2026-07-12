"""Porta de entrada única pra consumir a biblioteca do lab (categorização,
transformação, construção, agregação temporal, interação, pré-seleção,
Pedro_Wise e a orquestração `pipeline_lab`) num namespace só.

Os 8 pacotes-núcleo continuam existindo e importáveis individualmente
(`from pedro_wise import ...`, `from categorizacao import ...`) -- nenhum
código interno do repo (`app/backend`, `scripts`, `tests`) precisa mudar
por causa deste pacote. `modelagem_lab` existe pra quem consome a
biblioteca de fora (notebook, outro projeto) e não quer decorar 8 nomes de
pacote genéricos nem arriscar colisão de namespace com pacotes de mesmo
nome de outros labs no mesmo ambiente Python:

    import modelagem_lab as ml

    resultado = (
        ml.Esteira.dividir_por_amostra(df, coluna_amostra="split", valores_dev=["train"],
                                        valores_teste=["test"], coluna_y="target")
        .categorizar_e_transformar()
        .treinar()
    )

    # pacotes-núcleo continuam acessíveis via atributo, pra quem quer o
    # estilo funcional em vez da Esteira:
    ml.categorizacao.bins_monotonicos(...)
    ml.pedro_wise.run_pedro_wise(...)
"""

from __future__ import annotations

import agregacao_temporal
import categorizacao
import construcao
import interacao
import pedro_wise
import pipeline_lab
import preselecao
import transformacao
from pipeline_lab import Esteira, EtapaForaDeOrdemError

__all__ = [
    "agregacao_temporal",
    "categorizacao",
    "construcao",
    "interacao",
    "pedro_wise",
    "pipeline_lab",
    "preselecao",
    "transformacao",
    "Esteira",
    "EtapaForaDeOrdemError",
]
