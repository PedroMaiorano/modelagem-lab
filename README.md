# modelagem-lab

Laboratório pessoal de ciência de dados: modelagem estatística e ML em **Python e R**,
técnicas clássicas e SOTA. Agnóstico de domínio (risco de crédito é caso de uso, não
único foco).

## 8 módulos de modelagem (costurados num funil por `pipeline_lab`)

```
divisao → construcao (opc.) → agregacao_temporal/esfera1 (opc.) → interacao/esfera2 (opc.)
   → categorizacao+transformacao → preselecao (opc.) → pedro_wise
```

`python/pipeline_lab/` é a orquestração: coleção de funções soltas (não uma
API orientada a objeto) que compõem os módulos-núcleo na ordem certa, sempre
sobre um `pandas.DataFrame` — ver [`python/pipeline_lab/REFERENCIA.md`](python/pipeline_lab/REFERENCIA.md)
para toda função pública, parâmetro e a literatura que justifica cada decisão.

1. **Construção** (`python/construcao/`) — razões/diferenças entre variáveis (escopo v1 deliberadamente mínimo).
2. **Agregação temporal** (`python/agregacao_temporal/`, "esfera 1") — primitivas de janela móvel sobre painel (máximo/média/mínimo/desvio-padrão/tendência), sem look-ahead, preservando o split dev/teste — behavioral scoring.
3. **Interação** (`python/interacao/`, "esfera 2") — descoberta de regras estilo RuleFit (ensemble de árvores rasas → caminhos raiz-folha viram candidatas 0/1), com validação de estabilidade out-of-time.
4. **Categorização** (`python/categorizacao/`) — binning: largura/frequência igual, árvore, monotônico (aproximação do OptBinning).
5. **Transformação** (`python/transformacao/`) — WOE + Information Value + Box-Cox/Yeo-Johnson, fit/transform anti-leakage. Fecha a lacuna histórica: `_woe` era só nome, agora é implementação.
6. **Pré-seleção** (`python/preselecao/`) — filtros de variância/IV/correlação antes do Pedro_Wise, para conter a explosão combinatória de candidatas (construção + transformações de potência).
7. **Treinamento** (`python/pedro_wise/`) — port completo (níveis 1-3) do algoritmo Pedro_Wise (R→Python), validado contra o R original, com 3 experimentos comparativos.

✅ 135 testes cobrindo os 8 módulos + scraping.

**Pipeline completo testado no dataset real**: bate o baseline cru (KS 0.42 vs. 0.40, AUC 0.76 vs. 0.73) — ver [`docs/experimentos/pipeline-completo-credito-real.md`](docs/experimentos/pipeline-completo-credito-real.md).

## Pilares de suporte
- **Scraping de literatura acadêmica aberta** (arXiv, Semantic Scholar, OpenAlex, CrossRef, Europe PMC/PubMed) — ✅ clients implementados e testados, ~58 referências catalogadas nos 4 módulos + livros.
- **Interface** — duas versões, ambas em `app/`:
  - v1: dashboard Streamlit (`app/streamlit_app.py`) — exploratório, simples.
  - v2: FastAPI + Next.js/Tailwind (`app/backend/`, `app/frontend/`) — progresso em tempo real via SSE, UI mais fluida. Ver [`docs/planos/interface-v2-fastapi-react.md`](docs/planos/interface-v2-fastapi-react.md).

## Estrutura
```
docs/          base de conhecimento (SOTA tracker, APIs, literatura por módulo, experimentos, livros)
python/        pipeline_lab/ (orquestração) + construcao/ agregacao_temporal/ interacao/
               categorizacao/ transformacao/ preselecao/ pedro_wise/ — os 8 módulos
app/           streamlit_app.py (v1) + backend/ e frontend/ (v2) — consomem python/*, não reimplementam
r/             protótipos/originais em R
scraping/      clients de APIs abertas (arXiv, Semantic Scholar, OpenAlex, CrossRef, Europe PMC)
scripts/       benchmark, validação R↔Python, experimentos comparativos, geração de datasets, pipeline completo
tests/         pytest (68 testes)
notebooks/     exploração ad-hoc
.claude/       configuração Claude Code (agents, skills, hooks)
```

## Começando
- Config e comportamento: ver [`CLAUDE.md`](CLAUDE.md).
- **Continuidade/estado do projeto**: [`docs/planos/expansao-modulos-2026-07-08.md`](docs/planos/expansao-modulos-2026-07-08.md) — comece por aqui se estiver retomando o trabalho numa sessão nova.
- Fluxo de trabalho: [`docs/guias/fluxo-de-trabalho.md`](docs/guias/fluxo-de-trabalho.md).
- Estado da arte: [`docs/referencias/sota-tracker-modelagem.md`](docs/referencias/sota-tracker-modelagem.md).
- Literatura por módulo: [`docs/literatura/`](docs/literatura/) — categorização, transformação, construção, treinamento.
- Livros de referência: [`docs/referencias/livros.md`](docs/referencias/livros.md).
- Algoritmo central (treinamento): [`docs/algoritmos-originais/pedro-wise-resumo.md`](docs/algoritmos-originais/pedro-wise-resumo.md) — inclui validação numérica contra o R original.
- Experimentos comparativos: [`docs/experimentos/`](docs/experimentos/).
- Datasets disponíveis: [`docs/referencias/datasets.md`](docs/referencias/datasets.md) — inclui `credito_real` (UCI, dado real).
- Interface: [`docs/planos/interface-streamlit.md`](docs/planos/interface-streamlit.md) (v1) e [`docs/planos/interface-v2-fastapi-react.md`](docs/planos/interface-v2-fastapi-react.md) (v2).

## Comandos
```bash
pytest tests -x -v                                                      # testes (135)
ruff check python/ scraping/ scripts/ app/backend/                      # lint
mypy python/pedro_wise python/categorizacao python/transformacao python/construcao scraping/  # type check (strict)

python scripts/pipeline_completo_credito_real.py                        # funil completo via pipeline_lab
python scraping/arxiv_client.py --query 'cat:stat.ML AND all:"variable selection"' --max 10
python scripts/benchmark_paralelizacao.py                               # mede backend/n_jobs
Rscript scripts/validar_port_r.R && python scripts/validar_port_python.py  # revalida port vs. R

python -m streamlit run app/streamlit_app.py                            # interface v1 (use python -m, não `streamlit` direto)
python -m uvicorn main:app --reload --port 8001 --app-dir app/backend   # interface v2 — backend
cd app/frontend && npm run dev                                          # interface v2 — frontend (outro terminal)
```
