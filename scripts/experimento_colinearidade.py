"""Experimento: colinearidade forte entre `xa_woe`/`xb_woe` (proxies
quase-duplicadas de um fator latente `u`, corr ~0.9).

Testa o achado do Faletto & Bien (2022, ver
docs/literatura/stability-selection.md): stability selection com lasso puro
pode falhar sob proxies correlacionados — o lasso escolhe arbitrariamente UMA
proxy por reamostragem, a frequência se divide entre as duas, e **nenhuma**
atinge o limiar. Compara contra LASSO de fit único (sempre inclui uma) e
contra o Pedro_Wise, com e sem `forward_duplo` (nível 2), para checar se
testar o par conjuntamente muda o resultado.

Usa `data/experimento_colinearidade/{dev,teste}.csv`
(gerar_dataset_colinearidade.py). Reaproveita `rodar_lasso`,
`rodar_stability_selection`, `avaliar_variaveis` de
`experimento_pedro_wise_vs_alternativas.py` (mesmo diretório).

Uso: python scripts/experimento_colinearidade.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "python"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd
from experimento_pedro_wise_vs_alternativas import avaliar_variaveis, rodar_lasso, rodar_stability_selection
from pedro_wise.base import extrair_base
from pedro_wise.estimators import LogisticGLM
from pedro_wise.metrics import KSGaussianMetric
from pedro_wise.selection import run_level1
from pedro_wise.types import Level1Config, SelectionState
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

_reconfigure = getattr(sys.stdout, "reconfigure", None)
if _reconfigure is not None and sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    _reconfigure(encoding="utf-8", errors="replace")

DIR_DADOS = Path(__file__).resolve().parent.parent / "data" / "experimento_colinearidade"


def _estado_nulo(estimator, metric, df_dev, df_teste):
    modelo_nulo = estimator.fit(df_dev[[]], df_dev["y"])
    score_nulo = metric(modelo_nulo, df_dev[[]], df_dev["y"], df_teste[[]], df_teste["y"])
    return SelectionState(variables=(), model=modelo_nulo, score=score_nulo)


def rodar_pedro_wise_nivel1_apenas(df_dev: pd.DataFrame, df_teste: pd.DataFrame) -> list[str]:
    """Só forward/troca/backward simples — variável por vez, sem `forward_duplo`.
    Equivalente em espírito a um único fit de LASSO: greedy, sem testar pares.
    """
    estimator = LogisticGLM()
    metric = KSGaussianMetric(criterio="teste")
    estado_inicial = _estado_nulo(estimator, metric, df_dev, df_teste)
    estado_final, _ = run_level1(estimator, metric, df_dev, df_teste, estado_inicial, Level1Config())
    return list(estado_final.variables)


def rodar_pedro_wise_com_duplo(df_dev: pd.DataFrame, df_teste: pd.DataFrame) -> list[str]:
    from pedro_wise.pipeline import run_pedro_wise
    from pedro_wise.types import Level2Config

    estimator = LogisticGLM()
    metric = KSGaussianMetric(criterio="teste")
    estado_inicial = _estado_nulo(estimator, metric, df_dev, df_teste)
    estado_final, _ = run_pedro_wise(
        estimator, metric, df_dev, df_teste, estado_inicial, Level1Config(), Level2Config()
    )
    return list(estado_final.variables)


def rodar_lasso_fit_unico(df_dev: pd.DataFrame, colunas: list[str], c_regularizacao: float) -> list[str]:
    """Um único fit de LASSO no `c_regularizacao` dado — a comparação que o
    Faletto & Bien de fato usa: stability selection no MESMO nível de
    regularização de um lasso comum, não o C ótimo por CV.
    """
    scaler = StandardScaler()
    X = scaler.fit_transform(df_dev[colunas])
    modelo = LogisticRegression(
        penalty="l1", solver="liblinear", C=c_regularizacao, random_state=0, max_iter=2000
    )
    modelo.fit(X, df_dev["y"])
    coefs = modelo.coef_[0]
    return [v for v, c in zip(colunas, coefs, strict=True) if abs(c) > 1e-6]


def main() -> None:
    df_dev = pd.read_csv(DIR_DADOS / "dev.csv")
    df_teste = pd.read_csv(DIR_DADOS / "teste.csv")
    colunas = [c for c in df_dev.columns if c != "y"]
    correlacao = df_dev["xa_woe"].corr(df_dev["xb_woe"])

    # C=0.005 achado por varredura manual para ESTE dataset (ver commit): em
    # C=0.02-0.01 xa/xb ficam em ~1.00 (o par inteiro é estável); em C=0.002 o
    # par inteiro é zerado (regularização forte demais até para o sinal real).
    # C=0.005 é a janela estreita onde o par colapsa junto para ~0.27-0.36 —
    # abaixo do limiar de 0.6 mesmo com sinal real forte. C ótimo por CV
    # (~0.5-1) nem chega perto dessa zona — por isso a comparação usa o MESMO
    # C forte tanto no lasso de fit único quanto na stability selection.
    c_forte = 0.005

    print(f"Dataset: {len(df_dev)} linhas dev, corr(xa_woe, xb_woe) = {correlacao:.3f}")
    print("Gabarito: xa/xb são a MESMA informação (proxies de u); x_ruido/x_ruido2 são ruído puro.\n")

    resultados: dict[str, list[str]] = {}

    print("Rodando Pedro_Wise (nível 1 apenas, sem forward_duplo)...")
    resultados["Pedro_Wise (nível 1 só)"] = rodar_pedro_wise_nivel1_apenas(df_dev, df_teste)

    print("Rodando Pedro_Wise (com forward_duplo)...")
    resultados["Pedro_Wise (com nível 2)"] = rodar_pedro_wise_com_duplo(df_dev, df_teste)

    print("Rodando LASSO (C ótimo por CV)...")
    resultados["LASSO (C ótimo por CV)"] = rodar_lasso(df_dev, colunas)

    print(f"Rodando LASSO (fit único, C={c_forte} — mesmo nível da stability selection)...")
    resultados[f"LASSO (fit único, C={c_forte})"] = rodar_lasso_fit_unico(df_dev, colunas, c_forte)

    print(f"Rodando stability selection (100 reamostragens, C={c_forte})...\n")
    vars_stability, frequencias = rodar_stability_selection(df_dev, colunas, c_regularizacao=c_forte)
    resultados["Stability Selection"] = vars_stability

    print("=" * 78)
    print(f"{'Método':<32} {'Bases selecionadas':<30} {'KS-teste':>8} {'AUC':>6}")
    print("=" * 78)
    for nome, variaveis in resultados.items():
        metricas = avaliar_variaveis(variaveis, df_dev, df_teste)
        bases = sorted({extrair_base(v) for v in variaveis})
        print(f"{nome:<32} {','.join(bases):<30} {metricas['ks_teste']:>8.4f} {metricas['auc_teste']:>6.3f}")

    print("\nFrequência de seleção por variável (stability selection):")
    print(frequencias.to_string())
    freq_xa = frequencias.get("xa_woe", 0.0)
    freq_xb = frequencias.get("xb_woe", 0.0)
    print(f"\nxa_woe: {freq_xa:.2f} | xb_woe: {freq_xb:.2f} | limiar padrão: 0.60")
    if freq_xa < 0.6 and freq_xb < 0.6:
        print(">> Falha reproduzida: NENHUMA das duas proxies atinge o limiar (Faletto & Bien 2022).")
    else:
        print(">> Falha NÃO reproduzida nesta rodada — pelo menos uma proxy atingiu o limiar.")


if __name__ == "__main__":
    main()
