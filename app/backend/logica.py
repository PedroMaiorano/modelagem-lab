"""Camada de lógica do backend FastAPI — só consome `python/{pedro_wise,
categorizacao,transformacao,construcao}` (o core), nunca reimplementa
seleção/binning/WOE aqui. Mesma regra do `app/logica.py` (Streamlit v1).

Progresso em tempo real (sem tocar o core): o `pedro_wise` já loga cada
atualização aceita via `logger.info(...)` em todos os módulos (`selection`,
`level2`, `level3`, `pipeline`, `shadow_probing`). `CapturadorProgresso`
anexa um `logging.Handler` ao logger pai `pedro_wise` durante a execução e
publica cada registro numa fila — dá streaming real sem precisar modificar
uma única linha do core já testado.
"""

from __future__ import annotations

import logging
import queue
import sys
import time
from pathlib import Path
from typing import Any, Literal, NamedTuple

_RAIZ = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_RAIZ / "python"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from categorizacao import aplicar_bins, bins_monotonicos  # noqa: E402
from construcao import construir_diferenca, construir_razao  # noqa: E402
from pedro_wise.estimators import LogisticGLM  # noqa: E402
from pedro_wise.level3 import run_pedro_wise_completo  # noqa: E402
from pedro_wise.metrics import KSGaussianMetric  # noqa: E402
from pedro_wise.pipeline import run_pedro_wise  # noqa: E402
from pedro_wise.types import (  # noqa: E402
    Level1Config,
    Level2Config,
    Level3Config,
    SelectionState,
    ShadowProbingConfig,
)
from sklearn.metrics import roc_auc_score  # noqa: E402
from transformacao import ajustar_woe, aplicar_woe, classificar_iv, gerar_transformacoes_fixas  # noqa: E402

DIR_DADOS = _RAIZ / "data"

# Razões de negócio padrão para o dataset credito_real — mesmas do script de
# experimento (scripts/pipeline_completo_credito_real.py). Só aplicadas se
# as colunas existirem no dataset escolhido; funcionam como sugestão
# automática, não excluem pares customizados que o usuário adicionar na UI
# (ver ParConstrucao/rodar_construcao) — os dois se somam.
PARES_RAZAO_CREDITO_REAL = [(f"PAYAMT{i}", f"BILLAMT{i}", f"proppaga{i}") for i in range(1, 7)]


class ParConstrucao(NamedTuple):
    numerador: str
    denominador: str
    nome: str
    operacao: Literal["razao", "diferenca"] = "razao"


class CapturadorProgresso(logging.Handler):
    """Handler que publica cada log record numa fila thread-safe, como
    mensagem de progresso `{"tipo": "log", "mensagem": ...}`.
    """

    def __init__(self, fila: queue.Queue[dict[str, Any]]) -> None:
        super().__init__(level=logging.INFO)
        self._fila = fila

    def emit(self, record: logging.LogRecord) -> None:
        self._fila.put({"tipo": "log", "mensagem": self.format(record)})


def listar_datasets() -> list[str]:
    if not DIR_DADOS.exists():
        return []

    def _tem_dev_e_teste(p: Path) -> bool:
        return p.is_dir() and (p / "dev.csv").exists() and (p / "teste.csv").exists()

    return sorted(p.name for p in DIR_DADOS.iterdir() if _tem_dev_e_teste(p))


