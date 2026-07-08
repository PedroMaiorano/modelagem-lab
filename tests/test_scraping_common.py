"""Testes do cache imutável e do rate limiter compartilhados pelos clients."""

from __future__ import annotations

import time

from scraping._common import Paper, RateLimiter, caminho_cache, escrever_cache, ler_cache


def test_cache_roundtrip(monkeypatch, tmp_path):
    monkeypatch.setattr("scraping._common.DIR_CACHE", tmp_path)

    paper = Paper(
        source="arxiv",
        source_id="2101.00001",
        title="Um paper de teste",
        authors=("Fulano", "Beltrano"),
        year=2021,
        abstract="Resumo curto.",
        url="https://arxiv.org/abs/2101.00001",
        oa_pdf_url="https://arxiv.org/pdf/2101.00001",
    )
    escrever_cache(paper)

    lido = ler_cache("arxiv", "2101.00001")
    assert lido == paper


def test_ler_cache_ausente_retorna_none(monkeypatch, tmp_path):
    monkeypatch.setattr("scraping._common.DIR_CACHE", tmp_path)
    assert ler_cache("arxiv", "inexistente") is None


def test_caminho_cache_sanitiza_ids_com_barra():
    caminho = caminho_cache("crossref", "10.1234/abc.def")
    assert "/" not in caminho.name
    assert caminho.name == "crossref_10.1234_abc.def.json"


def test_rate_limiter_espera_intervalo_minimo():
    limiter = RateLimiter(intervalo_minimo_s=0.2)
    t0 = time.monotonic()
    limiter.aguardar()  # primeira chamada não espera
    limiter.aguardar()  # segunda espera até completar o intervalo
    dt = time.monotonic() - t0
    assert dt >= 0.2
