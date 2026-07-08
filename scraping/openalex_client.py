"""Client OpenAlex — cobertura ampla, sem chave, `mailto` para o polite pool.

Uso: python scraping/openalex_client.py --query "double machine learning" --max 10
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import requests

from scraping._common import CONTATO, USER_AGENT, Paper, RateLimiter, escrever_cache, ler_cache

ENDPOINT = "https://api.openalex.org/works"
# Sem limite rígido, mas polite: ~1 req/s evita qualquer throttling implícito.
_limiter = RateLimiter(intervalo_minimo_s=1.0)


def _parsear_item(item: dict[str, Any]) -> Paper:
    autores = tuple(
        (a.get("author") or {}).get("display_name", "") for a in item.get("authorships") or []
    )
    ano = item.get("publication_year")
    oa = item.get("open_access") or {}
    return Paper(
        source="openalex",
        source_id=item["id"].rsplit("/", 1)[-1],
        title=item.get("title") or item.get("display_name") or "",
        authors=autores,
        year=ano,
        abstract=None,  # OpenAlex expõe abstract_inverted_index, não texto corrido — fora do escopo v1
        url=item.get("id", ""),
        oa_pdf_url=oa.get("oa_url"),
    )


def buscar(query: str, max_results: int = 15, apenas_acesso_aberto: bool = True) -> list[Paper]:
    _limiter.aguardar()
    params: dict[str, str] = {"search": query, "per-page": str(max_results), "mailto": CONTATO}
    if apenas_acesso_aberto:
        params["filter"] = "is_oa:true"
    resp = requests.get(ENDPOINT, params=params, headers={"User-Agent": USER_AGENT}, timeout=30)
    resp.raise_for_status()
    dados = resp.json()

    papers: list[Paper] = []
    for item in dados.get("results", []):
        openalex_id = item.get("id", "").rsplit("/", 1)[-1]
        if not openalex_id:
            continue
        cacheado = ler_cache("openalex", openalex_id)
        if cacheado is not None:
            papers.append(cacheado)
            continue
        paper = _parsear_item(item)
        escrever_cache(paper)
        papers.append(paper)
    return papers


def main() -> None:
    parser = argparse.ArgumentParser(description="Busca works no OpenAlex (fonte aberta).")
    parser.add_argument("--query", required=True)
    parser.add_argument("--max", type=int, default=15, dest="max_results")
    parser.add_argument("--incluir-fechados", action="store_true", help="não filtrar is_oa:true")
    args = parser.parse_args()

    for paper in buscar(args.query, args.max_results, apenas_acesso_aberto=not args.incluir_fechados):
        print(f"[{paper.year}] {paper.title} — {paper.url}")


if __name__ == "__main__":
    main()
