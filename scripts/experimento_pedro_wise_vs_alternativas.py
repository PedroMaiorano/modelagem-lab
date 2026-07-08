"""Experimento comparativo: Pedro_Wise (port) vs. LASSO vs. stability selection.

Motivação: `docs/referencias/sota-tracker-modelagem.md` §5 registra isso como
"experimento natural do lab" — comparar o wrapper stepwise portado contra as
alternativas embedded/robustas da literatura, no mesmo dataset.

Usa `data/validacao_r/{dev,teste}.csv` (gerado por gerar_dataset_validacao.py),
cujo processo gerador é CONHECIDO — permite avaliar cada método contra o
"gabarito" real, não só contra KS/AUC:
  - bases informativas: xa, xb (proxies de um fator latente u), x1, x2, x3
  - bases de ruído puro: x_ruido, x_ruido2
  - x1_log é outra versão (mesma base x1), não noise nem sinal independente

Uso: python scripts/experimento_pedro_wise_vs_alternativas.py
"""

from __future__ import annotations

import sys
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "python"))

import numpy as np
import pandas as pd
from pedro_wise.base import extrair_base
from pedro_wise.estimators import LogisticGLM
from pedro_wise.metrics import KSGaussianMetric
from pedro_wise.pipeline import run_pedro_wise
from pedro_wise.types import Level1Config, Level2Config, SelectionState
from sklearn.linear_model import LogisticRegression, LogisticRegressionCV
from sklearn.metrics import roc_auc_score
from sklearn.preprocessing import StandardScaler

# Nomes/relatório trazem acentuação fora do cp1252 do console Windows.
_reconfigure = getattr(sys.stdout, "reconfigure", None)
if _reconfigure is not None and sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    _reconfigure(encoding="utf-8", errors="replace")

DIR_DADOS = Path(__file__).resolve().parent.parent / "data" / "validacao_r"
BASES_INFORMATIVAS = {"xa", "xb", "x1", "x2", "x3"}
BASES_RUIDO = {"x_ruido", "x_ruido2"}

# sklearn 1.9+ emite FutureWarning/UserWarning ao usar penalty="l1" (API em
# transição para l1_ratio) e ConvergenceWarning em alguns folds do CV — nenhum
# afeta o resultado numérico aqui; silenciados para não afogar a tabela final.
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)


def avaliar_variaveis(
    variaveis: list[str], df_dev: pd.DataFrame, df_teste: pd.DataFrame
) -> dict[str, float]:
    """Reajusta uma logística simples (statsmodels) só com `variaveis` e mede
    KS/AUC em teste — mesma régua para todos os métodos, independente de como
    cada um internamente ajustou/regularizou durante a seleção.
    """
    if not variaveis:
        return {"ks_teste": 0.0, "auc_teste": 0.5, "n_vars": 0}

    estimator = LogisticGLM()
    modelo = estimator.fit(df_dev[variaveis], df_dev["y"])
    prob_teste = modelo.predict_proba(df_teste[variaveis])
    auc = roc_auc_score(df_teste["y"], prob_teste)

    metric = KSGaussianMetric(criterio="teste")
    ks = metric(modelo, df_dev[variaveis], df_dev["y"], df_teste[variaveis], df_teste["y"])
    return {"ks_teste": ks, "auc_teste": auc, "n_vars": len(variaveis)}


def avaliar_recuperacao(variaveis: list[str]) -> dict[str, object]:
    bases_selecionadas = {extrair_base(v) for v in variaveis}
    verdadeiros_positivos = bases_selecionadas & BASES_INFORMATIVAS
    falsos_positivos = bases_selecionadas & BASES_RUIDO
    return {
        "bases_selecionadas": sorted(bases_selecionadas),
        "recall_bases_informativas": len(verdadeiros_positivos) / len(BASES_INFORMATIVAS),
        "n_bases_ruido_incluidas": len(falsos_positivos),
    }


def rodar_pedro_wise(df_dev: pd.DataFrame, df_teste: pd.DataFrame, *, shadow_probing: bool) -> list[str]:
    from pedro_wise.types import ShadowProbingConfig

    estimator = LogisticGLM()
    metric = KSGaussianMetric(criterio="teste")
    modelo_nulo = estimator.fit(df_dev[[]], df_dev["y"])
    score_nulo = metric(modelo_nulo, df_dev[[]], df_dev["y"], df_teste[[]], df_teste["y"])
    estado_inicial = SelectionState(variables=(), model=modelo_nulo, score=score_nulo)

    config1 = Level1Config(shadow_probing=ShadowProbingConfig(ativado=shadow_probing, semente=7))
    config2 = Level2Config(n_best_duplo=5, n_best_triplo_1=3, n_best_triplo_2=3)

    estado_final, _ = run_pedro_wise(estimator, metric, df_dev, df_teste, estado_inicial, config1, config2)
    return list(estado_final.variables)


