"""Utilitários compartilhados pelos clients de scraping: tipo `Paper` comum,
cache imutável de metadados em `data/papers/` (chave `fonte_id`, nunca
re-baixado) e um rate limiter simples por fonte.

Ver docs/referencias/apis-fontes-abertas.md para os limites e regras de cada
fonte. Regra inegociável (CLAUDE.md): só fontes 100% abertas, nunca paywall
— nenhum client aqui baixa PDF de fonte fechada.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path

DIR_CACHE = Path(__file__).resolve().parent.parent / "data" / "papers"
CONTATO = "pedro.maiorano@gmail.com"
USER_AGENT = f"modelagem-lab-literature-scout/0.1 (mailto:{CONTATO})"


@dataclass(frozen=True)
class Paper:
    """Metadados mínimos e comuns entre fontes. `oa_pdf_url` só é preenchido
    quando a própria fonte confirma acesso aberto ao PDF — nunca inferido.
    """

    source: str
    source_id: str
    title: str
    authors: tuple[str, ...]
    year: int | None
    abstract: str | None
    url: str
    oa_pdf_url: str | None = None


def caminho_cache(source: str, source_id: str) -> Path:
    id_seguro = source_id.replace("/", "_").replace(":", "_").replace(" ", "_")
    return DIR_CACHE / f"{source}_{id_seguro}.json"


def ler_cache(source: str, source_id: str) -> Paper | None:
    """`None` se não estiver em cache. Nunca sobrescreva um Paper já cacheado
    com dados de uma busca diferente — o cache é a fonte de verdade local.
    """
    caminho = caminho_cache(source, source_id)
    if not caminho.exists():
        return None
    dados = json.loads(caminho.read_text(encoding="utf-8"))
    dados["authors"] = tuple(dados["authors"])
    return Paper(**dados)


def escrever_cache(paper: Paper) -> Path:
    DIR_CACHE.mkdir(parents=True, exist_ok=True)
    caminho = caminho_cache(paper.source, paper.source_id)
    caminho.write_text(json.dumps(asdict(paper), ensure_ascii=False, indent=2), encoding="utf-8")
    return caminho


class RateLimiter:
    """Espera o intervalo mínimo entre chamadas sucessivas à mesma fonte —
    um limiter por client (instanciado no módulo), não compartilhado entre fontes.
    """

    def __init__(self, intervalo_minimo_s: float) -> None:
        self._intervalo = intervalo_minimo_s
        self._ultima_chamada: float | None = None

    def aguardar(self) -> None:
        agora = time.monotonic()
        if self._ultima_chamada is not None:
            faltante = self._intervalo - (agora - self._ultima_chamada)
            if faltante > 0:
                time.sleep(faltante)
        self._ultima_chamada = time.monotonic()
