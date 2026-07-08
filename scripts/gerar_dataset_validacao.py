"""Gera o dataset sintético usado para validar o port Python contra o R original.

Uso: `python scripts/gerar_dataset_validacao.py`

Escreve `data/validacao_r/dev.csv` e `data/validacao_r/teste.csv` (gitignored,
ver `.gitignore` -> `data/`). Mesmo CSV é lido tanto por `validar_port_r.R`
quanto por `validar_port_python.py` — garante que os dois lados operam sobre
exatamente os mesmos dados.

Estrutura do dataset (pensada para exercitar todos os níveis 1/2/2.5):
- `xa_woe`, `xb_woe`: proxies ruidosas de um fator latente comum -> par
  sinérgico, só visível ao forward duplo (nível 2).
- `x1_woe` / `x1_log`: mesma base, x1_log mais ruidosa -> exercita troca simples.
- `x2_woe`, `x3_woe`: informativas mas mais fracas -> exercitam forward simples
  repetido e forward triplo.
- `x_ruido_woe` / `x_ruido_log`, `x_ruido2_woe`: puro ruído, mesma/base
  diferente -> nunca devem ser selecionadas.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

SAIDA = Path(__file__).resolve().parent.parent / "data" / "validacao_r"


def main() -> None:
    rng = np.random.default_rng(2026)
    n = 4000

    u = rng.normal(0, 1, n)
    xa_woe = u + rng.normal(0, 1.4, n)
    xb_woe = u + rng.normal(0, 1.4, n)

    x1_woe = rng.normal(0, 1, n)
    x1_log = x1_woe + rng.normal(0, 0.9, n)

    x2_woe = rng.normal(0, 1, n)
    x3_woe = rng.normal(0, 1, n)

    x_ruido_woe = rng.normal(0, 1, n)
    x_ruido_log = rng.normal(0, 1, n)
    x_ruido2_woe = rng.normal(0, 1, n)

    logit_p = 1.3 * u + 0.7 * x1_woe + 0.5 * x2_woe + 0.4 * x3_woe
    p = 1 / (1 + np.exp(-logit_p))
    y = rng.binomial(1, p)

    df = pd.DataFrame(
        {
            "y": y,
            "xa_woe": xa_woe,
            "xb_woe": xb_woe,
            "x1_woe": x1_woe,
            "x1_log": x1_log,
            "x2_woe": x2_woe,
            "x3_woe": x3_woe,
            "x_ruido_woe": x_ruido_woe,
            "x_ruido_log": x_ruido_log,
            "x_ruido2_woe": x_ruido2_woe,
        }
    )

    metade = n // 2
    df_dev = df.iloc[:metade].reset_index(drop=True)
    df_teste = df.iloc[metade:].reset_index(drop=True)

    SAIDA.mkdir(parents=True, exist_ok=True)
    df_dev.to_csv(SAIDA / "dev.csv", index=False)
    df_teste.to_csv(SAIDA / "teste.csv", index=False)
    print(f"Escrito {SAIDA / 'dev.csv'} ({len(df_dev)} linhas)")
    print(f"Escrito {SAIDA / 'teste.csv'} ({len(df_teste)} linhas)")


if __name__ == "__main__":
    main()
