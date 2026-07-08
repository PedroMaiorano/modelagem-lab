# modelagem-lab

Laboratório pessoal de ciência de dados: modelagem estatística e ML em **Python e R**,
técnicas clássicas e SOTA, com foco em **seleção de variáveis, construção de modelos e
análises**. Agnóstico de domínio (risco de crédito é caso de uso, não único foco).

## Três pilares
1. **Port + melhoria do algoritmo Pedro_Wise** (seleção stepwise multi-nível, R→Python).
2. **Scraping de literatura acadêmica aberta** (arXiv, Semantic Scholar, OpenAlex, CrossRef, Europe PMC/PubMed).
3. **Interface futura** (Streamlit/FastAPI/Shiny) — preparado, não construído.

## Estrutura
```
docs/         base de conhecimento (SOTA tracker, APIs, algoritmo original, wiki de literatura)
python/       implementações Python (port + modelos)     [vazio — próxima etapa]
r/            protótipos/originais em R
scraping/     clients de APIs abertas                     [vazio — próxima etapa]
tests/        pytest
notebooks/    exploração ad-hoc
.claude/      configuração Claude Code (agents, skills, hooks)
```

## Começando
- Config e comportamento: ver [`CLAUDE.md`](CLAUDE.md).
- Fluxo de trabalho: [`docs/guias/fluxo-de-trabalho.md`](docs/guias/fluxo-de-trabalho.md).
- Estado da arte: [`docs/referencias/sota-tracker-modelagem.md`](docs/referencias/sota-tracker-modelagem.md).
- Algoritmo central (pilar 1): [`docs/algoritmos-originais/pedro-wise-resumo.md`](docs/algoritmos-originais/pedro-wise-resumo.md).

Comandos-alvo (o código ainda não existe — greenfield):
```bash
pytest tests -x -v      # testes
ruff check python/      # lint
mypy python/            # type check
```