def carregar_dataset(nome: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    pasta = DIR_DADOS / nome
    return pd.read_csv(pasta / "dev.csv"), pd.read_csv(pasta / "teste.csv")


def preview_dataset(nome: str, n: int = 5) -> dict[str, Any]:
    df_dev, df_teste = carregar_dataset(nome)
    colunas_numericas = [c for c in df_dev.columns if c != "y" and pd.api.types.is_numeric_dtype(df_dev[c])]
    return {
        "colunas": list(df_dev.columns),
        "colunas_numericas": colunas_numericas,
        "n_dev": len(df_dev),
        "n_teste": len(df_teste),
        "amostra": df_dev.head(n).to_dict(orient="records"),
    }


def _construir(
    df_dev: pd.DataFrame,
    df_teste: pd.DataFrame,
    fila: queue.Queue[dict[str, Any]],
    pares_customizados: list[ParConstrucao] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    """Construção (razões/diferenças de negócio) — módulo isolado, ver
    `python/construcao/`. Dois tipos de pares, somados:
    - `PARES_RAZAO_CREDITO_REAL`: sugestão automática específica do dataset
      `credito_real`, aplicada só se as colunas existirem.
    - `pares_customizados`: definidos pelo usuário na UI (qualquer par de
      colunas numéricas do dataset ativo, razão ou diferença) — é o que
      generaliza o módulo pra além do `credito_real`.
    """
    pares_automaticos = [
        ParConstrucao(num, den, nome, "razao")
        for num, den, nome in PARES_RAZAO_CREDITO_REAL
        if num in df_dev.columns and den in df_dev.columns
    ]
    pares_customizados = pares_customizados or []
    pares_validos = [
        p for p in pares_customizados if p.numerador in df_dev.columns and p.denominador in df_dev.columns
    ]
    n_ignorados = len(pares_customizados) - len(pares_validos)
    if n_ignorados:
        fila.put(
            {"tipo": "log", "mensagem": f"  [pulado] {n_ignorados} par(es) customizados com coluna ausente"}
        )

    todos_pares = pares_automaticos + pares_validos
    if not todos_pares:
        return df_dev, df_teste, []

    fila.put({"tipo": "etapa", "mensagem": f"Construção: {len(todos_pares)} variáveis novas"})
    def _aplicar(p: ParConstrucao, df: pd.DataFrame) -> pd.Series:
        if p.operacao == "razao":
            return construir_razao(df[p.numerador], df[p.denominador], p.nome)
        return construir_diferenca(df[p.numerador], df[p.denominador], p.nome)

    novas_dev = {p.nome: _aplicar(p, df_dev) for p in todos_pares}
    novas_teste = {p.nome: _aplicar(p, df_teste) for p in todos_pares}
    df_dev = pd.concat([df_dev, pd.DataFrame(novas_dev, index=df_dev.index)], axis=1)
    df_teste = pd.concat([df_teste, pd.DataFrame(novas_teste, index=df_teste.index)], axis=1)
    return df_dev, df_teste, [p.nome for p in todos_pares]


def _categorizar_e_transformar(
    df_dev: pd.DataFrame,
    df_teste: pd.DataFrame,
    fila: queue.Queue[dict[str, Any]],
    gerar_transformacoes_potencia: bool = True,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, float]]:
    """Categorização (bins monotônicos) + transformação (WOE) — módulos
    isolados, ver `python/categorizacao/` e `python/transformacao/`. Para
    variáveis numéricas, opcionalmente também gera log/raiz/quad/cubo/
    inversas (`gerar_transformacoes_fixas`) como candidatas extras — o
    Pedro_Wise (nível 1, `transformacao_simples`) já sabe testar trocar a
    versão WOE por uma dessas via `pedro_wise.base.extrair_base`, desde que
    compartilhem o mesmo prefixo de base, que é o que garantimos aqui.
    """
    colunas_candidatas = [c for c in df_dev.columns if c != "y"]
    fila.put({"tipo": "etapa", "mensagem": f"Categorização + WOE: {len(colunas_candidatas)} candidatas"})

    woe_dev: dict[str, Any] = {"y": df_dev["y"]}
    woe_teste: dict[str, Any] = {"y": df_teste["y"]}
    iv_por_variavel: dict[str, float] = {}
    n_potencia = 0

    for coluna in colunas_candidatas:
        try:
            # datasets sintéticos do lab já nomeiam a variável crua com sufixo
            # "_woe" por convenção (ver docs/algoritmos-originais/pedro-wise-resumo.md)
            # — usamos a base semântica (sem esse sufixo) tanto pro nome WOE
            # quanto pras transformações de potência, senão elas ficariam com
            # bases diferentes e o Pedro_Wise nunca as veria como alternativas.
            base_semantica = coluna[:-4] if coluna.endswith("_woe") else coluna
            eh_numerica = pd.api.types.is_numeric_dtype(df_dev[coluna])

            if eh_numerica:
                # Numérica: categoriza (binning monotônico) antes do WOE.
                resultado_bin = bins_monotonicos(df_dev[coluna], df_dev["y"], n_bins_inicial=15)
                if len(resultado_bin.edges) < 3:
                    continue
                bin_dev = aplicar_bins(df_dev[coluna], resultado_bin.edges)
                bin_teste = aplicar_bins(df_teste[coluna], resultado_bin.edges)
            else:
                # Categórica (texto/data-como-string): sem binning — cada
                # categoria já É o "bin", prática padrão de WOE categórico
                # (ver docs/literatura/categorizacao.md: binning existe pra
                # discretizar CONTÍNUAS, não se aplica aqui).
                bin_dev = df_dev[coluna]
                bin_teste = df_teste[coluna]

            tabela = ajustar_woe(bin_dev, df_dev["y"])
            nome_woe = f"{base_semantica}_woe"
            woe_dev[nome_woe] = aplicar_woe(bin_dev, tabela)
            woe_teste[nome_woe] = aplicar_woe(bin_teste, tabela)
            iv_por_variavel[coluna] = tabela.iv_total
            classificacao = classificar_iv(tabela.iv_total)
            mensagem = f"  {coluna}: IV={tabela.iv_total:.4f} ({classificacao})"
            fila.put({"tipo": "log", "mensagem": mensagem})

            if gerar_transformacoes_potencia and eh_numerica:
                extras_dev = gerar_transformacoes_fixas(df_dev[coluna], base_semantica)
                extras_teste = gerar_transformacoes_fixas(df_teste[coluna], base_semantica)
                # só mantém transformações válidas (domínio ok) em dev E teste —
                # senão a coluna existiria só de um lado.
                for nome_extra in set(extras_dev) & set(extras_teste):
                    serie_dev, serie_teste = extras_dev[nome_extra], extras_teste[nome_extra]
                    if not (np.isfinite(serie_dev).all() and np.isfinite(serie_teste).all()):
                        continue
                    woe_dev[nome_extra] = serie_dev
                    woe_teste[nome_extra] = serie_teste
                    n_potencia += 1
        except (ValueError, IndexError, TypeError) as e:
            fila.put({"tipo": "log", "mensagem": f"  [pulado] {coluna}: {e}"})

    if n_potencia:
        mensagem_potencia = f"  +{n_potencia} transformações de potência (log/quad/cubo/inversas)"
        fila.put({"tipo": "log", "mensagem": mensagem_potencia})

    return pd.DataFrame(woe_dev), pd.DataFrame(woe_teste), iv_por_variavel


def _construir_e_transformar(
    df_dev: pd.DataFrame,
    df_teste: pd.DataFrame,
    fila: queue.Queue[dict[str, Any]],
    gerar_transformacoes_potencia: bool = True,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, float]]:
    """Composição construção → categorização → transformação, usada pelo
    pipeline "rodar tudo de uma vez" (`rodar_pipeline`). Os módulos também
    são expostos separadamente para inspeção (`rodar_construcao`,
    `rodar_categorizacao_transformacao`), sem persistir nada em disco — cada
    chamada de `/api/pipeline/run` recomputa do zero a partir de `dev.csv`/
    `teste.csv`, então não há cache para ficar desatualizado.
    """
    df_dev, df_teste, _ = _construir(df_dev, df_teste, fila)
    return _categorizar_e_transformar(
        df_dev, df_teste, fila, gerar_transformacoes_potencia=gerar_transformacoes_potencia
    )


