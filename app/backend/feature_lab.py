"""Lógica do backend pro Feature-lab (esferas 1/2 — agregação temporal e
descoberta de interação, ver `python/agregacao_temporal` e `python/interacao`).
Este módulo só orquestra: lê dado de disco, chama o core, empacota resultado
pra API — mesma regra do resto do backend (núcleo em `python/`, backend
nunca reimplementa lógica de modelagem, ver `logica.py`).

Fluxo único e sequencial (não dois "modos" separados — feedback real: dois
formulários quase idênticos era confuso). `listar_bases` devolve TODA base
disponível (painel ou já-flat) com o tipo marcado, mas o tipo é só uma
SUGESTÃO de default pra interface — a decisão de rodar esfera 1 ou não é do
usuário (toggle explícito), não uma trava automática: `agregar_base` aceita
qualquer base (painel OU flat) contanto que o usuário escolha colunas de
chave/tempo válidas nela.

- **painel** (`data/{nome}/painel.csv`, uma linha por chave-tempo): o caso
  natural pra esfera 1 -- já tem colunas de chave/tempo sugeridas.
- **flat** (mesmos `dev.csv`/`teste.csv` que o Pedro_Wise usa, via
  `logica.carregar_dataset`): normalmente pula esfera 1 (`rodar_direto`),
  mas nada impede o usuário de escolher chave/tempo manualmente ali também
  se fizer sentido pro caso dele.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any, Literal

_RAIZ = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_RAIZ / "python"))

import pandas as pd  # noqa: E402
import pipeline_lab.esfera1 as pipeline_lab_esfera1  # noqa: E402
import pipeline_lab.esfera2 as pipeline_lab_esfera2  # noqa: E402
from agregacao_temporal import extrair_base_agregado  # noqa: E402
from categorizacao import aplicar_bins, bins_frequencia_igual  # noqa: E402
from interacao import (  # noqa: E402
    Condicao,
    Regra,
    avaliar_estabilidade,
    extrair_candidatas,
    regras_para_colunas,
)
from pedro_wise.estimators import LogisticGLM  # noqa: E402
from pedro_wise.metrics import KSGaussianMetric  # noqa: E402
from pedro_wise.pipeline import run_pedro_wise  # noqa: E402
from pedro_wise.types import SelectionState  # noqa: E402
from sklearn.metrics import roc_auc_score  # noqa: E402
from transformacao.woe import ajustar_woe  # noqa: E402

DIR_PAINEIS = _RAIZ / "data"

#: Nomes de coluna candidatos a "tempo/safra" quando sugerindo defaults pro
#: usuário -- heurística simples, o usuário sempre pode trocar na interface.
_CANDIDATOS_TEMPO = {"safra", "data", "mes", "tempo", "competencia", "anomes"}


def listar_paineis() -> list[str]:
    """Pastas em `data/` que têm `painel.csv` -- candidatas à esfera 1."""
    if not DIR_PAINEIS.exists():
        return []
    return sorted(p.name for p in DIR_PAINEIS.iterdir() if p.is_dir() and (p / "painel.csv").exists())


def listar_bases() -> list[dict[str, str]]:
    """Toda base disponível pro Feature-lab, com o tipo marcado -- um seletor
    só, em vez de dois formulários separados pra "painel" e "dataset flat".
    Painel tem prioridade se a mesma pasta tiver os dois formatos (não
    deveria acontecer na prática, mas evita ambiguidade)."""
    from logica import listar_datasets  # import tardio evita ciclo com main.py

    paineis = set(listar_paineis())
    bases = [{"nome": n, "tipo": "painel"} for n in sorted(paineis)]
    bases += [{"nome": n, "tipo": "flat"} for n in listar_datasets() if n not in paineis]
    return bases


def info_painel(nome: str, coluna_y: str = "y") -> dict[str, Any]:
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
    # Candidatas pra esfera 2 quando a esfera 1 tá desligada: só coluna
    # numérica de verdade -- não pode depender de qual coluna foi sugerida
    # como chave/tempo (bug real: `contrato`/`safra` sumiam da lista de
    # candidatas mesmo com a esfera 1 desativada, porque o estado de
    # chave/tempo continuava marcado). Coluna de texto (chave, safra em
    # formato "2024-01" etc.) não entra num classificador numérico de
    # qualquer forma, então o filtro certo é por tipo, não por seleção.
    # `coluna_y` também sai daqui -- nunca é candidata a feature de si mesma.
    colunas_numericas = [c for c in colunas if c != coluna_y and pd.api.types.is_numeric_dtype(df[c])]

    return {
        "colunas": colunas,
        "colunas_numericas": colunas_numericas,
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


def _carregar_tabela_base(base: str, tipo: Literal["painel", "flat"]) -> tuple[pd.DataFrame, Path | None]:
    """Carrega a tabela bruta de uma base, seja painel (`painel.csv`) ou
    flat (`dev.csv`+`teste.csv` concatenados, via `logica.carregar_dataset`).
    Devolve também o caminho de `agregado.csv` (só faz sentido pra painel,
    onde o alvo pode morar num arquivo à parte) -- `None` pra flat, que já
    carrega `y` junto."""
    if tipo == "painel":
        pasta = DIR_PAINEIS / base
        caminho_painel = pasta / "painel.csv"
        if not caminho_painel.exists():
            raise ValueError(f"Painel '{base}' não encontrado")
        return pd.read_csv(caminho_painel), pasta / "agregado.csv"

    from logica import carregar_dataset  # import tardio evita ciclo com main.py

    df_dev, df_teste = carregar_dataset(base)
    return pd.concat([df_dev, df_teste], ignore_index=True), None


def valores_distintos_base(
    base: str, tipo: Literal["painel", "flat"], coluna: str, limite: int = 50
) -> list[dict[str, Any]]:
    """Valores distintos de uma coluna da base, com contagem -- pra
    interface montar um seletor de "o que é treino/o que é teste" com
    opções reais em vez de pedir pro usuário digitar às cegas (mesmo
    padrão de `ingestao.valores_distintos`, mas em cima de uma base do
    Feature-lab em vez de um upload em staging)."""
    df, _ = _carregar_tabela_base(base, tipo)
    if coluna not in df.columns:
        raise ValueError(f"Coluna '{coluna}' não existe em '{base}'")
    contagens = df[coluna].astype(str).value_counts().head(limite)
    return [{"valor": v, "contagem": int(c)} for v, c in contagens.items()]


def carregar_base_bruta(base: str, tipo: Literal["painel", "flat"], coluna_y: str = "y") -> dict[str, Any]:
    """Carrega a base sem passar pela esfera 1 -- caminho pro toggle de
    agregação desligado mesmo numa base tipo painel (cada usuário decide,
    não é travado pelo tipo). Devolve como registros, no mesmo formato que
    `descobrir_em_tabela` espera. `coluna_y` é renomeada pra "y" aqui dentro
    -- o resto do código sempre trabalha com o nome interno fixo.

    Base painel sem a coluna resposta nas linhas brutas (comum -- o alvo
    geralmente vive só no ponto de observação agregado, não em cada linha
    do histórico bruto) levanta erro claro em vez de silenciosamente não
    achar o alvo: sem rodar a esfera 1 primeiro, não tem como saber qual
    linha do histórico de cada chave é "a" observação a associar ao alvo.
    """
    df, caminho_alvo = _carregar_tabela_base(base, tipo)
    if coluna_y not in df.columns:
        raise ValueError(
            f"Base '{base}' não tem coluna '{coluna_y}' nas linhas brutas -- rode a esfera 1 primeiro "
            "(o alvo normalmente só existe no ponto de observação agregado, não no histórico bruto)"
        )
    if coluna_y != "y":
        df = df.rename(columns={coluna_y: "y"})
    return {"tabela": df.to_dict(orient="records"), "colunas": list(df.columns), "n_linhas": len(df)}


#: Núcleo da esfera 1 mora em `pipeline_lab.esfera1` (biblioteca standalone,
#: sem disco/FastAPI) -- alias aqui só pra não quebrar quem já importa
#: `_agregar_df` deste módulo (ex.: `logica.py`).
_agregar_df = pipeline_lab_esfera1.agregar


def agregar_base(
    base: str,
    tipo: Literal["painel", "flat"],
    chave: str,
    coluna_tempo: str,
    colunas_valor: list[str],
    janelas: list[int],
    coluna_y: str = "y",
) -> dict[str, Any]:
    """Esfera 1 sobre uma base já salva (painel ou dataset flat do
    feature-lab). Devolve a tabela pronta (com `y` -- `coluna_y` renomeada
    internamente, o resto do código sempre trabalha com o nome fixo), a
    lista de colunas geradas, e as contagens brutas (pra resumo na
    interface). Ver `_agregar_df` pro núcleo da agregação em si.
    """
    df, caminho_alvo = _carregar_tabela_base(base, tipo)
    por_chave, colunas_geradas = _agregar_df(df, chave, coluna_tempo, colunas_valor, janelas)

    if coluna_y in por_chave.columns:
        if coluna_y != "y":
            por_chave = por_chave.rename(columns={coluna_y: "y"})
    else:
        if caminho_alvo is None or not caminho_alvo.exists():
            raise ValueError(f"Base '{base}' não tem coluna '{coluna_y}' nem agregado.csv com o alvo")
        alvo_bruto = pd.read_csv(caminho_alvo)
        if coluna_y not in alvo_bruto.columns:
            raise ValueError(f"agregado.csv de '{base}' não tem coluna '{coluna_y}'")
        alvo = alvo_bruto[[chave, coluna_y]].rename(columns={coluna_y: "y"})
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
                # condições brutas -- a interface manda de volta quando o
                # usuário quer usar uma regra descoberta na esfera 2 como
                # variável da esfera 3 (ver `_materializar_regras_em`).
                "condicoes": [
                    {"feature": c.feature, "operador": c.operador, "limiar": c.limiar}
                    for c in regra.condicoes
                ],
            }
        )
    return linhas


def _materializar_regras_em(
    dev: pd.DataFrame, teste: pd.DataFrame, regras: list[dict[str, Any]]
) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    """Materializa regras da esfera 2 (selecionadas pelo usuário) como
    colunas 0/1 em dev/teste JÁ separados -- reaproveita
    `regras_para_colunas`/`Regra.aplicar` (nunca reimplementa a avaliação de
    condição). Aplicado depois do split (não antes, e não devolvido pro
    cliente pra ser reenviado/re-splitado depois): se uma regra referenciar
    uma coluna categórica WOE-codificada (ex.: `Thallium_woe`), essa coluna só
    existe depois do split+WOE, e um round-trip cliente-servidor com re-split
    correria risco de embaralhar as linhas de outro jeito e produzir um dev/
    teste diferente do que gerou a regra."""
    if not regras:
        return dev, teste, []
    objetos = [
        Regra(tuple(Condicao(c["feature"], c["operador"], c["limiar"]) for c in r["condicoes"]))
        for r in regras
    ]
    colunas_regra_dev = regras_para_colunas(objetos, dev)
    colunas_regra_teste = regras_para_colunas(objetos, teste)
    dev = pd.concat([dev, colunas_regra_dev], axis=1)
    teste = pd.concat([teste, colunas_regra_teste], axis=1)
    return dev, teste, list(colunas_regra_dev.columns)


def _iv_univariado(df: pd.DataFrame, colunas: list[str], y: pd.Series) -> dict[str, float]:
    """IV de cada coluna sozinha (não em combinação) -- reaproveita o
    binning e o cálculo de IV que já existem (`categorizacao`,
    `transformacao.woe`), não reimplementa nada. Dá uma visão rápida de
    quais colunas geradas pela esfera 1 já são fortes por conta própria,
    antes de olhar as regras de interação da esfera 2.
    """
    resultado = {}
    for c in colunas:
        try:
            edges = bins_frequencia_igual(df[c], n_bins=10)
            bin_idx = aplicar_bins(df[c], edges)
            resultado[c] = ajustar_woe(bin_idx.astype(str), y).iv_total
        except (ValueError, IndexError):
            # coluna degenerada (constante, poucos valores distintos etc.)
            # -- não impede o cálculo das outras.
            resultado[c] = 0.0
    return resultado


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
    proporcao_variaveis_por_split: float | None = None,
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
        proporcao_variaveis_por_split=proporcao_variaveis_por_split,
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
    base: str,
    tipo: Literal["painel", "flat"],
    chave: str,
    coluna_tempo: str,
    colunas_valor: list[str],
    janelas: list[int],
    coluna_y: str = "y",
) -> dict[str, Any]:
    """Esfera 1 sozinha, empacotada pra API -- devolve a tabela resultante
    como registros (JSON-serializável) pra interface guardar e mandar de
    volta na chamada da esfera 2 (`descobrir_em_tabela`), sem precisar ler a
    base do disco de novo nem introduzir estado no backend entre as duas
    chamadas. `ivs`: poder preditivo de cada coluna, sozinha -- tanto das
    colunas geradas quanto das originais (no último período de cada chave,
    que é o que sobra na tabela depois do `groupby().tail(1)`) -- pra dar
    pra comparar se agregar ajudou ou não."""
    agregacao = agregar_base(base, tipo, chave, coluna_tempo, colunas_valor, janelas, coluna_y)
    tabela: pd.DataFrame = agregacao["tabela"]
    colunas_geradas: list[str] = agregacao["colunas_geradas"]
    tem_alvo = "y" in tabela.columns
    ivs = _iv_univariado(tabela, colunas_geradas, tabela["y"]) if tem_alvo else {}
    ivs_originais = _iv_univariado(tabela, colunas_valor, tabela["y"]) if tem_alvo else {}
    return {
        "tabela": tabela.to_dict(orient="records"),
        "colunas_geradas": colunas_geradas,
        "colunas_originais": colunas_valor,
        "ivs": ivs,
        "ivs_originais": ivs_originais,
        "taxa_evento": float(tabela["y"].mean()) if tem_alvo else None,
        "n_linhas_painel": agregacao["n_linhas_painel"],
        "n_chaves": agregacao["n_chaves"],
    }


def _dividir_dev_teste(
    df: pd.DataFrame,
    metodo_split: Literal["aleatorio", "coluna"],
    semente: int,
    coluna_split: str | None = None,
    valores_dev: list[str] | None = None,
    valores_teste: list[str] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Reaproveita as mesmas funções de split do fluxo de preparar dataset
    do Pedro_Wise (`ingestao.py`) -- nenhuma lógica de split nova aqui."""
    from ingestao import dividir_aleatorio, dividir_por_amostra_existente

    if metodo_split == "coluna":
        if not coluna_split or not valores_dev or not valores_teste:
            raise ValueError(
                "Informe coluna_split, valores_dev e valores_teste pro split por coluna existente"
            )
        if coluna_split not in df.columns:
            raise ValueError(f"Coluna de split '{coluna_split}' não existe na tabela")
        return dividir_por_amostra_existente(df, coluna_split, valores_dev, valores_teste)
    return dividir_aleatorio(df, proporcao_teste=0.5, semente=semente)


