# CLAUDE.md — modelagem-lab

> Laboratório pessoal de ciência de dados: modelagem estatística e ML em Python e R,
> técnicas clássicas e SOTA, com foco em **seleção de variáveis, construção de modelos
> e análises**. Agnóstico de domínio; risco de crédito é um caso de uso suportado,
> não o único. Três pilares: (1) port+melhoria do algoritmo Pedro_Wise (R→Python),
> (2) scraping de literatura acadêmica aberta, (3) preparo para interface futura.

---

## 1. Comandos

```bash
test:      pytest tests -x -v
lint:      ruff check python/ scraping/ scripts/
typecheck: mypy python/pedro_wise scraping/
r-script:  Rscript r/<arquivo>.R
scraper:   python scraping/arxiv_client.py --query 'cat:stat.ML AND all:"variable selection"' --max 10
benchmark: python scripts/benchmark_paralelizacao.py
validar:   Rscript scripts/validar_port_r.R && python scripts/validar_port_python.py
```
> Pilares 1 (port Pedro_Wise) e 2 (scraping de literatura) implementados e testados.
> Pilar 3 (interface) segue dormente — só ativa a skill `scaffold-interface` quando pedido.
> Todo código Python novo é type-hinted, testado e lintado.

---

## 2. Comportamento

### Sempre
- **Pesquise antes de afirmar SOTA.** Antes de recomendar uma técnica de seleção/modelagem como "estado da arte", confira `docs/referencias/sota-tracker-modelagem.md`. Se o tópico não estiver lá, dispare `buscar-literatura` — não invente atualidade.
- **Métrica e família são plugáveis.** Ao construir ou portar qualquer seleção de variáveis, trate a métrica (KS, AUC/Gini, log-loss, AIC/BIC, R²aj) e o estimador (GLM binomial, outras famílias, boosting) como parâmetros injetáveis — nunca hardcode como no R original.
- **Anti-leakage é lei.** Seleção e avaliação usam split treino/validação/teste (ou temporal quando houver ordem). Reportar métrica de treino como se fosse desempenho é erro grave.
- **Cache de literatura é imutável.** Antes de buscar em qualquer API, cheque `data/papers/` — não re-baixe metadados já salvos (desperdício e risco de rate limit).
- Paralelize buscas/leituras independentes na mesma mensagem.

### Nunca
- Nunca fazer scraping de paywall, Sci-Hub, ou qualquer fonte fechada. Só fontes 100% abertas (arXiv, Semantic Scholar, OpenAlex, CrossRef, Europe PMC/PubMed, repositórios OA). Ver `docs/referencias/apis-fontes-abertas.md`.
- Nunca reproduzir os anti-padrões do R original no port (ver seção 7): `rbind` em loop, refit total por teste, `cat()` como log, recursão sem memoização.
- Nunca commitar sem pedido explícito do usuário. Nunca commitar `.env`, dados brutos pesados ou credenciais.
- Nunca construir a interface (pilar 3) agora — apenas manter `scaffold-interface` pronta para quando o usuário pedir.
- Nunca comentar O QUÊ o código faz — só o PORQUÊ não-óbvio.

---

## 3. Estilo e Tom

- Português, direto e técnico. O usuário é modelador experiente (background risco de crédito) — nada de explicação introdutória, mas pode querer relembrar uma técnica específica.
- Ao recomendar uma técnica, entregue: quando usar, pressupostos, alternativa clássica vs. SOTA, e trade-off — não um ensaio.
- Referências de arquivo: `[arquivo.py:42](python/arquivo.py#L42)`.

---

## 4. Agentes e Skills Disponíveis

| Artefato | Tipo | Quando usar |
|----------|------|-------------|
| `algorithm-porter` | agent | Port R→Python **com melhoria algorítmica** — o caso central é o Pedro_Wise. Carrega o contexto do algoritmo original. |
| `literature-scout` | agent | Busca + síntese de literatura em fontes abertas; alimenta a wiki `docs/literatura/`. |
| `model-builder` | agent | Construir/treinar modelos e pipelines de seleção de variáveis; validação e avaliação. |
| `stats-advisor` | agent | Aconselha metodologia: qual técnica de seleção/modelagem usar, clássica vs. SOTA, pressupostos. Decide o QUÊ; `model-builder` faz o COMO. |
| `port-r-python` | skill | Workflow passo-a-passo de port R→Python (usa `algorithm-porter`). |
| `buscar-literatura` | skill | Workflow de busca acadêmica com comandos concretos por API. |
| `selecao-variaveis` | skill | Workflow de seleção de variáveis (forward/backward/stepwise, regularização, boosting, stability selection). |
| `scaffold-interface` | skill | **Dormente** — scaffolding de Streamlit/FastAPI/Shiny. Só ativa quando o usuário pedir a interface. |

