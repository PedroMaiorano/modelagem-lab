"""Client arXiv — busca metadados via a API pública (Atom/XML), sem chave.

Única fonte da lista que responde XML, não JSON. Ver
docs/referencias/apis-fontes-abertas.md para categorias relevantes e limites.

Uso: python scraping/arxiv_client.py --query 'cat:stat.ML AND all:"variable selection"' --max 10
"""

from __future__ import annotations

import argparse
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import requests

from scraping._common import USER_AGENT, Paper, RateLimiter, escrever_cache, ler_cache

# Titulos podem trazer caracteres fora do cp1252 do console Windows; forca utf-8 na saida.
_reconfigure = getattr(sys.stdout, "reconfigure", None)
if _reconfigure is not None and sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    _reconfigure(encoding="utf-8", errors="replace")

ENDPOINT = "http://export.arxiv.org/api/query"
_NS = {"atom": "http://www.w3.org/2005/Atom"}
_limiter = RateLimiter(intervalo_minimo_s=3.0)


def _texto(elemento: ET.Element, tag: str) -> str:
    return " ".join((elemento.findtext(f"atom:{tag}", default="", namespaces=_NS) or "").split())


def _parsear_entrada(entrada: ET.Element) -> Paper:
    id_completo = entrada.findtext("atom:id", default="", namespaces=_NS) or ""
    arxiv_id = id_completo.rsplit("/", 1)[-1]
    publicado = entrada.findtext("atom:published", default="", namespaces=_NS) or ""
    ano = int(publicado[:4]) if publicado[:4].isdigit() else None
    autores = tuple(
        (a.findtext("atom:name", default="", namespaces=_NS) or "").strip()
        for a in entrada.findall("atom:author", _NS)
    )
    pdf_url = next(
        (link.get("href") for link in entrada.findall("atom:link", _NS) if link.get("title") == "pdf"),
        None,
    )
    return Paper(
        source="arxiv",
        source_id=arxiv_id,
        title=_texto(entrada, "title"),
        authors=autores,
        year=ano,
        abstract=_texto(entrada, "summary") or None,
        url=f"https://arxiv.org/abs/{arxiv_id}",
        oa_pdf_url=pdf_url,
    )


def buscar(query: str, max_results: int = 15) -> list[Paper]:
    """Busca no arXiv. Respeita cache: entradas já vistas não são reparseadas."""
    _limiter.aguardar()
    resp = requests.get(
        ENDPOINT,
        params={
            "search_query": query,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
            "max_results": str(max_results),
        },
        headers={"User-Agent": USER_AGENT},
        timeout=30,
    )
    resp.raise_for_status()
    raiz = ET.fromstring(resp.text)

    papers: list[Paper] = []
    for entrada in raiz.findall("atom:entry", _NS):
        arxiv_id = (entrada.findtext("atom:id", default="", namespaces=_NS) or "").rsplit("/", 1)[-1]
        cacheado = ler_cache("arxiv", arxiv_id) if arxiv_id else None
        if cacheado is not None:
            papers.append(cacheado)
            continue
        paper = _parsear_entrada(entrada)
        escrever_cache(paper)
        papers.append(paper)
    return papers


def main() -> None:
    parser = argparse.ArgumentParser(description="Busca papers no arXiv (fonte aberta, sem chave).")
    parser.add_argument("--query", required=True, help='ex.: cat:stat.ML AND all:"variable selection"')
    parser.add_argument("--max", type=int, default=15, dest="max_results")
    args = parser.parse_args()

    for paper in buscar(args.query, args.max_results):
        print(f"[{paper.year}] {paper.title} — {paper.url}")


if __name__ == "__main__":
    main()