#: Núcleo mora em `pipeline_lab.esfera2` -- alias aqui só pra não quebrar
#: quem já importa `_transformar_categoricas_woe` deste módulo (`logica.py`,
#: `test_feature_lab.py`).
_transformar_categoricas_woe = pipeline_lab_esfera2.transformar_categoricas_woe


def descobrir_em_tabela(
    registros: list[dict[str, Any]],
    colunas_x: list[str],
    profundidade_maxima: int = 2,
    n_arvores: int = 60,
    min_suporte: float = 0.02,
    max_suporte: float = 0.5,
    max_regras: int = 10,
    permitir_cruzamento_entre_bases: bool = True,
    semente: int = 0,
    coluna_y: str = "y",
    proporcao_variaveis_por_split: float | None = None,
    metodo_split: Literal["aleatorio", "coluna"] = "aleatorio",
    coluna_split: str | None = None,
    valores_dev: list[str] | None = None,
    valores_teste: list[str] | None = None,
    colunas_categoricas: list[str] | None = None,
) -> dict[str, Any]:
    """Esfera 2 sobre uma tabela já em mãos (tipicamente a saída de
    `rodar_agregacao`) -- reconstrói o DataFrame, faz o split dev/teste
    (aleatório por padrão, ou por uma coluna de amostra já existente na
    base) e roda `_descobrir`. `colunas_categoricas`: subconjunto de
    `colunas_x` pra WOE-codificar antes (ver `_transformar_categoricas_woe`)
    -- colunas de texto entram nesse tratamento automaticamente."""
    if not colunas_x:
        raise ValueError("Selecione ao menos uma coluna candidata")
    if coluna_y not in (registros[0] if registros else {}):
        raise ValueError(f"Tabela sem coluna '{coluna_y}'")

    df = pd.DataFrame.from_records(registros)
    if coluna_y != "y":
        df = df.rename(columns={coluna_y: "y"})
    dev, teste = _dividir_dev_teste(df, metodo_split, semente, coluna_split, valores_dev, valores_teste)
    dev, teste, colunas_x = _transformar_categoricas_woe(dev, teste, colunas_x, colunas_categoricas or [])

    return _descobrir(
        dev[colunas_x],
        dev["y"],
        teste[colunas_x],
        teste["y"],
        profundidade_maxima,
        n_arvores,
        min_suporte,
        max_suporte,
        max_regras,
        permitir_cruzamento_entre_bases,
        semente,
        proporcao_variaveis_por_split,
    )


