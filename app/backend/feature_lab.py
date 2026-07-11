"""Lógica do backend pro Feature-lab (esferas 1/2 — agregação temporal e
descoberta de interação, ver `python/agregacao_temporal` e `python/interacao`).
Este módulo só orquestra: lê dado de disco, chama o core, empacota resultado
pra API — mesma regra do resto do backend (núcleo em `python/`, backend
nunca reimplementa lógica de modelagem, ver `logica.py`).

Duas fontes de dado, desacopladas de propósito (feedback real: nem todo
dataset tem granularidade de painel mensal, e forçar por esfera 1 pra
chegar na esfera 2 não faz sentido nesse caso):

- **Painel** (`data/{nome}/painel.csv`, uma linha por chave-tempo): passa
  pela esfera 1 (`agregar_painel`) antes da esfera 2.
- **Direto** (qualquer dataset já flat, os mesmos `dev.csv`/`teste.csv` que
  o Pedro_Wise usa, via `logica.carregar_dataset`): pula a esfera 1, vai
  direto pra esfera 2 com as colunas escolhidas como candidatas.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any

_RAIZ = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_RAIZ / "python"))

import pandas as pd  # noqa: E402
from agregacao_temporal import (  # noqa: E402
    construir_agregados_janela,
    extrair_base_agregado,
    normalizar_safra,
)
from interacao import avaliar_estabilidade, extrair_candidatas  # noqa: E402

DIR_PAINEIS = _RAIZ / "data"

#: Nomes de coluna candidatos a "tempo/safra" quando sugerindo defaults pro
#: usuário -- heurística simples, o usuário sempre pode trocar na interface.
_CANDIDATOS_TEMPO = {"safra", "data", "mes", "tempo", "competencia", "anomes"}


def listar_paineis() -> list[str]:
    """Pastas em `data/` que têm `painel.csv` -- candidatas ao modo agregação."""
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


def salvar_painel(nome: str, conteudo: pd.DataFrame) -> dict[str, Any]:
    """Grava um painel novo em `data/{nome}/painel.csv` -- fonte de dado pro
    modo agregação. Sem split dev/teste aqui (isso acontece na esfera 2, a
    partir do resultado já agregado uma-linha-por-chave)."""
    if conteudo.empty:
        raise ValueError("Arquivo vazio")
    if len(conteudo.columns) < 2:
        raise ValueError("Painel precisa de pelo menos 2 colunas (chave e um valor)")

    nome_seguro = "".join(c for c in nome if c.isalnum() or c in "-_") or "painel"
    pasta = DIR_PAINEIS / nome_seguro
    pasta.mkdir(parents=True, exist_ok=True)
    conteudo.to_csv(pasta / "painel.csv", index=False)
    return info_painel(nome_seguro) | {"nome": nome_seguro}


def agregar_painel(
    painel: str,
    chave: str,
    coluna_tempo: str,
    colunas_valor: list[str],
    janelas: list[int],
) -> dict[str, Any]:
    """Esfera 1: roda `construir_agregados_janela` pra cada `colunas_valor` e
    reduz a uma linha por chave (último período). Devolve a tabela pronta
    (com `y`, se disponível em `agregado.csv`), a lista de colunas geradas,
    e as contagens brutas do painel (pra resumo na interface).
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

    return {
        "tabela": por_chave,
        "colunas_geradas": colunas_geradas,
        "n_linhas_painel": len(df),
        "n_chaves": int(df[chave].nunique()),
    }


def _empacotar_regras(regras: list[Any], tabela: pd.DataFrame) -> list[dict[str, Any]]:
    """Junta a tabela de estabilidade (suporte/IV dev x teste) com metadados
    estruturais de cada regra (nº de condições, nº de variáveis distintas) --
    o que a interface precisa pra ordenar/filtrar por complexidade, não só
    por poder preditivo."""
    por_nome = {r.nome: r for r in regras}
    linhas = []
    for _, linha in tabela.iterrows():
        regra = por_nome[linha["regra"]]
        variaveis = {extrair_base_agregado(c.feature) for c in regra.condicoes}
        linhas.append(
            {
                "regra": linha["regra"],
                "n_condicoes": len(regra.condicoes),
                "n_variaveis": len(variaveis),
                "suporte_dev": float(linha["suporte_dev"]),
                "suporte_teste": float(linha["suporte_teste"]),
                "iv_dev": float(linha["iv_dev"]),
                "iv_teste": float(linha["iv_teste"]),
            }
        )
    return linhas


