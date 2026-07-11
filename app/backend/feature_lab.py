"""Lógica do backend pro Feature-lab (esferas 1/2 — agregação temporal e
descoberta de interação, ver `python/agregacao_temporal` e `python/interacao`).
Este módulo só orquestra: lê o painel de disco, chama o core, empacota
resultado pra API — mesma regra do resto do backend (núcleo em `python/`,
backend nunca reimplementa lógica de modelagem, ver `logica.py`).

Fonte de dado por enquanto: pastas em `data/` com `painel.csv` (uma linha
por chave-tempo) e opcionalmente `agregado.csv` (alvo `y`, uma linha por
chave) — o mesmo formato que `scripts/gerar_dataset_painel_atraso.py` já
produz. Upload de painel real fica pra uma próxima etapa.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_RAIZ = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_RAIZ / "python"))

import pandas as pd  # noqa: E402
from agregacao_temporal import construir_agregados_janela, normalizar_safra  # noqa: E402
from interacao import avaliar_estabilidade, extrair_candidatas  # noqa: E402
from sklearn.linear_model import LogisticRegression  # noqa: E402
from sklearn.metrics import roc_auc_score  # noqa: E402
from sklearn.preprocessing import StandardScaler  # noqa: E402

DIR_PAINEIS = _RAIZ / "data"

#: Nomes de coluna candidatos a "tempo/safra" quando sugerindo defaults pro
#: usuário -- heurística simples, o usuário sempre pode trocar na interface.
_CANDIDATOS_TEMPO = {"safra", "data", "mes", "tempo", "competencia", "anomes"}


def listar_paineis() -> list[str]:
    """Pastas em `data/` que têm `painel.csv` -- candidatas a Feature-lab."""
    if not DIR_PAINEIS.exists():
        return []
    return sorted(p.name for p in DIR_PAINEIS.iterdir() if p.is_dir() and (p / "painel.csv").exists())


def info_painel(nome: str) -> dict[str, Any]:
    caminho = DIR_PAINEIS / nome / "painel.csv"
    if not caminho.exists():
        raise ValueError(f"Painel '{nome}' não encontrado")

    df = pd.read_csv(caminho)
    colunas = list(df.columns)
    chave_sugerida = colunas[0] if colunas else ""
    tempo_sugerido = next(
        (c for c in colunas if c.lower() in _CANDIDATOS_TEMPO),
        colunas[1] if len(colunas) > 1 else "",
    )
    colunas_valor_disponiveis = [c for c in colunas if c not in {chave_sugerida, tempo_sugerido}]

    return {
        "colunas": colunas,
        "chave_sugerida": chave_sugerida,
        "tempo_sugerido": tempo_sugerido,
        "colunas_valor_disponiveis": colunas_valor_disponiveis,
        "n_linhas": len(df),
        "n_chaves": int(df[chave_sugerida].nunique()) if chave_sugerida else 0,
    }


def _auc(X_dev: pd.DataFrame, y_dev: pd.Series, X_teste: pd.DataFrame, y_teste: pd.Series) -> float:
    # Escala (fit só em dev) -- variáveis com magnitudes bem diferentes
    # (dias vs. reais, por ex.) fazem o solver não convergir sem isso.
    escala = StandardScaler().fit(X_dev)
    modelo = LogisticRegression(max_iter=1000).fit(escala.transform(X_dev), y_dev)
    return float(roc_auc_score(y_teste, modelo.predict_proba(escala.transform(X_teste))[:, 1]))


def rodar_feature_lab(
    painel: str,
    chave: str,
    coluna_tempo: str,
    colunas_valor: list[str],
    janelas: list[int],
    profundidade_maxima: int = 2,
    n_arvores: int = 60,
    min_suporte: float = 0.02,
    max_suporte: float = 0.5,
    max_regras: int = 10,
    permitir_cruzamento_entre_bases: bool = True,
    semente: int = 0,
) -> dict[str, Any]:
    """Roda esfera 1 (agregação) + esfera 2 (descoberta de interação +
    validação out-of-time) de ponta a ponta -- mesmo fluxo de
    `scripts/explorar_feature_lab.py`, empacotado pra API. Sem estado entre
    chamadas (mesma filosofia do resto do playground de Módulos): cada
    requisição recalcula tudo do zero a partir dos parâmetros recebidos.
    """
    pasta = DIR_PAINEIS / painel
    caminho_painel = pasta / "painel.csv"
    caminho_alvo = pasta / "agregado.csv"
    if not caminho_painel.exists():
        raise ValueError(f"Painel '{painel}' não encontrado")
    if not colunas_valor:
        raise ValueError("Selecione ao menos uma coluna de valor pra agregar")

    df = pd.read_csv(caminho_painel)
    df["_tempo_norm"] = normalizar_safra(df[coluna_tempo])
    df = df.sort_values([chave, "_tempo_norm"]).reset_index(drop=True)

    agregado = df
    colunas_geradas: list[str] = []
    for valor in colunas_valor:
        agregado = construir_agregados_janela(
            agregado, chave=chave, tempo="_tempo_norm", valor=valor, janelas=janelas
        )
        colunas_geradas += [c for c in agregado.columns if c.startswith(f"{valor}_")]

    por_chave = agregado.groupby(chave, sort=False).tail(1).reset_index(drop=True)

    if "y" not in por_chave.columns:
        if not caminho_alvo.exists():
            raise ValueError(f"Painel '{painel}' não tem coluna 'y' nem agregado.csv com o alvo")
        alvo = pd.read_csv(caminho_alvo)[[chave, "y"]]
        por_chave = por_chave.merge(alvo, on=chave, how="inner")

    rng_split = por_chave.sample(frac=1, random_state=semente)
    metade = len(rng_split) // 2
    dev, teste = rng_split.iloc[:metade], rng_split.iloc[metade:]
    X_dev, y_dev = dev[colunas_geradas], dev["y"]
    X_teste, y_teste = teste[colunas_geradas], teste["y"]

    resultado: dict[str, Any] = {
        "n_linhas_painel": len(df),
        "n_chaves": int(df[chave].nunique()),
        "colunas_geradas": colunas_geradas,
        "n_dev": len(dev),
        "n_teste": len(teste),
        "taxa_evento_dev": float(y_dev.mean()),
        "taxa_evento_teste": float(y_teste.mean()),
        "regras": [],
        "melhor_regra": None,
        "auc_sem_regra": None,
        "auc_com_regra": None,
    }

    regras = extrair_candidatas(
        X_dev,
        y_dev,
        profundidade_maxima=profundidade_maxima,
        n_arvores=n_arvores,
        min_suporte=min_suporte,
        max_suporte=max_suporte,
        max_regras=max_regras,
        semente=semente,
        permitir_cruzamento_entre_bases=permitir_cruzamento_entre_bases,
    )
    if not regras:
        return resultado

    tabela = avaliar_estabilidade(regras, X_dev, y_dev, X_teste, y_teste)
    resultado["regras"] = tabela.to_dict(orient="records")

    melhor = regras[0]
    auc_sem = _auc(X_dev, y_dev, X_teste, y_teste)
    X_dev_regra = X_dev.assign(_regra=melhor.aplicar(X_dev).astype(int))
    X_teste_regra = X_teste.assign(_regra=melhor.aplicar(X_teste).astype(int))
    auc_com = _auc(X_dev_regra, y_dev, X_teste_regra, y_teste)

    resultado["melhor_regra"] = melhor.nome
    resultado["auc_sem_regra"] = auc_sem
    resultado["auc_com_regra"] = auc_com
    return resultado
