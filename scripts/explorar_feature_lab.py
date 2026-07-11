"""Script pra explorar o feature-lab (esferas 1 e 2) sem precisar de UI ou
notebook -- roda no terminal, imprime os resultados. Pensado pra editar e
reexecutar: troque `CAMINHO_PAINEL`/`JANELAS`/`COLUNAS_VALOR` pelos seus
dados reais quando quiser sair do sintético.

Compara os dois modos de `extrair_candidatas`: livre (pode cruzar variáveis
brutas diferentes) vs. restrito à mesma base (regra de negócio que não quer
misturar domínios numa condição só) -- o dataset sintético tem sinal nos
dois formatos de propósito, pra deixar a diferença visível.

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
from sklearn.preprocessing import StandardScaler

# --- Edite aqui pra usar seus próprios dados ---------------------------------
CAMINHO_PAINEL = Path(__file__).resolve().parent.parent / "data" / "painel_atraso" / "painel.csv"
# O alvo (y) normalmente não mora no painel mensal em si -- vive numa base à
# parte (uma linha por chave, o ponto de observação do scoring). Aqui é o
# `agregado.csv` que o gerador sintético já produz; troque pelo caminho da
# sua base de alvo real, ou None se seu painel já tiver a coluna `y` direto.
CAMINHO_ALVO: Path | None = Path(__file__).resolve().parent.parent / "data" / "painel_atraso" / "agregado.csv"
CHAVE = "contrato"
COLUNA_SAFRA = "safra"
COLUNAS_VALOR = ["dias_atraso", "renda"]
JANELAS = [3]
# ------------------------------------------------------------------------------


def _imprimir_tabela(tabela: pd.DataFrame) -> None:
    with pd.option_context("display.width", 160, "display.max_colwidth", 60):
        print(tabela.to_string(index=False))


def _treinar_e_medir_auc(
    X_dev: pd.DataFrame, y_dev: pd.Series, X_teste: pd.DataFrame, y_teste: pd.Series
) -> float:
    # Escala (fit só em dev, aplica em teste -- mesmo padrão anti-leakage do
    # resto do lab): `dias_atraso` (dezenas) e `renda` (milhares) em escalas
    # bem diferentes fazem o solver do sklearn não convergir sem isso.
    escala = StandardScaler().fit(X_dev)
    modelo = LogisticRegression(max_iter=1000).fit(escala.transform(X_dev), y_dev)
    return float(roc_auc_score(y_teste, modelo.predict_proba(escala.transform(X_teste))[:, 1]))


def _auc_com_regra(regra, X_dev, y_dev, X_teste, y_teste) -> tuple[float, float]:  # type: ignore[no-untyped-def]
    auc_base = _treinar_e_medir_auc(X_dev, y_dev, X_teste, y_teste)

    X_dev_com_regra = X_dev.assign(_regra=regra.aplicar(X_dev).astype(int))
    X_teste_com_regra = X_teste.assign(_regra=regra.aplicar(X_teste).astype(int))
    auc_com_regra = _treinar_e_medir_auc(X_dev_com_regra, y_dev, X_teste_com_regra, y_teste)
    return auc_base, auc_com_regra


def main() -> None:
    if not CAMINHO_PAINEL.exists():
        print(f"Não achei {CAMINHO_PAINEL}.")
        print("Rode antes: python scripts/gerar_dataset_painel_atraso.py")
        return

    painel = pd.read_csv(CAMINHO_PAINEL)
    painel["safra_norm"] = normalizar_safra(painel[COLUNA_SAFRA])
    painel = painel.sort_values([CHAVE, "safra_norm"]).reset_index(drop=True)

    print(
        f"Painel: {len(painel)} linhas, {painel[CHAVE].nunique()} chaves, "
        f"{painel['safra_norm'].nunique()} safras, variáveis brutas: {COLUNAS_VALOR}"
    )

    print("\n== Esfera 1: agregação temporal ==")
    agregado = painel
    colunas_geradas: list[str] = []
    for valor in COLUNAS_VALOR:
        agregado = construir_agregados_janela(
            agregado, chave=CHAVE, tempo="safra_norm", valor=valor, janelas=JANELAS
        )
        colunas_geradas += [c for c in agregado.columns if c.startswith(f"{valor}_")]
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

    print(
        f"\nSplit dev/teste: {len(dev)} / {len(teste)} contratos, "
        f"taxa de evento dev={y_dev.mean():.1%} teste={y_teste.mean():.1%}"
    )

    for titulo, permitir_cruzamento in [
        ("permitir_cruzamento_entre_bases=True (livre)", True),
        ("permitir_cruzamento_entre_bases=False (só mesma variável bruta)", False),
    ]:
        print(f"\n== Esfera 2: descoberta de interação -- {titulo} ==")
        regras = extrair_candidatas(
            X_dev,
            y_dev,
            profundidade_maxima=2,
            n_arvores=60,
            max_regras=5,
            semente=0,
            permitir_cruzamento_entre_bases=permitir_cruzamento,
        )
        if not regras:
            print("Nenhuma regra sobreviveu aos filtros de suporte.")
            continue

        tabela = avaliar_estabilidade(regras, X_dev, y_dev, X_teste, y_teste)
        _imprimir_tabela(tabela)

        melhor = regras[0]
        auc_base, auc_com_regra = _auc_com_regra(melhor, X_dev, y_dev, X_teste, y_teste)
        print(f"Melhor regra: {melhor.nome}")
        print(f"AUC (teste) sem a regra: {auc_base:.4f}  |  com a regra: {auc_com_regra:.4f}")


if __name__ == "__main__":
    main()