def rodar_direto(
    dataset: str,
    colunas_x: list[str],
    profundidade_maxima: int = 2,
    n_arvores: int = 60,
    min_suporte: float = 0.02,
    max_suporte: float = 0.5,
    max_regras: int = 10,
    permitir_cruzamento_entre_bases: bool = True,
    coluna_y: str = "y",
    proporcao_variaveis_por_split: float | None = None,
    colunas_categoricas: list[str] | None = None,
) -> dict[str, Any]:
    """Modo direto: pula a esfera 1 -- usa um dataset já flat (mesmo
    dev.csv/teste.csv do Pedro_Wise, já com split dev/teste pronto) direto
    na esfera 2. Pra bases sem granularidade de painel mensal."""
    from logica import carregar_dataset  # import tardio evita ciclo com main.py

    if not colunas_x:
        raise ValueError("Selecione ao menos uma coluna candidata")

    df_dev, df_teste = carregar_dataset(dataset)
    faltando = [c for c in [*colunas_x, coluna_y] if c not in df_dev.columns]
    if faltando:
        raise ValueError(f"Coluna(s) ausente(s) no dataset: {faltando}")
    if coluna_y != "y":
        df_dev = df_dev.rename(columns={coluna_y: "y"})
        df_teste = df_teste.rename(columns={coluna_y: "y"})
    df_dev, df_teste, colunas_x = _transformar_categoricas_woe(
        df_dev, df_teste, colunas_x, colunas_categoricas or []
    )

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
        proporcao_variaveis_por_split=proporcao_variaveis_por_split,
    )