def _descobrir(
    X_dev: pd.DataFrame,
    y_dev: pd.Series,
    X_teste: pd.DataFrame,
    y_teste: pd.Series,
    profundidade_maxima: int,
    n_arvores: int,
    min_suporte: float,
    max_suporte: float,
    max_regras: int,
    permitir_cruzamento_entre_bases: bool,
    semente: int = 0,
) -> dict[str, Any]:
    """Esfera 2 + validação out-of-time, empacotado pra API. Não depende de
    nada de painel/agregação -- roda sobre qualquer par (X, y) já dividido
    em dev/teste."""
    t0 = time.perf_counter()
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
    regras_empacotadas: list[dict[str, Any]] = []
    if regras:
        tabela = avaliar_estabilidade(regras, X_dev, y_dev, X_teste, y_teste)
        regras_empacotadas = _empacotar_regras(regras, tabela)
    tempo_execucao = time.perf_counter() - t0

    return {
        "colunas_x": list(X_dev.columns),
        "n_dev": len(X_dev),
        "n_teste": len(X_teste),
        "taxa_evento_dev": float(y_dev.mean()),
        "taxa_evento_teste": float(y_teste.mean()),
        "regras": regras_empacotadas,
        "tempo_execucao_segundos": round(tempo_execucao, 2),
    }


def rodar_agregacao(
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
    """Modo com agregação: esfera 1 (painel -> uma linha por chave) seguida
    da esfera 2 sobre o resultado."""
    agregacao = agregar_painel(painel, chave, coluna_tempo, colunas_valor, janelas)
    por_chave, colunas_geradas = agregacao["tabela"], agregacao["colunas_geradas"]

    rng_split = por_chave.sample(frac=1, random_state=semente)
    metade = len(rng_split) // 2
    dev, teste = rng_split.iloc[:metade], rng_split.iloc[metade:]

    resultado = _descobrir(
        dev[colunas_geradas],
        dev["y"],
        teste[colunas_geradas],
        teste["y"],
        profundidade_maxima,
        n_arvores,
        min_suporte,
        max_suporte,
        max_regras,
        permitir_cruzamento_entre_bases,
        semente,
    )
    resultado["n_linhas_painel"] = agregacao["n_linhas_painel"]
    resultado["n_chaves"] = agregacao["n_chaves"]
    return resultado


def rodar_direto(
    dataset: str,
    colunas_x: list[str],
    profundidade_maxima: int = 2,
    n_arvores: int = 60,
    min_suporte: float = 0.02,
    max_suporte: float = 0.5,
    max_regras: int = 10,
    permitir_cruzamento_entre_bases: bool = True,
) -> dict[str, Any]:
    """Modo direto: pula a esfera 1 -- usa um dataset já flat (mesmo
    dev.csv/teste.csv do Pedro_Wise, já com split dev/teste pronto) direto
    na esfera 2. Pra bases sem granularidade de painel mensal."""
    from logica import carregar_dataset  # import tardio evita ciclo com main.py

    if not colunas_x:
        raise ValueError("Selecione ao menos uma coluna candidata")

    df_dev, df_teste = carregar_dataset(dataset)
    faltando = [c for c in [*colunas_x, "y"] if c not in df_dev.columns]
    if faltando:
        raise ValueError(f"Coluna(s) ausente(s) no dataset: {faltando}")

    return _descobrir(
        df_dev[colunas_x],
        df_dev["y"],
        df_teste[colunas_x],
        df_teste["y"],
        profundidade_maxima,
        n_arvores,
        min_suporte,
        max_suporte,
        max_regras,
        permitir_cruzamento_entre_bases,
    )
