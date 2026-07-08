"""Gera um dataset onde `xa_woe`/`xb_woe` são proxies QUASE-DUPLICADAS (alta
colinearidade) de um único fator latente `u` — o cenário em que a literatura
(Faletto & Bien 2022, ver docs/literatura/stability-selection.md) diz que
stability selection com lasso puro pode falhar: o lasso escolhe arbitrariamente
UMA das duas por reamostragem, a frequência de seleção se divide entre as duas,
e nenhuma atinge o limiar — resultado pior que um único fit de lasso.

Diferença estrutural do dataset anterior (`gerar_dataset_validacao.py`): lá
`xa_woe`/`xb_woe` tinham ruído individual alto (desvio 1.4) — proxies fracas,
correlação moderada. Aqui o ruído é baixo (desvio 0.3) — proxies quase
intercambiáveis, correlação alta (~0.9+), o teste de colinearidade real.

Uso: python scripts/gerar_dataset_colinearidade.py
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

SAIDA = Path(__file__).resolve().parent.parent / "data" / "experimento_colinearidade"


def main() -> None:
    rng = np.random.default_rng(2026)
    n = 3000

    u = rng.normal(0, 1, n)
    # ruído baixo -> alta correlação entre xa_woe e xb_woe (proxies quase-duplicadas)
    xa_woe = u + rng.normal(0, 0.3, n)
    xb_woe = u + rng.normal(0, 0.3, n)
    correlacao = np.corrcoef(xa_woe, xb_woe)[0, 1]

    x_ruido_woe = rng.normal(0, 1, n)
    x_ruido2_woe = rng.normal(0, 1, n)

    logit_p = 1.5 * u
    p = 1 / (1 + np.exp(-logit_p))
    y = rng.binomial(1, p)

    df = pd.DataFrame(
        {"y": y, "xa_woe": xa_woe, "xb_woe": xb_woe, "x_ruido_woe": x_ruido_woe, "x_ruido2_woe": x_ruido2_woe}
    )

    metade = n // 2
    df_dev = df.iloc[:metade].reset_index(drop=True)
    df_teste = df.iloc[metade:].reset_index(drop=True)

    SAIDA.mkdir(parents=True, exist_ok=True)
    df_dev.to_csv(SAIDA / "dev.csv", index=False)
    df_teste.to_csv(SAIDA / "teste.csv", index=False)
    print(f"corr(xa_woe, xb_woe) = {correlacao:.3f}")
    print(f"Escrito {SAIDA / 'dev.csv'} ({len(df_dev)} linhas)")
    print(f"Escrito {SAIDA / 'teste.csv'} ({len(df_teste)} linhas)")


if __name__ == "__main__":
    main()
