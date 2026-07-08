# modelagem-lab

Laboratório pessoal de ciência de dados: modelagem estatística e ML em **Python e R**,
técnicas clássicas e SOTA. Agnóstico de domínio (risco de crédito é caso de uso, não
único foco).

## 4 módulos de modelagem (compostos num pipeline)

```
construcao/  ──►  categorizacao/  ──►  transformacao/  ──►  pedro_wise/
(features novas)   (bins por var.)     (WOE por bin)        (seleção final)
```

1. **Categorização** (`python/categorizacao/`) — binning: largura/frequência igual, árvore, monotônico (aproximação do OptBinning). ✅ 7 testes.
2. **Transformação** (`python/transformacao/`) — WOE + Information Value, fit/transform anti-leakage. ✅ 11 testes. Fecha a lacuna histórica: `_woe` era só nome, agora é implementação.
3. **Construção** (`python/construcao/`) — razões/diferenças entre variáveis (escopo v1 deliberadamente mínimo). ✅ 5 testes.
4. **Treinamento** (`python/pedro_wise/`) — port completo (níveis 1-3) do algoritmo Pedro_Wise (R→Python), validado contra o R original, com 3 experimentos comparativos.

**Pipeline completo testado no dataset real**: bate o baseline cru (KS 0.42 vs. 0.40, AUC 0.76 vs. 0.73) — ver [`docs/experimentos/pipeline-completo-credito-real.md`](docs/experimentos/pipeline-completo-credito-real.md).

## Pilares de suporte
- **Scraping de literatura acadêmica aberta** (arXiv, Semantic Scholar, OpenAlex, CrossRef, Europe PMC/PubMed) — ✅ clients implementados e testados, ~58 referências catalogadas nos 4 módulos + livros.
- **Interface** (dashboard Streamlit) — ✅ v1 funcional em `app/`. Pedido pendente do usuário: versão mais fluida/bonita — ver `docs/planos/expansao-modulos-2026-07-08.md`.

## Estrutura
```
docs/         base de conhecimento (SOTA tracker, APIs, literatura por módulo, experimentos, livros)
python/       categorizacao/ transformacao/ construcao/ pedro_wise/ — os 4 módulos
app/          dashboard Streamlit — consome python/*, não reimplementa
r/            protótipos/originais em R
scraping/     clients de APIs abertas (arXiv, Semantic Scholar, OpenAlex, CrossRef, Europe PMC)
scripts/      benchmark, validação R↔Python, experimentos comparativos, geração de datasets, pipeline completo
tests/        pytest (63 testes)
notebooks/    exploração ad-hoc
.claude/      configuração Claude Code (agents, skills, hooks)
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
- Interface: [`docs/planos/interface-streamlit.md`](docs/planos/interface-streamlit.md).

## Comandos
```bash
pytest tests -x -v                                                      # testes (63)
ruff check python/ scraping/ scripts/ app/                              # lint
mypy python/pedro_wise python/categorizacao python/transformacao python/construcao scraping/  # type check (strict)

python scripts/pipeline_completo_credito_real.py                        # construção->categorização->WOE->treinamento
python scraping/arxiv_client.py --query 'cat:stat.ML AND all:"variable selection"' --max 10
python scripts/benchmark_paralelizacao.py                               # mede backend/n_jobs
Rscript scripts/validar_port_r.R && python scripts/validar_port_python.py  # revalida port vs. R
python -m streamlit run app/streamlit_app.py                            # dashboard (use python -m, não `streamlit` direto)
```