def rodar_regressao_manual(
    registros: list[dict[str, Any]],
    colunas_x: list[str],
    coluna_y: str = "y",
    metodo_split: Literal["aleatorio", "coluna"] = "aleatorio",
    coluna_split: str | None = None,
    valores_dev: list[str] | None = None,
    valores_teste: list[str] | None = None,
    semente: int = 0,
    regras: list[dict[str, Any]] | None = None,
    colunas_categoricas: list[str] | None = None,
) -> dict[str, Any]:
    """Esfera 3: monta uma regressão logística com as variáveis que o
    usuário escolher (agregadas, brutas, ou qualquer coluna disponível),
    ajustada via o mesmo `LogisticGLM`/`KSGaussianMetric` que o Pedro_Wise
    usa -- núcleo nunca reimplementado, só reaproveitado aqui pra um
    ajuste manual em vez da busca automática. `regras`: regras da esfera 2
    (opcional) materializadas como coluna 0/1 e somadas a `colunas_x` --
    split, WOE de categórica e materialização de regra acontecem todos
    aqui dentro, numa única chamada, pra nunca correr risco de um dev/teste
    diferente do que gerou a regra (ver `_materializar_regras_em`)."""
    if not colunas_x and not regras:
        raise ValueError("Selecione ao menos uma coluna")
    if coluna_y not in (registros[0] if registros else {}):
        raise ValueError(f"Tabela sem coluna '{coluna_y}'")

    df = pd.DataFrame.from_records(registros)
    if coluna_y != "y":
        df = df.rename(columns={coluna_y: "y"})
    dev, teste = _dividir_dev_teste(df, metodo_split, semente, coluna_split, valores_dev, valores_teste)
    dev, teste, colunas_x = _transformar_categoricas_woe(dev, teste, colunas_x, colunas_categoricas or [])
    dev, teste, colunas_regra = _materializar_regras_em(dev, teste, regras or [])
    colunas_x = [*colunas_x, *colunas_regra]

    X_dev, y_dev = dev[colunas_x], dev["y"]
    X_teste, y_teste = teste[colunas_x], teste["y"]

    modelo = LogisticGLM().fit(X_dev, y_dev)
    ks_dev = KSGaussianMetric(criterio="dev")(modelo, X_dev, y_dev, X_teste, y_teste)
    ks_teste = KSGaussianMetric(criterio="teste")(modelo, X_dev, y_dev, X_teste, y_teste)

    prob_teste = modelo.predict_proba(X_teste)
    auc_teste = float(roc_auc_score(y_teste, prob_teste))

    from logica import _tabela_decis  # import tardio evita ciclo com main.py

    return {
        "coeficientes": modelo.coeficientes(),
        "estatisticas": modelo.estatisticas(),
        "ks_dev": ks_dev,
        "ks_teste": ks_teste,
        "auc_teste": auc_teste,
        "n_dev": len(dev),
        "n_teste": len(teste),
        "taxa_evento_dev": float(y_dev.mean()),
        "taxa_evento_teste": float(y_teste.mean()),
        "tabela_decis": _tabela_decis(y_teste, prob_teste),
    }