def rodar_construcao(dataset: str, pares_customizados: list[ParConstrucao] | None = None) -> dict[str, Any]:
    """Roda só o módulo de construção, pra inspeção isolada (Fase 3 — UI
    modular). Não persiste nada; se não houver razões aplicáveis ao
    dataset nem pares customizados, `colunas_novas` vem vazio.
    """
    df_dev, df_teste = carregar_dataset(dataset)
    fila: queue.Queue[dict[str, Any]] = queue.Queue()
    df_dev, _, colunas_novas = _construir(df_dev, df_teste, fila, pares_customizados=pares_customizados)
    return {
        "colunas_novas": colunas_novas,
        "n_colunas_total": len([c for c in df_dev.columns if c != "y"]),
        "amostra": df_dev.head(5).to_dict(orient="records"),
    }


def rodar_categorizacao_transformacao(
    dataset: str,
    usar_construcao: bool = True,
    pares_customizados: list[ParConstrucao] | None = None,
    gerar_transformacoes_potencia: bool = True,
) -> dict[str, Any]:
    """Roda construção (opcional) + categorização + transformação, pra
    inspeção isolada (Fase 3 — UI modular). Não persiste nada.
    """
    df_dev, df_teste = carregar_dataset(dataset)
    fila: queue.Queue[dict[str, Any]] = queue.Queue()
    if usar_construcao:
        df_dev, df_teste, _ = _construir(df_dev, df_teste, fila, pares_customizados=pares_customizados)
    _, _, iv_por_variavel = _categorizar_e_transformar(
        df_dev, df_teste, fila, gerar_transformacoes_potencia=gerar_transformacoes_potencia
    )
    iv_ordenado = sorted(iv_por_variavel.items(), key=lambda kv: kv[1], reverse=True)
    return {
        "n_variaveis": len(iv_por_variavel),
        "iv": [{"variavel": v, "iv": iv, "classificacao": classificar_iv(iv)} for v, iv in iv_ordenado],
    }


