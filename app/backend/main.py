"""Backend FastAPI do dashboard (pilar interface, v2). Expõe os 4 módulos de
modelagem via API + streaming de progresso em tempo real (SSE) — ver
docs/planos/interface-v2-fastapi-react.md para a decisão de arquitetura.

Uso: python -m uvicorn main:app --reload --port 8000 --app-dir app/backend
(a partir da raiz do repo — `--app-dir` evita depender de `__init__.py`/pacote).
"""

from __future__ import annotations

import asyncio
import io
import json
import os
import queue
import threading
from typing import Annotated, Any, Literal

import pandas as pd
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from feature_lab import (
    carregar_base_bruta,
    descobrir_em_tabela,
    info_painel,
    listar_bases,
    listar_paineis,
    rodar_agregacao,
    rodar_direto,
    salvar_painel,
)
from ingestao import (
    calcular_corte_por_percentual,
    carregar_staging,
    detectar_colunas,
    dividir_aleatorio,
    dividir_por_amostra_existente,
    dividir_por_data_oot,
    gravar_dataset_preparado,
    salvar_staging,
    valores_distintos,
)
from logica import (
    ParConstrucao,
    listar_datasets,
    preview_dataset,
    rodar_categorizacao_transformacao,
    rodar_construcao,
    rodar_pipeline,
    rodar_pre_selecao,
)
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

app = FastAPI(title="modelagem-lab API", version="0.1.0")