def _rodar_stepwise_pedro_wise(dev: pd.DataFrame, teste: pd.DataFrame, colunas: list[str]) -> dict[str, Any]:
    """Roda a seleção stepwise de verdade do Pedro_Wise (nível 1/2/2.5, mesmo
    `run_pedro_wise` que a aba principal usa) restrita a `colunas` como
    candidatas -- nenhuma lógica de seleção reimplementada aqui, só
    reaproveitada com um subconjunto de colunas diferente a cada chamada."""
    d, t = dev[[*colunas, "y"]], teste[[*colunas, "y"]]
    estimator = LogisticGLM()
    metric = KSGaussianMetric(criterio="teste")
    modelo_nulo = estimator.fit(d[[]], d["y"])
    score_nulo = metric(modelo_nulo, d[[]], d["y"], t[[]], t["y"])
    estado_inicial = SelectionState(variables=(), model=modelo_nulo, score=score_nulo)
    estado_final, _ = run_pedro_wise(estimator, metric, d, t, estado_inicial)

    variaveis = list(estado_final.variables)
    if variaveis:
        ks_teste = metric(estado_final.model, d[variaveis], d["y"], t[variaveis], t["y"])
        metric_dev = KSGaussianMetric(criterio="dev")
        ks_dev = metric_dev(estado_final.model, d[variaveis], d["y"], t[variaveis], t["y"])
        prob_teste = estado_final.model.predict_proba(t[variaveis])
        auc_teste = float(roc_auc_score(t["y"], prob_teste))
    else:
        ks_teste, ks_dev, auc_teste = 0.0, 0.0, 0.5

    return {
        "variaveis": variaveis,
        "n_variaveis": len(variaveis),
        "ks_dev": ks_dev,
        "ks_teste": ks_teste,
        "auc_teste": auc_teste,
    }


