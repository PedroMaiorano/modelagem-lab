"""Roda o port Python sobre o MESMO dataset e config do `validar_port_r.R`,
para comparar a seleção de variáveis e o KS resultantes.

Uso: `python scripts/validar_port_python.py` (rodar validar_port_r.R antes)

Nota sobre o critério de decisão: o R original tem um bug conhecido
(`calc_ks_score` retorna só KS-dev — `as.numeric(ks_value_1, ks_value_2)`
descarta o segundo argumento silenciosamente) que faz a busca decidir
SEMPRE por KS-dev, nunca KS-teste, apesar de calcular os dois. Para uma
comparação justa da MECÂNICA de seleção (não da correção de anti-leakage,
que é uma melhoria deliberada do port), usamos `criterio="dev"` aqui —
mesma regra de decisão que o R de fato usa. `KSGaussianMetric(criterio="teste")`
é o default recomendado para uso real (ver metrics.py), não usado nesta
validação específica.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "python"))

import pandas as pd
from pedro_wise.base import extrair_base
from pedro_wise.estimators import LogisticGLM
from pedro_wise.metrics import KSGaussianMetric
from pedro_wise.pipeline import run_pedro_wise
from pedro_wise.types import Level1Config, Level2Config, SelectionState

DIR_DADOS = Path(__file__).resolve().parent.parent / "data" / "validacao_r"


def main() -> None:
    df_dev = pd.read_csv(DIR_DADOS / "dev.csv")
    df_teste = pd.read_csv(DIR_DADOS / "teste.csv")

    estimator = LogisticGLM()
    metric_decisao = KSGaussianMetric(criterio="dev")  # espelha o bug do R (decide só por dev)

    modelo_nulo = estimator.fit(df_dev[[]], df_dev["y"])
    score_nulo = metric_decisao(modelo_nulo, df_dev[[]], df_dev["y"], df_teste[[]], df_teste["y"])
    estado_inicial = SelectionState(variables=(), model=modelo_nulo, score=score_nulo)

    # Mesmos parâmetros da chamada de exemplo no Pedro_Wise_3.0.1.R:
    # n_best_duplo=5, n_best_triplo_1=3, n_best_triplo_2=3, backward_complexo_nivel_3=FALSE.
    config1 = Level1Config(min_vars_para_backward=5)
    config2 = Level2Config(n_best_duplo=5, n_best_triplo_1=3, n_best_triplo_2=3, min_vars_para_backward=5)

    estado_final, trace = run_pedro_wise(
        estimator, metric_decisao, df_dev, df_teste, estado_inicial, config1, config2
    )

    metric_teste = KSGaussianMetric(criterio="teste")
    ks_teste = metric_teste(
        estado_final.model,
        df_dev[list(estado_final.variables)],
        df_dev["y"],
        df_teste[list(estado_final.variables)],
        df_teste["y"],
    )

    variaveis_ordenadas = sorted(estado_final.variables)
    bases = sorted({extrair_base(v) for v in estado_final.variables})

    print("\n==== RESULTADO VALIDACAO PYTHON ====")
    print("VARIAVEIS:", ",".join(variaveis_ordenadas))
    print("BASES:", ",".join(bases))
    print(f"KS_DEV: {estado_final.score}")
    print(f"KS_TESTE: {ks_teste}")
    print(f"N_EVENTOS_TRACE: {len(trace.eventos)}")

    caminho_saida = DIR_DADOS / "resultado_python.txt"
    caminho_saida.write_text(
        "\n".join(
            [
                f"variaveis={','.join(variaveis_ordenadas)}",
                f"ks_dev={estado_final.score}",
                f"ks_teste={ks_teste}",
            ]
        )
    )
    print(f"\nEscrito {caminho_saida}")


if __name__ == "__main__":
    main()