def _tabela_decis(y: pd.Series, prob: np.ndarray, n_faixas: int = 10) -> list[dict[str, Any]]:
    """Tabela de decis (gains/KS table) — padrão em credit scoring pra
    inspecionar visualmente onde o modelo separa evento/não-evento, não só
    o KS/AUC agregados. Ordena por score decrescente (maior risco primeiro),
    divide em `n_faixas` grupos de tamanho ~igual, e acumula % de eventos e
    não-eventos capturados até cada faixa — a maior diferença entre as duas
    curvas acumuladas é o próprio KS.
    """
    n = len(y)
    if n == 0:
        return []
    ordem = np.argsort(-prob)
    y_ordenado = y.to_numpy()[ordem]
    total_eventos = int(y_ordenado.sum())
    total_nao_eventos = n - total_eventos

    tamanho_faixa = max(1, n // n_faixas)
    linhas: list[dict[str, Any]] = []
    eventos_acumulados = 0
    nao_eventos_acumulados = 0
    for i in range(n_faixas):
        inicio = i * tamanho_faixa
        if inicio >= n:
            break
        fim = n if i == n_faixas - 1 else min(n, inicio + tamanho_faixa)
        fatia = y_ordenado[inicio:fim]
        n_fatia = len(fatia)
        eventos = int(fatia.sum())
        eventos_acumulados += eventos
        nao_eventos_acumulados += n_fatia - eventos
        pct_eventos_acum = eventos_acumulados / total_eventos if total_eventos else 0.0
        pct_nao_eventos_acum = nao_eventos_acumulados / total_nao_eventos if total_nao_eventos else 0.0
        linhas.append(
            {
                "faixa": i + 1,
                "n": n_fatia,
                "taxa_evento": eventos / n_fatia if n_fatia else 0.0,
                "pct_eventos_capturados": pct_eventos_acum,
                "pct_nao_eventos_capturados": pct_nao_eventos_acum,
                "ks_acumulado": abs(pct_eventos_acum - pct_nao_eventos_acum),
            }
        )
    return linhas


def rodar_pipeline(
    dataset: str,
    *,
    usar_pipeline_completo: bool = True,
    criterio: str = "teste",
    shadow_probing: bool = False,
    # Nível 1 — flags individuais (regressão da v2 vs. a v1 Streamlit, restaurada).
    forward_simples: bool = True,
    transformacao_simples_nivel1: bool = True,
    backward_simples_nivel1: bool = True,
    min_vars_para_backward: int = 5,
    # Nível 2 / 2.5
    forward_duplo: bool = True,
    forward_triplo: bool = True,
    transformacao_simples_nivel2: bool = True,
    backward_simples_nivel2: bool = True,
    n_best_duplo: int = 5,
    n_best_triplo_1: int = 3,
    n_best_triplo_2: int = 3,
    # Nível 3 — nunca exposto antes na v2; existia no core mas não na API/UI.
    nivel3_ativado: bool = False,
    n_best_backward: int = 2,
    profundidade_maxima_nivel3: int = 2,
    gerar_transformacoes_potencia: bool = True,
    fila: queue.Queue[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Roda o pipeline (opcionalmente construção+categorização+WOE) seguido
    do Pedro_Wise (níveis 1-2.5, ou 1-3 se `nivel3_ativado`), publicando
    progresso em `fila` em tempo real via `CapturadorProgresso`. Retorna o
    resultado final (também colocado na fila como último item, tipo
    "resultado", pelo chamador).
    """
    fila = fila if fila is not None else queue.Queue()
    t0 = time.perf_counter()

    df_dev, df_teste = carregar_dataset(dataset)
    iv_por_variavel: dict[str, float] = {}

    if usar_pipeline_completo:
        df_dev, df_teste, iv_por_variavel = _construir_e_transformar(
            df_dev, df_teste, fila, gerar_transformacoes_potencia=gerar_transformacoes_potencia
        )
    else:
        fila.put({"tipo": "etapa", "mensagem": "Rodando direto nas variáveis originais (sem pipeline)"})

    sufixo_nivel3 = " (com nível 3)" if nivel3_ativado else ""
    fila.put({"tipo": "etapa", "mensagem": f"Treinamento: Pedro_Wise{sufixo_nivel3}"})

    logger_pedro_wise = logging.getLogger("pedro_wise")
    handler = CapturadorProgresso(fila)
    nivel_anterior = logger_pedro_wise.level
    logger_pedro_wise.addHandler(handler)
    logger_pedro_wise.setLevel(logging.INFO)
    try:
        estimator = LogisticGLM()
        metric = KSGaussianMetric(criterio=criterio)  # type: ignore[arg-type]
        modelo_nulo = estimator.fit(df_dev[[]], df_dev["y"])
        score_nulo = metric(modelo_nulo, df_dev[[]], df_dev["y"], df_teste[[]], df_teste["y"])
        estado_inicial = SelectionState(variables=(), model=modelo_nulo, score=score_nulo)

        config1 = Level1Config(
            forward_simples=forward_simples,
            transformacao_simples=transformacao_simples_nivel1,
            backward_simples=backward_simples_nivel1,
            min_vars_para_backward=min_vars_para_backward,
            shadow_probing=ShadowProbingConfig(ativado=shadow_probing, semente=7),
        )
        config2 = Level2Config(
            forward_duplo=forward_duplo,
            forward_triplo=forward_triplo,
            transformacao_simples=transformacao_simples_nivel2,
            backward_simples=backward_simples_nivel2,
            n_best_duplo=n_best_duplo,
            n_best_triplo_1=n_best_triplo_1,
            n_best_triplo_2=n_best_triplo_2,
        )
        if nivel3_ativado:
            config3 = Level3Config(
                ativado=True, n_best_backward=n_best_backward, profundidade_maxima=profundidade_maxima_nivel3
            )
            estado_final, trace = run_pedro_wise_completo(
                estimator, metric, df_dev, df_teste, estado_inicial, config1, config2, config3
            )
        else:
            estado_final, trace = run_pedro_wise(
                estimator, metric, df_dev, df_teste, estado_inicial, config1, config2
            )
    finally:
        logger_pedro_wise.removeHandler(handler)
        logger_pedro_wise.setLevel(nivel_anterior)

    variaveis = list(estado_final.variables)
    metric_teste = KSGaussianMetric(criterio="teste")
    if variaveis:
        ks_teste = metric_teste(
            estado_final.model, df_dev[variaveis], df_dev["y"], df_teste[variaveis], df_teste["y"]
        )
        prob_teste = estado_final.model.predict_proba(df_teste[variaveis])
        auc = float(roc_auc_score(df_teste["y"], prob_teste))
        tabela_decis = _tabela_decis(df_teste["y"], prob_teste)
        # FittedModel (Protocol) só garante variables/predict_proba — genérico
        # de propósito, pra caber estimadores futuros sem coeficiente linear
        # (sklearn/boosting). LogisticGLM (o único estimador hoje) tem
        # coeficientes(); resultado_final.model é sempre um LogisticGLM aqui.
        coeficientes = estado_final.model.coeficientes()  # type: ignore[attr-defined]
        intercepto = coeficientes.get("const", 0.0)
        coeficientes_variaveis = [
            {"variavel": v, "coeficiente": coeficientes.get(v, 0.0)} for v in variaveis
        ]
    else:
        ks_teste = 0.0
        auc = 0.5
        tabela_decis = []
        intercepto = 0.0
        coeficientes_variaveis = []

    iv_ordenado = sorted(iv_por_variavel.items(), key=lambda kv: kv[1], reverse=True)[:10]

    return {
        "tipo": "resultado",
        "variaveis": variaveis,
        "ks_dev": estado_final.score if criterio == "dev" else None,
        "ks_teste": ks_teste,
        "auc": auc,
        "n_eventos": len(trace.eventos),
        "top_iv": [{"variavel": v, "iv": iv} for v, iv in iv_ordenado],
        "tabela_decis": tabela_decis,
        "intercepto": intercepto,
        "coeficientes": coeficientes_variaveis,
        "tempo_segundos": round(time.perf_counter() - t0, 1),
    }
