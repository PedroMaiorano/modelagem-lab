"""Script pra explorar o feature-lab (esferas 1 e 2) sem precisar de UI ou
notebook -- roda no terminal, imprime os resultados. Pensado pra editar e
reexecutar: troque `CAMINHO_PAINEL`/`JANELAS`/`COLUNA_VALOR` pelos seus
dados reais quando quiser sair do sintético.

Uso: `python scripts/explorar_feature_lab.py`
(rode antes `python scripts/gerar_dataset_painel_atraso.py` se
`data/painel_atraso/painel.csv` ainda não existir)
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "python"))

import pandas as pd
from agregacao_temporal import construir_agregados_janela, normalizar_safra
from interacao import avaliar_estabilidade, extrair_candidatas
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

# --- Edite aqui pra usar seus próprios dados ---------------------------------
CAMINHO_PAINEL = Path(__file__).resolve().parent.parent / "data" / "painel_atraso" / "painel.csv"
# O alvo (y) normalmente não mora no painel mensal em si -- vive numa base à
# parte (uma linha por chave, o ponto de observação do scoring). Aqui é o
# `agregado.csv` que o gerador sintético já produz; troque pelo caminho da
# sua base de alvo real, ou None se seu painel já tiver a coluna `y` direto.
CAMINHO_ALVO: Path | None = Path(__file__).resolve().parent.parent / "data" / "painel_atraso" / "agregado.csv"
CHAVE = "contrato"
COLUNA_SAFRA = "safra"
COLUNA_VALOR = "dias_atraso"
JANELAS = [3, 6]
# ------------------------------------------------------------------------------


def main() -> None:
    if not CAMINHO_PAINEL.exists():
        print(f"Não achei {CAMINHO_PAINEL}.")
        print("Rode antes: python scripts/gerar_dataset_painel_atraso.py")
        return

    painel = pd.read_csv(CAMINHO_PAINEL)
    painel["safra_norm"] = normalizar_safra(painel[COLUNA_SAFRA])
    painel = painel.sort_values([CHAVE, "safra_norm"]).reset_index(drop=True)

    print(f"Painel: {len(painel)} linhas, {painel[CHAVE].nunique()} chaves, "
          f"{painel['safra_norm'].nunique()} safras")

    print("\n== Esfera 1: agregação temporal ==")
    agregado = construir_agregados_janela(
        painel, chave=CHAVE, tempo="safra_norm", valor=COLUNA_VALOR, janelas=JANELAS
    )
    colunas_geradas = [c for c in agregado.columns if c.startswith(f"{COLUNA_VALOR}_")]
    print(f"Colunas geradas: {colunas_geradas}")

    # Ponto de observação por contrato = último mês -- ajuste se seu caso for diferente.
    por_contrato = agregado.groupby(CHAVE, sort=False).tail(1).reset_index(drop=True)

    if "y" not in por_contrato.columns:
        if CAMINHO_ALVO is None or not CAMINHO_ALVO.exists():
            print("\n(sem coluna 'y' e sem CAMINHO_ALVO configurado -- pulando esferas 2/3)")
            return
        alvo = pd.read_csv(CAMINHO_ALVO)[[CHAVE, "y"]]
        por_contrato = por_contrato.merge(alvo, on=CHAVE, how="inner")

    rng_split = por_contrato.sample(frac=1, random_state=0)
    metade = len(rng_split) // 2
    dev, teste = rng_split.iloc[:metade], rng_split.iloc[metade:]
    X_dev, y_dev = dev[colunas_geradas], dev["y"]
    X_teste, y_teste = teste[colunas_geradas], teste["y"]

    print(f"\nSplit dev/teste: {len(dev)} / {len(teste)} contratos, "
          f"taxa de evento dev={y_dev.mean():.1%} teste={y_teste.mean():.1%}")

    print("\n== Esfera 2: descoberta de interação (RuleFit-style) ==")
    regras = extrair_candidatas(X_dev, y_dev, profundidade_maxima=2, n_arvores=60, max_regras=5, semente=0)
    if not regras:
        print("Nenhuma regra sobreviveu aos filtros de suporte -- tente ajustar min_suporte/max_suporte.")
        return

    print("\n== Validação out-of-time (dev vs. teste) ==")
    tabela = avaliar_estabilidade(regras, X_dev, y_dev, X_teste, y_teste)
    with pd.option_context("display.width", 160, "display.max_colwidth", 60):
        print(tabela.to_string(index=False))

    print("\n== Ganho de AUC ao adicionar a melhor regra ==")
    melhor = regras[0]
    coluna_regra = melhor.aplicar(X_dev).astype(int)
    coluna_regra_teste = melhor.aplicar(X_teste).astype(int)

    modelo_base = LogisticRegression(max_iter=1000).fit(X_dev, y_dev)
    auc_base = roc_auc_score(y_teste, modelo_base.predict_proba(X_teste)[:, 1])

    X_dev_com_regra = X_dev.assign(_melhor_regra=coluna_regra)
    X_teste_com_regra = X_teste.assign(_melhor_regra=coluna_regra_teste)
    modelo_com_regra = LogisticRegression(max_iter=1000).fit(X_dev_com_regra, y_dev)
    auc_com_regra = roc_auc_score(y_teste, modelo_com_regra.predict_proba(X_teste_com_regra)[:, 1])

    print(f"Regra: {melhor.nome}")
    print(f"AUC (teste) sem a regra: {auc_base:.4f}")
    print(f"AUC (teste) com a regra: {auc_com_regra:.4f}")


if __name__ == "__main__":
    main()
