"""Client CrossRef — metadados por DOI, sem chave, `mailto` para o polite pool.

Uso: python scraping/crossref_client.py --query "elastic net selection" --max 10
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import requests

from scraping._common import CONTATO, USER_AGENT, Paper, RateLimiter, escrever_cache, ler_cache

# Titulos podem trazer caracteres fora do cp1252 do console Windows; forca utf-8 na saida.
_reconfigure = getattr(sys.stdout, "reconfigure", None)
if _reconfigure is not None and sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    _reconfigure(encoding="utf-8", errors="replace")

ENDPOINT = "https://api.crossref.org/works"
_limiter = RateLimiter(intervalo_minimo_s=1.0)


def _parsear_item(item: dict[str, Any]) -> Paper:
    autores = tuple(
        " ".join(filter(None, [a.get("given"), a.get("family")])) for a in item.get("author") or []
    )
    partes_data = (item.get("published") or {}).get("date-parts") or [[None]]
    ano = partes_data[0][0] if partes_data and partes_data[0] else None
    doi = item.get("DOI", "")
    return Paper(
        source="crossref",
        source_id=doi,
        title=" ".join(item.get("title") or []),
        authors=autores,
        year=ano,
        abstract=item.get("abstract"),
        url=item.get("URL") or f"https://doi.org/{doi}",
        oa_pdf_url=None,  # CrossRef não confirma OA de forma confiável — deixar para OpenAlex/Unpaywall
    )


def buscar(query: str, max_results: int = 15, apenas_com_abstract: bool = True) -> list[Paper]:
    _limiter.aguardar()
    params: dict[str, str] = {"query": query, "rows": str(max_results), "mailto": CONTATO}
    if apenas_com_abstract:
        params["filter"] = "has-abstract:true"
    resp = requests.get(ENDPOINT, params=params, headers={"User-Agent": USER_AGENT}, timeout=30)
    resp.raise_for_status()
    dados = resp.json()

    papers: list[Paper] = []
    for item in dados.get("message", {}).get("items", []):
        doi = item.get("DOI")
        if not doi:
            continue
        cacheado = ler_cache("crossref", doi)
        if cacheado is not None:
            papers.append(cacheado)
            continue
        paper = _parsear_item(item)
        escrever_cache(paper)
        papers.append(paper)
    return papers


def main() -> None:
    parser = argparse.ArgumentParser(description="Busca works no CrossRef (fonte aberta).")
    parser.add_argument("--query", required=True)
    parser.add_argument("--max", type=int, default=15, dest="max_results")
    args = parser.parse_args()

    for paper in buscar(args.query, args.max_results):
        print(f"[{paper.year}] {paper.title} — {paper.url}")


if __name__ == "__main__":
    main()
