"""Client Europe PMC — biomédico/risco em saúde, sempre filtrando OPEN_ACCESS:Y.

Uso: python scraping/europepmc_client.py --query "variable selection" --max 10
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import requests

from scraping._common import USER_AGENT, Paper, RateLimiter, escrever_cache, ler_cache

# Titulos podem trazer caracteres fora do cp1252 do console Windows; forca utf-8 na saida.
_reconfigure = getattr(sys.stdout, "reconfigure", None)
if _reconfigure is not None and sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    _reconfigure(encoding="utf-8", errors="replace")

ENDPOINT = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
# Sem limite documentado à parte, mas alinhado ao PubMed E-utilities (3 req/s sem chave).
_limiter = RateLimiter(intervalo_minimo_s=0.4)


def _parsear_item(item: dict[str, Any]) -> Paper:
    autores_str = item.get("authorString", "")
    autores = tuple(a.strip() for a in autores_str.split(",") if a.strip())
    ano_str = item.get("pubYear")
    ano = int(ano_str) if ano_str and ano_str.isdigit() else None
    pmid = item.get("id", "")
    fonte_id = item.get("source", "") + ":" + pmid
    tem_pdf_oa = item.get("isOpenAccess") == "Y" and item.get("fullTextUrlList")
    pdf_url = None
    if tem_pdf_oa:
        urls = item["fullTextUrlList"].get("fullTextUrl", [])
        pdf_url = next((u.get("url") for u in urls if u.get("documentStyle") == "pdf"), None)
    return Paper(
        source="europepmc",
        source_id=fonte_id,
        title=item.get("title", ""),
        authors=autores,
        year=ano,
        abstract=item.get("abstractText"),
        url=f"https://europepmc.org/article/{item.get('source', '')}/{pmid}",
        oa_pdf_url=pdf_url,
    )


def buscar(query: str, max_results: int = 15) -> list[Paper]:
    """Sempre restringe a `OPEN_ACCESS:Y` — nunca retorna itens fechados."""
    _limiter.aguardar()
    query_aberta = f"OPEN_ACCESS:Y AND ({query})"
    resp = requests.get(
        ENDPOINT,
        params={"query": query_aberta, "format": "json", "pageSize": str(max_results)},
        headers={"User-Agent": USER_AGENT},
        timeout=30,
    )
    resp.raise_for_status()
    dados = resp.json()

    papers: list[Paper] = []
    for item in dados.get("resultList", {}).get("result", []):
        pmid = item.get("id")
        if not pmid:
            continue
        fonte_id = item.get("source", "") + ":" + pmid
        cacheado = ler_cache("europepmc", fonte_id)
        if cacheado is not None:
            papers.append(cacheado)
            continue
        paper = _parsear_item(item)
        escrever_cache(paper)
        papers.append(paper)
    return papers


def main() -> None:
    parser = argparse.ArgumentParser(description="Busca artigos abertos no Europe PMC.")
    parser.add_argument("--query", required=True)
    parser.add_argument("--max", type=int, default=15, dest="max_results")
    args = parser.parse_args()

    for paper in buscar(args.query, args.max_results):
        print(f"[{paper.year}] {paper.title} — {paper.url}")


if __name__ == "__main__":
    main()
