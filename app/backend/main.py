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
import queue
import threading
from typing import Annotated, Any, Literal

import pandas as pd
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
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
    listar_datasets,
    preview_dataset,
    rodar_categorizacao_transformacao,
    rodar_construcao,
    rodar_pipeline,
)
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

app = FastAPI(title="modelagem-lab API", version="0.1.0")

# Dev local: frontend Next.js roda em outra porta (3000) — precisa de CORS.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


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


@app.post("/api/modulo/construcao")
def rota_rodar_construcao(dataset: str) -> dict[str, Any]:
    if dataset not in listar_datasets():
        raise HTTPException(status_code=404, detail=f"Dataset '{dataset}' não encontrado")
    return rodar_construcao(dataset)


@app.post("/api/modulo/categorizacao-transformacao")
def rota_rodar_categorizacao_transformacao(dataset: str, usar_construcao: bool = True) -> dict[str, Any]:
    if dataset not in listar_datasets():
        raise HTTPException(status_code=404, detail=f"Dataset '{dataset}' não encontrado")
    return rodar_categorizacao_transformacao(dataset, usar_construcao=usar_construcao)


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
