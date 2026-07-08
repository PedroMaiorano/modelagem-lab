"""Algoritmos de binning (discretização de variável contínua em faixas).

Ver `docs/literatura/categorizacao.md` para a literatura. Quatro estratégias,
da mais simples (não-supervisionada) à mais alinhada com a prática de
scorecards (monotônica supervisionada):

- `bins_largura_igual` / `bins_frequencia_igual`: baseline não-supervisionado.
- `bins_arvore`: usa uma árvore de decisão rasa como discretizador supervisionado
  — split por ganho de informação, análogo em espírito ao uso de árvores em
  C4.5 (Quinlan 1996, ver literatura).
- `bins_monotonicos`: força a taxa de evento a ser monotônica entre bins
  adjacentes via merge guloso — versão pragmática (não ótima via MIP) da
  ideia central do OptBinning (Navas-Palencia 2020). Documentado como
  aproximação deliberada, não a solução ótima da literatura.

Todas retornam `edges: np.ndarray` (quebras) compatível com `aplicar_bins`.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

_EPS = 1e-9


def bins_largura_igual(x: pd.Series, n_bins: int = 10) -> np.ndarray:
    """Quebras de largura igual (não-supervisionado) — baseline."""
    lo, hi = x.min(), x.max()
    return np.linspace(lo, hi, n_bins + 1)


def bins_frequencia_igual(x: pd.Series, n_bins: int = 10) -> np.ndarray:
    """Quebras por quantil (não-supervisionado) — mesma contagem por bin."""
    quantis = np.linspace(0, 1, n_bins + 1)
    edges = np.quantile(x, quantis)
    return np.unique(edges)  # remove quebras duplicadas (empates em quantis)


def bins_arvore(x: pd.Series, y: pd.Series, max_folhas: int = 10, min_amostras_folha: int = 50) -> np.ndarray:
    """Discretização supervisionada via árvore de decisão rasa: os splits da
    árvore (por ganho de informação) viram as quebras de bin. Análogo em
    espírito a C4.5 (Quinlan 1996) — não é o algoritmo original, é a mesma
    ideia aplicada como discretizador isolado em vez de parte de uma árvore
    de classificação completa.
    """
    from sklearn.tree import DecisionTreeClassifier

    arvore = DecisionTreeClassifier(max_leaf_nodes=max_folhas, min_samples_leaf=min_amostras_folha)
    arvore.fit(x.to_numpy().reshape(-1, 1), y)

    limiares = arvore.tree_.threshold[arvore.tree_.feature >= 0]
    edges = np.sort(np.unique(limiares))
    return np.concatenate([[x.min()], edges, [x.max()]])


@dataclass(frozen=True)
class ResultadoMonotonico:
    edges: np.ndarray
    taxa_evento_por_bin: np.ndarray
    n_merges: int


def bins_monotonicos(
    x: pd.Series, y: pd.Series, n_bins_inicial: int = 20, direcao: str = "auto"
) -> ResultadoMonotonico:
    """Bins com taxa de evento monotônica: parte de `n_bins_inicial` bins por
    frequência igual e faz merge guloso de bins adjacentes até a sequência de
    taxas de evento ficar monotônica (crescente ou decrescente).

    **Aproximação pragmática, não a solução ótima.** A literatura (OptBinning,
    Navas-Palencia 2020, ver `docs/literatura/categorizacao.md`) formula isso
    como programação matemática com garantia de otimalidade; aqui é um merge
    guloso simples — mais barato, sem essa garantia. Suficiente para uso
    exploratório; para produção de scorecard formal, considerar migrar para
    `optbinning` (pacote Python que implementa a versão ótima).

    `direcao="auto"` decide crescente/decrescente pela correlação de Spearman
    entre bin e taxa de evento nos bins iniciais.
    """
    edges_iniciais = bins_frequencia_igual(x, n_bins_inicial)
    bin_idx = pd.cut(x, list(edges_iniciais), include_lowest=True, labels=False)

    df_bin = pd.DataFrame({"bin": bin_idx, "y": y})
    contagens = df_bin.groupby("bin", observed=True)["y"].agg(["sum", "count"]).sort_index()
    taxas = (contagens["sum"] / contagens["count"]).to_numpy()
    edges_atuais = list(edges_iniciais)

    if direcao == "auto":
        crescente = bool(pd.Series(taxas).corr(pd.Series(range(len(taxas))), method="spearman") >= 0)
    else:
        crescente = direcao == "crescente"

    n_merges = 0
    contagens_evento = contagens["sum"].to_numpy().astype(float)
    contagens_total = contagens["count"].to_numpy().astype(float)

    while len(taxas) > 1:
        violacoes = (
            np.diff(taxas) < -_EPS if crescente else np.diff(taxas) > _EPS
        )
        if not violacoes.any():
            break
        i = int(np.argmax(violacoes))  # primeira violação: bin i e i+1 trocam de ordem
        # merge bin i e i+1: soma contagens, remove a quebra entre eles
        contagens_evento[i] += contagens_evento[i + 1]
        contagens_total[i] += contagens_total[i + 1]
        contagens_evento = np.delete(contagens_evento, i + 1)
        contagens_total = np.delete(contagens_total, i + 1)
        taxas = contagens_evento / contagens_total
        del edges_atuais[i + 1]
        n_merges += 1

    return ResultadoMonotonico(edges=np.array(edges_atuais), taxa_evento_por_bin=taxas, n_merges=n_merges)


def aplicar_bins(x: pd.Series, edges: np.ndarray) -> pd.Series:
    """Mapeia `x` para o índice do bin (0-based), usando `edges` já ajustadas
    (em `bins_*`). Valores fora do range de `edges` caem no bin extremo mais
    próximo (`include_lowest=True` + clip).
    """
    edges_ajustadas = edges.copy()
    edges_ajustadas[0] = min(edges_ajustadas[0], x.min())
    edges_ajustadas[-1] = max(edges_ajustadas[-1], x.max())
    return pd.cut(x, list(edges_ajustadas), include_lowest=True, labels=False).astype("Int64")
