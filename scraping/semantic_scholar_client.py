"""Client Semantic Scholar Graph API — busca por texto, sem chave (100 req/5min).

Uso: python scraping/semantic_scholar_client.py --query "stability selection" --max 10
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import requests

from scraping._common import USER_AGENT, Paper, RateLimiter, escrever_cache, ler_cache

ENDPOINT = "https://api.semanticscholar.org/graph/v1/paper/search"
_CAMPOS = "title,abstract,year,authors,tldr,openAccessPdf,url"
# 100 req / 5 min sem chave => 1 a cada 3s é seguro (ver docs/referencias/apis-fontes-abertas.md).
_limiter = RateLimiter(intervalo_minimo_s=3.0)


def _parsear_item(item: dict[str, Any]) -> Paper:
    autores = tuple(a.get("name", "") for a in item.get("authors") or [])
    oa_pdf = item.get("openAccessPdf") or {}
    tldr = (item.get("tldr") or {}).get("text")
    abstract = item.get("abstract") or tldr
    return Paper(
        source="semantic_scholar",
        source_id=item["paperId"],
        title=item.get("title", ""),
        authors=autores,
        year=item.get("year"),
        abstract=abstract,
        url=item.get("url") or f"https://www.semanticscholar.org/paper/{item['paperId']}",
        oa_pdf_url=oa_pdf.get("url"),
    )


def buscar(query: str, max_results: int = 15) -> list[Paper]:
    _limiter.aguardar()
    resp = requests.get(
        ENDPOINT,
        params={"query": query, "fields": _CAMPOS, "limit": str(max_results)},
        headers={"User-Agent": USER_AGENT},
        timeout=30,
    )
    resp.raise_for_status()
    dados = resp.json()

    papers: list[Paper] = []
    for item in dados.get("data", []):
        paper_id = item.get("paperId")
        if not paper_id:
            continue
        cacheado = ler_cache("semantic_scholar", paper_id)
        if cacheado is not None:
            papers.append(cacheado)
            continue
        paper = _parsear_item(item)
        escrever_cache(paper)
        papers.append(paper)
    return papers


def main() -> None:
    parser = argparse.ArgumentParser(description="Busca papers no Semantic Scholar (fonte aberta).")
    parser.add_argument("--query", required=True)
    parser.add_argument("--max", type=int, default=15, dest="max_results")
    args = parser.parse_args()

    for paper in buscar(args.query, args.max_results):
        print(f"[{paper.year}] {paper.title} — {paper.url}")


if __name__ == "__main__":
    main()
