# modelagem-lab

Laboratório pessoal de ciência de dados: modelagem estatística e ML em **Python e R**,
técnicas clássicas e SOTA, com foco em **seleção de variáveis, construção de modelos e
análises**. Agnóstico de domínio (risco de crédito é caso de uso, não único foco).

## Três pilares
1. **Port + melhoria do algoritmo Pedro_Wise** (seleção stepwise multi-nível, R→Python) — ✅ completo (níveis 1-3), validado contra o R original.
2. **Scraping de literatura acadêmica aberta** (arXiv, Semantic Scholar, OpenAlex, CrossRef, Europe PMC/PubMed) — ✅ clients implementados e testados.
3. **Interface futura** (Streamlit/FastAPI/Shiny) — preparado (skill `scaffold-interface`), não construído.

## Estrutura
```
docs/         base de conhecimento (SOTA tracker, APIs, algoritmo original, wiki de literatura)
python/       port do Pedro_Wise (níveis 1-3), métrica/estimador plugáveis
r/            protótipos/originais em R
scraping/     clients de APIs abertas (arXiv, Semantic Scholar, OpenAlex, CrossRef, Europe PMC)
scripts/      benchmark de paralelização, validação R↔Python, geração de dataset sintético
tests/        pytest (34 testes)
notebooks/    exploração ad-hoc
.claude/      configuração Claude Code (agents, skills, hooks)
```

## Começando
- Config e comportamento: ver [`CLAUDE.md`](CLAUDE.md).
- Fluxo de trabalho: [`docs/guias/fluxo-de-trabalho.md`](docs/guias/fluxo-de-trabalho.md).
- Estado da arte: [`docs/referencias/sota-tracker-modelagem.md`](docs/referencias/sota-tracker-modelagem.md).
- Algoritmo central (pilar 1): [`docs/algoritmos-originais/pedro-wise-resumo.md`](docs/algoritmos-originais/pedro-wise-resumo.md) — inclui a validação numérica contra o R original.
- Paralelização: [`docs/referencias/benchmark-paralelizacao.md`](docs/referencias/benchmark-paralelizacao.md).
- Fontes de literatura: [`docs/referencias/apis-fontes-abertas.md`](docs/referencias/apis-fontes-abertas.md).

## Comandos
```bash
pytest tests -x -v                                  # testes (34)
ruff check python/ scraping/ scripts/                # lint
mypy python/pedro_wise scraping/                     # type check (strict)

python scraping/arxiv_client.py --query 'cat:stat.ML AND all:"variable selection"' --max 10
python scripts/benchmark_paralelizacao.py            # mede backend/n_jobs
Rscript scripts/validar_port_r.R && python scripts/validar_port_python.py  # revalida port vs. R
```