# Dev local sempre liberado; em produção (Render) o domínio do frontend
# (Vercel) vem de FRONTEND_ORIGINS, separado por vírgula — evita hardcodar
# a URL de deploy no código (ela muda por ambiente/preview).
_origins_extra = [o.strip() for o in os.environ.get("FRONTEND_ORIGINS", "").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", *_origins_extra],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def rota_saude() -> dict[str, str]:
    """Health check pra plataformas de deploy (Render faz GET / por padrão)."""
    return {"status": "ok", "servico": "modelagem-lab API"}


@app.get("/api/datasets")
def rota_listar_datasets() -> list[str]:
    return listar_datasets()


@app.get("/api/datasets/{nome}/preview")
def rota_preview_dataset(nome: str) -> dict[str, Any]:
    if nome not in listar_datasets():
        raise HTTPException(status_code=404, detail=f"Dataset '{nome}' não encontrado")
    return preview_dataset(nome)


# ---------------------------------------------------------------------------
# Módulos isolados (Fase 3): construção e categorização+transformação podem
# ser rodados e inspecionados separadamente do treinamento, sem persistir
# nada em disco — cada chamada recomputa a partir de dev.csv/teste.csv.
# O treinamento continua em /api/pipeline/run (já é "opcional usar
# construção+categorização+WOE" via usar_pipeline_completo).
# ---------------------------------------------------------------------------


class ParConstrucaoAPI(BaseModel):
    numerador: str
    denominador: str
    nome: str | None = None
    operacao: Literal["razao", "diferenca"] = "razao"


def _par_construcao(p: ParConstrucaoAPI) -> ParConstrucao:
    simbolo = "sobre" if p.operacao == "razao" else "menos"
    nome = p.nome or f"{p.numerador}_{simbolo}_{p.denominador}"
    return ParConstrucao(p.numerador, p.denominador, nome, p.operacao)


class ConfigConstrucao(BaseModel):
    dataset: str
    pares_customizados: list[ParConstrucaoAPI] = []


@app.post("/api/modulo/construcao")
def rota_rodar_construcao(config: ConfigConstrucao) -> dict[str, Any]:
    if config.dataset not in listar_datasets():
        raise HTTPException(status_code=404, detail=f"Dataset '{config.dataset}' não encontrado")
    pares = [_par_construcao(p) for p in config.pares_customizados]
    return rodar_construcao(config.dataset, pares_customizados=pares)


class ConfigCategorizacaoTransformacao(BaseModel):
    dataset: str
    usar_construcao: bool = True
    pares_customizados: list[ParConstrucaoAPI] = []
    gerar_transformacoes_potencia: bool = True
    gerar_bin_ordinal: bool = True


@app.post("/api/modulo/categorizacao-transformacao")
def rota_rodar_categorizacao_transformacao(config: ConfigCategorizacaoTransformacao) -> dict[str, Any]:
    if config.dataset not in listar_datasets():
        raise HTTPException(status_code=404, detail=f"Dataset '{config.dataset}' não encontrado")
    pares = [_par_construcao(p) for p in config.pares_customizados]
    return rodar_categorizacao_transformacao(
        config.dataset,
        usar_construcao=config.usar_construcao,
        pares_customizados=pares,
        gerar_transformacoes_potencia=config.gerar_transformacoes_potencia,
        gerar_bin_ordinal=config.gerar_bin_ordinal,
    )


class ConfigPreSelecao(BaseModel):
    dataset: str
    usar_construcao: bool = True
    pares_customizados: list[ParConstrucaoAPI] = []
    gerar_transformacoes_potencia: bool = True
    gerar_bin_ordinal: bool = True
    limiar_variancia: float | None = 1e-6
    limiar_iv: float | None = 0.02
    limiar_correlacao: float | None = 0.9


@app.post("/api/modulo/pre-selecao")
def rota_rodar_pre_selecao(config: ConfigPreSelecao) -> dict[str, Any]:
    if config.dataset not in listar_datasets():
        raise HTTPException(status_code=404, detail=f"Dataset '{config.dataset}' não encontrado")
    pares = [_par_construcao(p) for p in config.pares_customizados]
    return rodar_pre_selecao(
        config.dataset,
        usar_construcao=config.usar_construcao,
        pares_customizados=pares,
        gerar_transformacoes_potencia=config.gerar_transformacoes_potencia,
        gerar_bin_ordinal=config.gerar_bin_ordinal,
        limiar_variancia=config.limiar_variancia,
        limiar_iv=config.limiar_iv,
        limiar_correlacao=config.limiar_correlacao,
    )


# ---------------------------------------------------------------------------
# Ingestão: upload de CSV, detecção de colunas, split (amostra existente /
# OOT por data / aleatório). Ver app/backend/ingestao.py.
# ---------------------------------------------------------------------------


@app.post("/api/dataset/upload")
async def rota_upload_dataset(arquivo: Annotated[UploadFile, File()]) -> dict[str, Any]:
    conteudo = await arquivo.read()
    try:
        df = pd.read_csv(io.BytesIO(conteudo))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Não consegui ler o CSV: {e}") from e
    if df.empty:
        raise HTTPException(status_code=400, detail="Arquivo vazio")

    upload_id = salvar_staging(df)
    colunas = detectar_colunas(df)
    return {
        "upload_id": upload_id,
        "n_linhas": len(df),
        "colunas": [
            {
                "nome": c.nome,
                "tipo": c.tipo,
                "formato_data": c.formato_data,
                "n_distintos": c.n_distintos,
                "exemplos": [str(v) for v in c.exemplos],
            }
            for c in colunas
        ],
    }


@app.get("/api/dataset/{upload_id}/coluna/{coluna}/valores")
def rota_valores_distintos(upload_id: str, coluna: str) -> list[dict[str, Any]]:
    try:
        return valores_distintos(upload_id, coluna)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except KeyError as e:
        raise HTTPException(status_code=400, detail=f"Coluna '{coluna}' não encontrada") from e


@app.get("/api/dataset/sugerir-corte")
def rota_sugerir_corte(
    upload_id: str, coluna: str, formato: str, proporcao_teste: float = 0.3
) -> dict[str, str]:
    """Corte de data sugerido pra "os N% mais recentes viram OOT" — o
    frontend usa isso como valor inicial de um campo editável, não aplica
    automaticamente.
    """
    try:
        df = carregar_staging(upload_id)
        corte = calcular_corte_por_percentual(df, coluna, formato, proporcao_teste)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {"corte": corte}


class ConfigSplitAmostra(BaseModel):
    modo: Literal["amostra"]
    coluna: str
    valores_dev: list[str]
    valores_teste: list[str]


class ConfigSplitOOT(BaseModel):
    modo: Literal["oot"]
    coluna: str
    formato: str
    corte: str


class ConfigSplitAleatorio(BaseModel):
    modo: Literal["aleatorio"]
    proporcao_teste: float = 0.3
    semente: int = 42


class ConfigPreparar(BaseModel):
    upload_id: str
    nome_dataset: str
    coluna_resposta: str
    split: ConfigSplitAmostra | ConfigSplitOOT | ConfigSplitAleatorio = Field(discriminator="modo")


@app.post("/api/dataset/preparar")
def rota_preparar_dataset(config: ConfigPreparar) -> dict[str, Any]:
    try:
        df = carregar_staging(config.upload_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    if config.coluna_resposta not in df.columns:
        raise HTTPException(status_code=400, detail=f"Coluna resposta '{config.coluna_resposta}' não existe")
    df = df.rename(columns={config.coluna_resposta: "y"})

    split = config.split
    if split.modo == "amostra":
        df_dev, df_teste = dividir_por_amostra_existente(
            df, split.coluna, split.valores_dev, split.valores_teste
        )
    elif split.modo == "oot":
        df_dev, df_teste = dividir_por_data_oot(df, split.coluna, split.formato, split.corte)
    else:
        df_dev, df_teste = dividir_aleatorio(df, split.proporcao_teste, split.semente)

    if len(df_dev) == 0 or len(df_teste) == 0:
        raise HTTPException(
            status_code=400, detail="Split resultou em dev ou teste vazio — ajuste a configuração"
        )

    gravar_dataset_preparado(config.nome_dataset, df_dev, df_teste)
    return {"nome_dataset": config.nome_dataset, "n_dev": len(df_dev), "n_teste": len(df_teste)}


class ConfigPipeline(BaseModel):
    dataset: str
    usar_pipeline_completo: bool = True
    criterio: str = "teste"
    shadow_probing: bool = False
    # Nível 1
    forward_simples: bool = True
    transformacao_simples_nivel1: bool = True
    backward_simples_nivel1: bool = True
    min_vars_para_backward: int = 5
    # Nível 2 / 2.5
    forward_duplo: bool = True
    forward_triplo: bool = True
    transformacao_simples_nivel2: bool = True
    backward_simples_nivel2: bool = True
    n_best_duplo: int = 5
    n_best_triplo_1: int = 3
    n_best_triplo_2: int = 3
    # Nível 3
    nivel3_ativado: bool = False
    n_best_backward: int = 2
    profundidade_maxima_nivel3: int = 2
    gerar_transformacoes_potencia: bool = True
    gerar_bin_ordinal: bool = True
    # Pré-seleção (módulo 3) — opt-in, aplicada antes do treinamento
    usar_pre_selecao: bool = False
    limiar_variancia: float | None = 1e-6
    limiar_iv: float | None = 0.02
    limiar_correlacao: float | None = 0.9
    # Restrição de significância — None desliga (padrão)
    p_valor_maximo: float | None = None
    comparar_sem_p_valor: bool = True


def _worker(config: ConfigPipeline, fila: queue.Queue[dict[str, Any] | None]) -> None:
    try:
        resultado = rodar_pipeline(
            config.dataset,
            usar_pipeline_completo=config.usar_pipeline_completo,
            criterio=config.criterio,
            shadow_probing=config.shadow_probing,
            forward_simples=config.forward_simples,
            transformacao_simples_nivel1=config.transformacao_simples_nivel1,
            backward_simples_nivel1=config.backward_simples_nivel1,
            min_vars_para_backward=config.min_vars_para_backward,
            forward_duplo=config.forward_duplo,
            forward_triplo=config.forward_triplo,
            transformacao_simples_nivel2=config.transformacao_simples_nivel2,
            backward_simples_nivel2=config.backward_simples_nivel2,
            n_best_duplo=config.n_best_duplo,
            n_best_triplo_1=config.n_best_triplo_1,
            n_best_triplo_2=config.n_best_triplo_2,
            nivel3_ativado=config.nivel3_ativado,
            n_best_backward=config.n_best_backward,
            profundidade_maxima_nivel3=config.profundidade_maxima_nivel3,
            gerar_transformacoes_potencia=config.gerar_transformacoes_potencia,
            gerar_bin_ordinal=config.gerar_bin_ordinal,
            usar_pre_selecao=config.usar_pre_selecao,
            limiar_variancia=config.limiar_variancia,
            limiar_iv=config.limiar_iv,
            limiar_correlacao=config.limiar_correlacao,
            p_valor_maximo=config.p_valor_maximo,
            comparar_sem_p_valor=config.comparar_sem_p_valor,
            fila=fila,  # type: ignore[arg-type]
        )
        fila.put(resultado)
    except Exception as e:  # noqa: BLE001 — reportado ao cliente via SSE, não deve derrubar o worker
        fila.put({"tipo": "erro", "mensagem": str(e)})
    finally:
        fila.put(None)  # sentinela: fim do stream


@app.post("/api/pipeline/run")
async def rota_rodar_pipeline(config: ConfigPipeline) -> EventSourceResponse:
    if config.dataset not in listar_datasets():
        raise HTTPException(status_code=404, detail=f"Dataset '{config.dataset}' não encontrado")

    fila: queue.Queue[dict[str, Any] | None] = queue.Queue()
    thread = threading.Thread(target=_worker, args=(config, fila), daemon=True)
    thread.start()

    async def gerador():
        loop = asyncio.get_event_loop()
        while True:
            item = await loop.run_in_executor(None, fila.get)
            if item is None:
                break
            yield {"event": "progresso", "data": json.dumps(item, ensure_ascii=False)}

    return EventSourceResponse(gerador())


# ---------------------------------------------------------------------------
# Feature-lab (esferas 1/2, experimental) -- ver app/backend/feature_lab.py
# ---------------------------------------------------------------------------


@app.get("/api/feature-lab/bases")
def rota_listar_bases() -> list[dict[str, str]]:
    """Toda base disponível (painel ou já-flat), com o tipo marcado -- um
    seletor só na interface, que decide na hora se mostra a esfera 1."""
    return listar_bases()


@app.get("/api/feature-lab/paineis")
def rota_listar_paineis() -> list[str]:
    return listar_paineis()


@app.get("/api/feature-lab/paineis/{nome}/info")
def rota_info_painel(nome: str, coluna_y: str = "y") -> dict[str, Any]:
    try:
        return info_painel(nome, coluna_y)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@app.get("/api/feature-lab/base-bruta")
def rota_carregar_base_bruta(
    base: str, tipo: Literal["painel", "flat"], coluna_y: str = "y"
) -> dict[str, Any]:
    """Carrega a base sem passar pela esfera 1 -- pro toggle de agregação
    desligado, mesmo numa base tipo painel."""
    try:
        return carregar_base_bruta(base, tipo, coluna_y)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.post("/api/feature-lab/paineis/upload")
async def rota_upload_painel(
    arquivo: Annotated[UploadFile, File()], nome: Annotated[str, Form()]
) -> dict[str, Any]:
    conteudo = await arquivo.read()
    try:
        df = pd.read_csv(io.BytesIO(conteudo))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Não consegui ler o CSV: {e}") from e
    try:
        return salvar_painel(nome, df)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


class ConfigAgregacao(BaseModel):
    base: str
    tipo: Literal["painel", "flat"]
    chave: str
    coluna_tempo: str
    colunas_valor: list[str]
    janelas: list[int] = [3]
    coluna_y: str = "y"


@app.post("/api/feature-lab/agregacao")
def rota_rodar_agregacao(config: ConfigAgregacao) -> dict[str, Any]:
    """Esfera 1 sozinha -- devolve a tabela resultante pra interface guardar
    e mandar de volta em /descobrir (etapa separada, clique separado)."""
    try:
        return rodar_agregacao(
            base=config.base,
            tipo=config.tipo,
            chave=config.chave,
            coluna_tempo=config.coluna_tempo,
            colunas_valor=config.colunas_valor,
            janelas=config.janelas,
            coluna_y=config.coluna_y,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


class ConfigDescobrir(BaseModel):
    tabela: list[dict[str, Any]]
    colunas_x: list[str]
    profundidade_maxima: int = 2
    n_arvores: int = 60
    min_suporte: float = 0.02
    max_suporte: float = 0.5
    max_regras: int = 10
    permitir_cruzamento_entre_bases: bool = True
    coluna_y: str = "y"
    proporcao_variaveis_por_split: float | None = None
    metodo_split: Literal["aleatorio", "coluna"] = "aleatorio"
    coluna_split: str | None = None
    valores_dev: list[str] | None = None
    valores_teste: list[str] | None = None


@app.post("/api/feature-lab/descobrir")
def rota_descobrir_em_tabela(config: ConfigDescobrir) -> dict[str, Any]:
    """Esfera 2 sozinha, sobre a tabela que a esfera 1 já produziu (etapa
    separada da agregação -- clique separado na interface)."""
    try:
        return descobrir_em_tabela(
            registros=config.tabela,
            colunas_x=config.colunas_x,
            profundidade_maxima=config.profundidade_maxima,
            n_arvores=config.n_arvores,
            min_suporte=config.min_suporte,
            max_suporte=config.max_suporte,
            max_regras=config.max_regras,
            permitir_cruzamento_entre_bases=config.permitir_cruzamento_entre_bases,
            coluna_y=config.coluna_y,
            proporcao_variaveis_por_split=config.proporcao_variaveis_por_split,
            metodo_split=config.metodo_split,
            coluna_split=config.coluna_split,
            valores_dev=config.valores_dev,
            valores_teste=config.valores_teste,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


class ConfigDireto(BaseModel):
    dataset: str
    colunas_x: list[str]
    profundidade_maxima: int = 2
    n_arvores: int = 60
    min_suporte: float = 0.02
    max_suporte: float = 0.5
    max_regras: int = 10
    permitir_cruzamento_entre_bases: bool = True
    coluna_y: str = "y"
    proporcao_variaveis_por_split: float | None = None


@app.post("/api/feature-lab/direto")
def rota_rodar_direto(config: ConfigDireto) -> dict[str, Any]:
    if config.dataset not in listar_datasets():
        raise HTTPException(status_code=404, detail=f"Dataset '{config.dataset}' não encontrado")
    try:
        return rodar_direto(
            dataset=config.dataset,
            colunas_x=config.colunas_x,
            profundidade_maxima=config.profundidade_maxima,
            n_arvores=config.n_arvores,
            min_suporte=config.min_suporte,
            max_suporte=config.max_suporte,
            max_regras=config.max_regras,
            permitir_cruzamento_entre_bases=config.permitir_cruzamento_entre_bases,
            coluna_y=config.coluna_y,
            proporcao_variaveis_por_split=config.proporcao_variaveis_por_split,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