def rodar_lasso(df_dev: pd.DataFrame, colunas: list[str]) -> list[str]:
    """LASSO logístico com C escolhido por CV (5-fold), coeficientes padronizados."""
    scaler = StandardScaler()
    X = scaler.fit_transform(df_dev[colunas])
    modelo = LogisticRegressionCV(
        Cs=10, cv=5, penalty="l1", solver="liblinear", scoring="roc_auc", random_state=0, max_iter=2000
    )
    modelo.fit(X, df_dev["y"])
    coefs = modelo.coef_[0]
    return [v for v, c in zip(colunas, coefs, strict=True) if abs(c) > 1e-6]


def rodar_stability_selection(
    df_dev: pd.DataFrame,
    colunas: list[str],
    *,
    n_reamostragens: int = 100,
    limiar: float = 0.6,
    c_regularizacao: float = 0.05,
    semente: int = 0,
) -> tuple[list[str], pd.Series]:
    """Stability selection (Meinshausen & Bühlmann 2010): reamostra sem
    reposição (metade dos dados) B vezes, roda LASSO com C fixo em cada
    reamostragem, e seleciona variáveis com frequência de seleção >= `limiar`.
    Ver docs/literatura/stability-selection.md.

    `c_regularizacao=0.05` **não é o C que o CV escolheria** para um fit único
    (aqui o LASSO-CV solo escolhe algo perto de C=0.5-1). Testado em varredura
    manual (C em 0.5, 0.2, 0.1, 0.05, 0.02, 0.01): C=0.5 deixa ruído passar de
    83-87% de frequência (quase indistinguível do sinal real a 100%); C=0.05 é
    o ponto onde sinal fica em 100% e ruído cai para <=11%. C=0.02 já é forte
    demais e começa a perder `x3_woe` (0.49). Confirma na prática o que a
    literatura já avisa: stability selection precisa de regularização mais
    forte que a de um fit único via CV — é a instabilidade sob regularização
    agressiva, não a regularização em si, que separa sinal de ruído.
    """
    rng = np.random.default_rng(semente)
    n = len(df_dev)
    contagem = pd.Series(0, index=colunas, dtype=int)

    scaler = StandardScaler()
    X_completo = scaler.fit_transform(df_dev[colunas])
    y_completo = df_dev["y"].to_numpy()

    for _ in range(n_reamostragens):
        indices = rng.choice(n, size=n // 2, replace=False)
        modelo = LogisticRegression(
            penalty="l1", solver="liblinear", C=c_regularizacao, random_state=0, max_iter=2000
        )
        modelo.fit(X_completo[indices], y_completo[indices])
        selecionadas = np.abs(modelo.coef_[0]) > 1e-6
        contagem.loc[np.array(colunas)[selecionadas]] += 1

    frequencia = contagem / n_reamostragens
    selecionadas = frequencia[frequencia >= limiar].index.tolist()
    return selecionadas, frequencia.sort_values(ascending=False)


def main() -> None:
    df_dev = pd.read_csv(DIR_DADOS / "dev.csv")
    df_teste = pd.read_csv(DIR_DADOS / "teste.csv")
    colunas = [c for c in df_dev.columns if c != "y"]

    print(f"Dataset: {len(df_dev)} linhas dev, {len(df_teste)} linhas teste, {len(colunas)} candidatas")
    print(f"Bases informativas (gabarito): {sorted(BASES_INFORMATIVAS)}")
    print(f"Bases de ruído (gabarito): {sorted(BASES_RUIDO)}\n")

    resultados = {}

    print("Rodando Pedro_Wise (sem shadow probing)...")
    vars_pw = rodar_pedro_wise(df_dev, df_teste, shadow_probing=False)
    resultados["Pedro_Wise"] = vars_pw

    print("Rodando Pedro_Wise (com shadow probing)...")
    vars_pw_shadow = rodar_pedro_wise(df_dev, df_teste, shadow_probing=True)
    resultados["Pedro_Wise + shadow probing"] = vars_pw_shadow

    print("Rodando LASSO (CV)...")
    vars_lasso = rodar_lasso(df_dev, colunas)
    resultados["LASSO"] = vars_lasso

    print("Rodando stability selection (100 reamostragens)...")
    vars_stability, frequencias = rodar_stability_selection(df_dev, colunas)
    resultados["Stability Selection"] = vars_stability

    print("\n" + "=" * 78)
    print(f"{'Método':<28} {'Vars':<40} {'KS-teste':>8} {'AUC':>6} {'Recall':>7} {'Ruído':>6}")
    print("=" * 78)
    for nome, variaveis in resultados.items():
        metricas = avaliar_variaveis(variaveis, df_dev, df_teste)
        recuperacao = avaliar_recuperacao(variaveis)
        vars_str = ",".join(sorted(variaveis)) if variaveis else "(nenhuma)"
        if len(vars_str) > 38:
            vars_str = vars_str[:35] + "..."
        print(
            f"{nome:<28} {vars_str:<40} {metricas['ks_teste']:>8.4f} {metricas['auc_teste']:>6.3f} "
            f"{recuperacao['recall_bases_informativas']:>7.0%} {recuperacao['n_bases_ruido_incluidas']:>6d}"
        )

    print("\nFrequência de seleção (stability selection, top 10):")
    print(frequencias.head(10).to_string())


if __name__ == "__main__":
    main()