def comparar_com_pedro_wise(
    registros: list[dict[str, Any]],
    colunas_base: list[str],
    regras: list[dict[str, Any]],
    coluna_y: str = "y",
    metodo_split: Literal["aleatorio", "coluna"] = "aleatorio",
    coluna_split: str | None = None,
    valores_dev: list[str] | None = None,
    valores_teste: list[str] | None = None,
    semente: int = 0,
    colunas_categoricas: list[str] | None = None,
) -> dict[str, Any]:
    """Prova de valor das regras da esfera 2: roda a seleção stepwise real do
    Pedro_Wise duas vezes -- uma só com `colunas_base` como candidatas, outra
    com `colunas_base` + as regras (materializadas como coluna 0/1) também
    candidatas -- e devolve o KS/AUC de cada modelo final encontrado. Se o
    KS "com regras" não superar o "sem regras", as regras não estão
    agregando valor de verdade pra esse dataset (não é só uma opinião —
    é o mesmo critério de seleção usado na aba principal julgando).
    `colunas_categoricas`: mesmo tratamento WOE de `descobrir_em_tabela` --
    precisa ser aplicado aqui de novo (split + fit WOE só no dev) antes de
    materializar uma regra que referencie uma coluna categórica (ex.:
    `Thallium_woe`), senão essa coluna não existe na tabela pra avaliar a
    condição da regra."""
    if not colunas_base:
        raise ValueError("Selecione ao menos uma coluna base")

    df = pd.DataFrame.from_records(registros)
    if coluna_y not in df.columns:
        raise ValueError(f"Tabela sem coluna '{coluna_y}'")
    if coluna_y != "y":
        df = df.rename(columns={coluna_y: "y"})

    dev, teste = _dividir_dev_teste(df, metodo_split, semente, coluna_split, valores_dev, valores_teste)
    dev, teste, colunas_base = _transformar_categoricas_woe(
        dev, teste, colunas_base, colunas_categoricas or []
    )
    dev, teste, colunas_regra = _materializar_regras_em(dev, teste, regras)

    sem_regras = _rodar_stepwise_pedro_wise(dev, teste, colunas_base)
    if colunas_regra:
        com_regras = _rodar_stepwise_pedro_wise(dev, teste, [*colunas_base, *colunas_regra])
    else:
        com_regras = sem_regras

    return {
        "sem_regras": sem_regras,
        "com_regras": com_regras,
        "n_dev": len(dev),
        "n_teste": len(teste),
    }
