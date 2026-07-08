# modelagem-lab

Laboratório pessoal de ciência de dados: modelagem estatística e ML em **Python e R**,
técnicas clássicas e SOTA, com foco em **seleção de variáveis, construção de modelos e
análises**. Agnóstico de domínio (risco de crédito é caso de uso, não único foco).

## Três pilares
1. **Port + melhoria do algoritmo Pedro_Wise** (seleção stepwise multi-nível, R→Python) — ✅ completo (níveis 1-3), validado contra o R original, 2 experimentos comparativos.
2. **Scraping de literatura acadêmica aberta** (arXiv, Semantic Scholar, OpenAlex, CrossRef, Europe PMC/PubMed) — ✅ clients implementados e testados, 3 tópicos documentados.
3. **Interface** (dashboard Streamlit) — ✅ v1 funcional em `app/`.

## Estrutura
```
docs/         base de conhecimento (SOTA tracker, APIs, algoritmo original, literatura, experimentos)
python/       port do Pedro_Wise (níveis 1-3), métrica/estimador plugáveis
app/          dashboard Streamlit (pilar 3) — consome python/pedro_wise, não reimplementa
r/            protótipos/originais em R
scraping/     clients de APIs abertas (arXiv, Semantic Scholar, OpenAlex, CrossRef, Europe PMC)
scripts/      benchmark de paralelização, validação R↔Python, experimentos comparativos, geração de datasets
tests/        pytest (40 testes)
notebooks/    exploração ad-hoc
.claude/      configuração Claude Code (agents, skills, hooks)
```

## Começando
- Config e comportamento: ver [`CLAUDE.md`](CLAUDE.md).
- Fluxo de trabalho: [`docs/guias/fluxo-de-trabalho.md`](docs/guias/fluxo-de-trabalho.md).
- Estado da arte: [`docs/referencias/sota-tracker-modelagem.md`](docs/referencias/sota-tracker-modelagem.md).
- Algoritmo central (pilar 1): [`docs/algoritmos-originais/pedro-wise-resumo.md`](docs/algoritmos-originais/pedro-wise-resumo.md) — inclui a validação numérica contra o R original.
- Experimentos comparativos: [`docs/experimentos/`](docs/experimentos/) — Pedro_Wise vs. LASSO vs. stability selection.
- Paralelização: [`docs/referencias/benchmark-paralelizacao.md`](docs/referencias/benchmark-paralelizacao.md).
- Fontes de literatura: [`docs/referencias/apis-fontes-abertas.md`](docs/referencias/apis-fontes-abertas.md).
- Interface: [`docs/planos/interface-streamlit.md`](docs/planos/interface-streamlit.md).

## Comandos
```bash
pytest tests -x -v                                  # testes (40)
ruff check python/ scraping/ scripts/                # lint
mypy python/pedro_wise scraping/                     # type check (strict)

python scraping/arxiv_client.py --query 'cat:stat.ML AND all:"variable selection"' --max 10
python scripts/benchmark_paralelizacao.py            # mede backend/n_jobs
Rscript scripts/validar_port_r.R && python scripts/validar_port_python.py  # revalida port vs. R
python -m streamlit run app/streamlit_app.py         # dashboard (use python -m, não `streamlit` direto)
```