---

## 5. Segurança e Permissões

- `settings.json` (compartilhável): permissões calibradas ao mínimo necessário — Python, R, git de leitura+commit, curl para APIs abertas, WebFetch/WebSearch. **NÃO** usa `bypassPermissions`; este é um lab de trabalho real.
- `settings.local.json` (gitignored): permissões pessoais incrementais e `additionalDirectories`.
- Hook `pre-bash-safety.js` bloqueia deleção de `docs/`, `data/papers/` e git destrutivo.
- Comandos destrutivos sobre acervo (`docs/`, `data/papers/`) exigem confirmação explícita.

---

## 6. Estrutura do Projeto

```
modelagem-lab/
├── docs/
│   ├── referencias/
│   │   ├── sota-tracker-modelagem.md   # SOTA de seleção/modelagem — coração do lab
│   │   └── apis-fontes-abertas.md      # APIs acadêmicas abertas (endpoints, limites)
│   ├── algoritmos-originais/
│   │   ├── Pedro_Wise_3.0.1.R          # cópia fiel do algoritmo original
│   │   └── pedro-wise-resumo.md        # lógica + anti-padrões + plano de port
│   ├── literatura/                     # técnicas documentadas (wiki, por literature-scout)
│   ├── guias/                          # guias de uso
│   ├── planos/                         # decisões de arquitetura/config
│   └── INDEX.md                        # mapa da wiki
├── python/pedro_wise/                  # port completo (níveis 1-3), métrica/estimador plugáveis
├── r/                                  # protótipos/originais em R
├── scraping/                           # clients de APIs abertas (arXiv, S2, OpenAlex, CrossRef, Europe PMC)
├── scripts/                            # benchmark, validação R↔Python, geração de dataset sintético
├── tests/                              # pytest (34 testes: port + scraping)
├── notebooks/                          # exploração ad-hoc
└── data/papers/                        # cache imutável de metadados (gitignored)
```

---

## 7. Contexto de Domínio

- **Pedro_Wise é a peça central do pilar 1.** É uma busca greedy multi-nível para GLM binomial que otimiza KS. O port Python deve preservar a *lógica de seleção* mas corrigir os anti-padrões e generalizar métrica/família. Leia `docs/algoritmos-originais/pedro-wise-resumo.md` antes de portar — não decifre o `.R` do zero.
- **Variáveis têm sufixo de transformação** (`_woe`, `_log`, ...). A "base" é o prefixo antes do último `_`. A seleção nunca coloca duas versões da mesma base no modelo ao mesmo tempo; "transformação simples" troca uma versão por outra da mesma base. Preserve essa semântica no port.
- **KS via score Gaussiano**: o R transforma probabilidade → `xbeta` → score 0-1000 truncado por faixas de percentil, depois roda `ks.test` entre score de y=1 e y=0. No port, isso é *uma* implementação da interface de métrica plugável, não a métrica única.
- **SOTA importa aqui.** A seleção stepwise clássica do Pedro_Wise deve conviver com alternativas modernas (LASSO/elastic net, component-wise boosting, stability selection, shadow-variable probing, AutoML). O `stats-advisor` conhece essas conexões; ver o SOTA tracker.
- **Fontes de literatura só abertas.** arXiv (XML, sem chave), Semantic Scholar (100 req/5min sem chave), OpenAlex e CrossRef (sem chave, polite pool via `mailto`), PubMed E-utilities (3 req/s sem chave). Detalhes operacionais em `docs/referencias/apis-fontes-abertas.md`.
- **Última verificação SOTA**: 2026-07-07. Reveja com `buscar-literatura` quando encostar em técnica não listada no tracker.
