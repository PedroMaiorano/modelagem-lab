"""Backend FastAPI do dashboard (pilar interface, v2). Expõe os 4 módulos de
modelagem via API + streaming de progresso em tempo real (SSE) — ver
docs/planos/interface-v2-fastapi-react.md para a decisão de arquitetura.

Uso: python -m uvicorn main:app --reload --port 8000 --app-dir app/backend
(a partir da raiz do repo — `--app-dir` evita depender de `__init__.py`/pacote).
"""

from __future__ import annotations

import asyncio
import json
import queue
import threading
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from logica import listar_datasets, preview_dataset, rodar_pipeline
from pydantic import BaseModel
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


class ConfigPipeline(BaseModel):
    dataset: str
    usar_pipeline_completo: bool = True
    criterio: str = "teste"
    shadow_probing: bool = False
    n_best_duplo: int = 5
    n_best_triplo_1: int = 3
    n_best_triplo_2: int = 3


def _worker(config: ConfigPipeline, fila: queue.Queue[dict[str, Any] | None]) -> None:
    try:
        resultado = rodar_pipeline(
            config.dataset,
            usar_pipeline_completo=config.usar_pipeline_completo,
            criterio=config.criterio,
            shadow_probing=config.shadow_probing,
            n_best_duplo=config.n_best_duplo,
            n_best_triplo_1=config.n_best_triplo_1,
            n_best_triplo_2=config.n_best_triplo_2,
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
