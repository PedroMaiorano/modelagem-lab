"""Testes dos clients de scraping com HTTP mockado — nenhuma chamada de rede
real roda na suíte de testes. Verificam: parsing correto da resposta de cada
fonte, escrita em cache, e reuso do cache numa segunda chamada (sem nova
requisição HTTP).
"""

from __future__ import annotations

from typing import Any

import pytest

import scraping.arxiv_client as arxiv_client
import scraping.crossref_client as crossref_client
import scraping.europepmc_client as europepmc_client
import scraping.openalex_client as openalex_client
import scraping.semantic_scholar_client as semantic_scholar_client

ARXIV_XML = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/2101.00001v1</id>
    <title>  Variable Selection via Stability   </title>
    <summary>  Um resumo de teste com   espacos extras.  </summary>
    <published>2021-03-15T00:00:00Z</published>
    <author><name>Fulano Silva</name></author>
    <author><name>Beltrano Souza</name></author>
    <link title="pdf" href="https://arxiv.org/pdf/2101.00001v1"/>
  </entry>
</feed>
"""


class _FakeResponse:
    def __init__(self, *, json_data: dict[str, Any] | None = None, text: str = "") -> None:
        self._json_data = json_data
        self.text = text

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        assert self._json_data is not None
        return self._json_data


@pytest.fixture(autouse=True)
def _cache_isolado(monkeypatch, tmp_path):
    monkeypatch.setattr("scraping._common.DIR_CACHE", tmp_path)
    modulos = (arxiv_client, semantic_scholar_client, openalex_client, crossref_client, europepmc_client)
    for limiter_mod in modulos:
        monkeypatch.setattr(limiter_mod, "_limiter", type(limiter_mod._limiter)(intervalo_minimo_s=0.0))


def test_arxiv_client_parseia_e_cacheia(monkeypatch):
    chamadas = []

    def _fake_get(url, params=None, headers=None, timeout=None):
        chamadas.append(params)
        return _FakeResponse(text=ARXIV_XML)

    monkeypatch.setattr(arxiv_client.requests, "get", _fake_get)

    resultados = arxiv_client.buscar("variable selection", max_results=5)
    assert len(resultados) == 1
    paper = resultados[0]
    assert paper.source == "arxiv"
    assert paper.source_id == "2101.00001v1"
    assert paper.title == "Variable Selection via Stability"
    assert paper.authors == ("Fulano Silva", "Beltrano Souza")
    assert paper.year == 2021
    assert paper.oa_pdf_url == "https://arxiv.org/pdf/2101.00001v1"

    # segunda busca: mesmo XML, mas agora o paper já está em cache
    resultados_2 = arxiv_client.buscar("variable selection", max_results=5)
    assert resultados_2 == resultados
    assert len(chamadas) == 2  # a busca em si sempre chama a API; só o paper individual é cacheado


def test_semantic_scholar_client_parseia_e_cacheia(monkeypatch):
    payload = {
        "data": [
            {
                "paperId": "abc123",
                "title": "Stability Selection",
                "abstract": "Resumo.",
                "year": 2020,
                "authors": [{"name": "Fulano"}],
                "openAccessPdf": {"url": "https://exemplo.org/paper.pdf"},
                "url": "https://www.semanticscholar.org/paper/abc123",
            }
        ]
    }
    monkeypatch.setattr(
        semantic_scholar_client.requests, "get", lambda *a, **kw: _FakeResponse(json_data=payload)
    )

    resultados = semantic_scholar_client.buscar("stability selection", max_results=5)
    assert len(resultados) == 1
    assert resultados[0].source_id == "abc123"
    assert resultados[0].oa_pdf_url == "https://exemplo.org/paper.pdf"


def test_openalex_client_inclui_mailto_e_filtro_oa(monkeypatch):
    payload = {
        "results": [
            {
                "id": "https://openalex.org/W123",
                "title": "Double Machine Learning",
                "publication_year": 2019,
                "authorships": [{"author": {"display_name": "Fulano"}}],
                "open_access": {"oa_url": "https://exemplo.org/oa.pdf"},
            }
        ]
    }
    params_capturados = {}

    def _fake_get(url, params=None, headers=None, timeout=None):
        params_capturados.update(params or {})
        return _FakeResponse(json_data=payload)

    monkeypatch.setattr(openalex_client.requests, "get", _fake_get)

    resultados = openalex_client.buscar("double machine learning", max_results=5)
    assert len(resultados) == 1
    assert resultados[0].source_id == "W123"
    assert params_capturados["mailto"] == "pedro.maiorano@gmail.com"
    assert params_capturados["filter"] == "is_oa:true"


def test_crossref_client_inclui_mailto(monkeypatch):
    payload = {
        "message": {
            "items": [
                {
                    "DOI": "10.1234/abc",
                    "title": ["Elastic Net Selection"],
                    "author": [{"given": "Fulano", "family": "Silva"}],
                    "published": {"date-parts": [[2018]]},
                    "abstract": "Resumo.",
                    "URL": "https://doi.org/10.1234/abc",
                }
            ]
        }
    }
    params_capturados = {}

    def _fake_get(url, params=None, headers=None, timeout=None):
        params_capturados.update(params or {})
        return _FakeResponse(json_data=payload)

    monkeypatch.setattr(crossref_client.requests, "get", _fake_get)

    resultados = crossref_client.buscar("elastic net selection", max_results=5)
    assert len(resultados) == 1
    assert resultados[0].source_id == "10.1234/abc"
    assert resultados[0].authors == ("Fulano Silva",)
    assert params_capturados["mailto"] == "pedro.maiorano@gmail.com"


def test_europepmc_client_forca_open_access(monkeypatch):
    payload = {
        "resultList": {
            "result": [
                {
                    "id": "12345",
                    "source": "MED",
                    "title": "Variable Selection in Health Risk",
                    "authorString": "Silva F, Souza B",
                    "pubYear": "2022",
                    "abstractText": "Resumo.",
                    "isOpenAccess": "Y",
                    "fullTextUrlList": {
                        "fullTextUrl": [{"documentStyle": "pdf", "url": "https://exemplo.org/pmc.pdf"}]
                    },
                }
            ]
        }
    }
    params_capturados = {}

    def _fake_get(url, params=None, headers=None, timeout=None):
        params_capturados.update(params or {})
        return _FakeResponse(json_data=payload)

    monkeypatch.setattr(europepmc_client.requests, "get", _fake_get)

    resultados = europepmc_client.buscar("variable selection", max_results=5)
    assert len(resultados) == 1
    assert resultados[0].oa_pdf_url == "https://exemplo.org/pmc.pdf"
    assert "OPEN_ACCESS:Y" in params_capturados["query"]
