"""Benchmark de paralelização: chamada isolada de `forward_simples` sob
backends/n_jobs distintos — mede o custo fixo de cada backend, não o ganho
no uso real (para isso, ver a seção "uso real" abaixo).

Uso: `python scripts/benchmark_paralelizacao.py`

Resultados medidos nesta máquina (8 vCPUs), chamada isolada (processo novo):

    Base pequena (1.5k linhas, 40 candidatas):
        sequencial            0.40s
        loky   n_jobs=4       3.9-4.0s  (pior — startup do pool de processos)
        threading n_jobs=2-8  0.48-0.57s (empata com sequencial)

    Base grande (30k linhas, 80 candidatas):
        sequencial             5.6s
        loky   n_jobs=4        1.8-1.9s  (pool reaproveitado entre repetições
                                           do script — custo de startup diluído)
        threading n_jobs=4     2.2-2.3s
        threading n_jobs=8     1.8-1.9s

Uso real — `run_level1` completo (30 candidatas, 15k linhas, convergindo
para 11 variáveis, várias dezenas de chamadas a `Parallel()` na mesma busca):

    sequencial (n_jobs=1)     64.7s
    threading  n_jobs=4       22.4s   (2.9x)
    loky       n_jobs=4       26.1s   (2.5x)

Conclusão: no uso real (o que importa), `threading` com `n_jobs` em torno de
3-4 é consistentemente o mais rápido — por isso é o backend fixo em
`pedro_wise.selection.PARALLEL_BACKEND`, nunca o `loky` default do joblib.
Este script mede só a chamada isolada (mais rápido de rodar); para o número
de uso real, ver o histórico de medição em
docs/referencias/benchmark-paralelizacao.md.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "python"))

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from pedro_wise.base import variaveis_disponiveis
from pedro_wise.estimators import LogisticGLM
from pedro_wise.metrics import KSGaussianMetric
from pedro_wise.selection import _tentar_fit_score


def _dataset_sintetico(n: int, n_vars: int, n_informativas: int = 5, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    u = rng.normal(0, 1, n)
    cols = {}
    for i in range(n_vars):
        peso = 1.0 if i < n_informativas else 0.0
        cols[f"v{i}_woe"] = peso * u + rng.normal(0, 1.2, n)
    logit_p = 1.5 * u
    p = 1 / (1 + np.exp(-logit_p))
    y = rng.binomial(1, p)
    return pd.DataFrame({"y": y, **cols})


def _benchmark(df_dev: pd.DataFrame, df_teste: pd.DataFrame, backend: str | None, n_jobs: int) -> float:
    estimator = LogisticGLM()
    metric = KSGaussianMetric(criterio="teste")
    candidatas = variaveis_disponiveis((), list(df_dev.columns))

    def _avaliar(v: str) -> object:
        return _tentar_fit_score(estimator, metric, df_dev, df_teste, (v,))

    t0 = time.perf_counter()
    if backend is None:
        [_avaliar(v) for v in candidatas]
    else:
        Parallel(n_jobs=n_jobs, backend=backend)(delayed(_avaliar)(v) for v in candidatas)
    return time.perf_counter() - t0


def main() -> None:
    cenarios = [
        ("pequena (1.5k linhas, 40 vars)", 1500, 40),
        ("grande (30k linhas, 80 vars)", 30_000, 80),
    ]
    configuracoes = [(None, 1), ("loky", 4), ("threading", 2), ("threading", 4), ("threading", 8)]

    for nome, n, n_vars in cenarios:
        df = _dataset_sintetico(n, n_vars)
        metade = n // 2
        df_dev, df_teste = df.iloc[:metade].reset_index(drop=True), df.iloc[metade:].reset_index(drop=True)
        print(f"\n=== {nome} ===")
        for backend, n_jobs in configuracoes:
            dt = _benchmark(df_dev, df_teste, backend, n_jobs)
            print(f"backend={str(backend):<10} n_jobs={n_jobs:>2}  tempo={dt:.3f}s")


if __name__ == "__main__":
    main()
