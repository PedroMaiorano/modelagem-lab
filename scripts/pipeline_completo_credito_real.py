"""Pipeline completo end-to-end no dataset real: construção -> categorização
-> transformação (WOE) -> treinamento (Pedro_Wise). Prova de integração dos
4 módulos do lab (docs/planos/expansao-modulos-2026-07-08.md) — não só cada
módulo isolado, mas a composição funcionando de ponta a ponta.

Compara contra o baseline já conhecido (Pedro_Wise direto nas variáveis
cruas, sem categorização/WOE — ver docs/referencias/datasets.md).

Uso: python scripts/pipeline_completo_credito_real.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "python"))

import pandas as pd
from categorizacao import aplicar_bins, bins_monotonicos
from construcao import construir_razoes_em_lote
from pedro_wise.estimators import LogisticGLM
from pedro_wise.metrics import KSGaussianMetric
from pedro_wise.pipeline import run_pedro_wise
from pedro_wise.types import Level1Config, Level2Config, SelectionState
from transformacao import ajustar_woe, aplicar_woe, classificar_iv

_reconfigure = getattr(sys.stdout, "reconfigure", None)
if _reconfigure is not None and sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    _reconfigure(encoding="utf-8", errors="replace")

DIR_DADOS = Path(__file__).resolve().parent.parent / "data" / "credito_real"

# Construção: razão "proporção paga da fatura" para os 6 meses disponíveis —
# feature de negócio óbvia que não existe nas colunas originais.
PARES_RAZAO = [(f"PAYAMT{i}", f"BILLAMT{i}", f"proppaga{i}") for i in range(1, 7)]


def construir_variaveis(df_dev: pd.DataFrame, df_teste: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    razoes_dev = construir_razoes_em_lote(df_dev, PARES_RAZAO)
    razoes_teste = construir_razoes_em_lote(df_teste, PARES_RAZAO)
    df_dev_aug = pd.concat([df_dev, razoes_dev], axis=1)
    df_teste_aug = pd.concat([df_teste, razoes_teste], axis=1)
    return df_dev_aug, df_teste_aug


def categorizar_e_transformar(
    df_dev: pd.DataFrame, df_teste: pd.DataFrame, colunas: list[str]
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, float]]:
    """Para cada coluna: ajusta bins monotônicos no dev, aplica em dev/teste,
    ajusta WOE no dev, aplica em dev/teste. Retorna os dois DataFrames só com
    as colunas `_woe` + `y`, e o IV de cada variável (para diagnóstico).
    """
    woe_dev = {"y": df_dev["y"]}
    woe_teste = {"y": df_teste["y"]}
    iv_por_variavel: dict[str, float] = {}

    for coluna in colunas:
        try:
            resultado_bin = bins_monotonicos(df_dev[coluna], df_dev["y"], n_bins_inicial=15)
            if len(resultado_bin.edges) < 3:  # variável quase constante -> bin único, sem informação
                continue
            bin_dev = aplicar_bins(df_dev[coluna], resultado_bin.edges)
            bin_teste = aplicar_bins(df_teste[coluna], resultado_bin.edges)

            tabela = ajustar_woe(bin_dev, df_dev["y"])
            nome_woe = f"{coluna}_woe"
            woe_dev[nome_woe] = aplicar_woe(bin_dev, tabela)
            woe_teste[nome_woe] = aplicar_woe(bin_teste, tabela)
            iv_por_variavel[coluna] = tabela.iv_total
        except (ValueError, IndexError) as e:
            print(f"  [pulado] {coluna}: {e}")

    return pd.DataFrame(woe_dev), pd.DataFrame(woe_teste), iv_por_variavel


def rodar_pedro_wise(df_dev: pd.DataFrame, df_teste: pd.DataFrame) -> tuple[list[str], float, float]:
    from sklearn.metrics import roc_auc_score

    estimator = LogisticGLM()
    metric = KSGaussianMetric(criterio="teste")
    modelo_nulo = estimator.fit(df_dev[[]], df_dev["y"])
    score_nulo = metric(modelo_nulo, df_dev[[]], df_dev["y"], df_teste[[]], df_teste["y"])
    estado_inicial = SelectionState(variables=(), model=modelo_nulo, score=score_nulo)

    estado_final, _ = run_pedro_wise(
        estimator, metric, df_dev, df_teste, estado_inicial, Level1Config(), Level2Config()
    )
    variaveis = list(estado_final.variables)
    prob_teste = estado_final.model.predict_proba(df_teste[variaveis])
    auc = float(roc_auc_score(df_teste["y"], prob_teste)) if variaveis else 0.5
    return variaveis, estado_final.score, auc


def main() -> None:
    t0 = time.perf_counter()
    df_dev = pd.read_csv(DIR_DADOS / "dev.csv")
    df_teste = pd.read_csv(DIR_DADOS / "teste.csv")

    print("=== 1. Construção ===")
    df_dev_aug, df_teste_aug = construir_variaveis(df_dev, df_teste)
    novas = [nome for _, _, nome in PARES_RAZAO]
    print(f"Variáveis construídas: {novas}")

    print("\n=== 2+3. Categorização + Transformação (WOE) ===")
    colunas_candidatas = [c for c in df_dev_aug.columns if c != "y"]
    df_dev_woe, df_teste_woe, iv_por_variavel = categorizar_e_transformar(
        df_dev_aug, df_teste_aug, colunas_candidatas
    )
    print(f"{len(iv_por_variavel)} variáveis viraram _woe (de {len(colunas_candidatas)} candidatas)")

    print("\nTop 10 por Information Value:")
    for var, iv in sorted(iv_por_variavel.items(), key=lambda kv: kv[1], reverse=True)[:10]:
        print(f"  {var:<15} IV={iv:.4f} ({classificar_iv(iv)})")

    print("\n=== 4. Treinamento (Pedro_Wise) sobre as variáveis _woe ===")
    variaveis_pipeline, ks_pipeline, auc_pipeline = rodar_pedro_wise(df_dev_woe, df_teste_woe)
    print(f"Selecionadas: {variaveis_pipeline}")
    print(f"KS-teste={ks_pipeline:.4f}  AUC={auc_pipeline:.4f}")

    print("\n=== Baseline: Pedro_Wise direto nas variáveis cruas (sem pipeline) ===")
    colunas_originais = [c for c in df_dev.columns if c != "y"]
    variaveis_baseline, ks_baseline, auc_baseline = rodar_pedro_wise(
        df_dev[["y", *colunas_originais]], df_teste[["y", *colunas_originais]]
    )
    print(f"Selecionadas: {variaveis_baseline}")
    print(f"KS-teste={ks_baseline:.4f}  AUC={auc_baseline:.4f}")

    print("\n=== Comparação ===")
    print(f"{'Abordagem':<35} {'KS-teste':>10} {'AUC':>8} {'N vars':>8}")
    print(f"{'Baseline (cru)':<35} {ks_baseline:>10.4f} {auc_baseline:>8.4f} {len(variaveis_baseline):>8}")
    linha_pipeline = f"{ks_pipeline:>10.4f} {auc_pipeline:>8.4f} {len(variaveis_pipeline):>8}"
    print(f"{'Pipeline completo (constr+cat+WOE)':<35} {linha_pipeline}")

    dt = time.perf_counter() - t0
    print(f"\nTempo total: {dt:.1f}s")


if __name__ == "__main__":
    main()
