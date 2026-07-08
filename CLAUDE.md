# CLAUDE.md — modelagem-lab

> Laboratório pessoal de ciência de dados: modelagem estatística e ML em Python e R,
> técnicas clássicas e SOTA. Agnóstico de domínio; risco de crédito é um caso de uso
> suportado, não o único. **4 módulos de modelagem** (cada um um pacote Python
> separado, compostos num pipeline — ver §7): **categorização** (binning),
> **transformação** (WOE/encodings), **construção** (feature engineering),
> **treinamento** (seleção de variáveis/modelos — o Pedro_Wise). Mais 2 pilares de
> suporte: scraping de literatura acadêmica aberta, e interface (dashboard em `app/`).

---

## 1. Comandos

```bash
test:      pytest tests -x -v
lint:      ruff check python/ scraping/ scripts/ app/
typecheck: mypy python/pedro_wise python/categorizacao python/transformacao python/construcao scraping/
r-script:  Rscript r/<arquivo>.R
scraper:   python scraping/arxiv_client.py --query 'cat:stat.ML AND all:"variable selection"' --max 10
benchmark: python scripts/benchmark_paralelizacao.py
validar:   Rscript scripts/validar_port_r.R && python scripts/validar_port_python.py
pipeline:  python scripts/pipeline_completo_credito_real.py   # construção->categorização->WOE->treinamento
app:       python -m streamlit run app/streamlit_app.py   # ver nota Windows em docs/planos/interface-streamlit.md
```
> Os 4 módulos de modelagem (categorização, transformação, construção, treinamento),
> scraping de literatura e interface (v1) estão implementados e testados (63 testes).
> Todo código Python novo é type-hinted, testado e lintado.
> **Próximo pedido pendente do usuário** (explicitamente adiado até os módulos
> estarem prontos): interface mais fluida/responsiva/bonita que o Streamlit v1
> atual — ver `docs/planos/expansao-modulos-2026-07-08.md` antes de iniciar.

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
- Nunca reimplementar lógica de seleção/métrica em `app/` — a interface só consome `python/pedro_wise` via `app/logica.py`.
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
| `model-builder` | agent | Construir/treinar modelos e pipelines — hoje cobre os 4 módulos (`categorizacao`, `transformacao`, `construcao`, `pedro_wise`), não só seleção. Validação e avaliação. |
| `stats-advisor` | agent | Aconselha metodologia em qualquer um dos 4 módulos: qual técnica usar, clássica vs. SOTA, pressupostos. Decide o QUÊ; `model-builder` faz o COMO. |
| `port-r-python` | skill | Workflow passo-a-passo de port R→Python (usa `algorithm-porter`). |
| `buscar-literatura` | skill | Workflow de busca acadêmica com comandos concretos por API. |
| `selecao-variaveis` | skill | Workflow de seleção de variáveis (forward/backward/stepwise, regularização, boosting, stability selection). |
| `scaffold-interface` | skill | Scaffolding de Streamlit/FastAPI/Shiny. **Já ativada uma vez** (v1 do dashboard em `app/`, ver `docs/planos/interface-streamlit.md`) — reutilizar para expandir a interface, não para recomeçar do zero. |

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
│   ├── experimentos/                   # comparações Pedro_Wise vs. alternativas, com achados
│   ├── guias/                          # guias de uso
│   ├── planos/                         # decisões de arquitetura/config
│   └── INDEX.md                        # mapa da wiki
├── python/
│   ├── pedro_wise/                     # módulo TREINAMENTO — port completo (níveis 1-3), métrica/estimador plugáveis
│   ├── categorizacao/                  # módulo CATEGORIZAÇÃO — binning (largura/frequência/árvore/monotônico)
│   ├── transformacao/                  # módulo TRANSFORMAÇÃO — WOE/IV (fit/transform anti-leakage)
│   └── construcao/                     # módulo CONSTRUÇÃO — razões/diferenças (escopo v1 mínimo, deliberado)
├── app/                                # dashboard Streamlit (pilar interface) — consome python/*, não reimplementa
├── r/                                  # protótipos/originais em R
├── scraping/                           # clients de APIs abertas (arXiv, S2, OpenAlex, CrossRef, Europe PMC)
├── scripts/                            # benchmark, validação R↔Python, experimentos, geração de datasets, pipeline completo
├── tests/                              # pytest (63 testes: 4 módulos + scraping)
├── notebooks/                          # exploração ad-hoc
└── data/papers/                        # cache imutável de metadados (gitignored)
```

---

## 7. Contexto de Domínio

### Os 4 módulos de modelagem — como compõem

```
construcao/  ──►  categorizacao/  ──►  transformacao/  ──►  pedro_wise/
(features novas)   (bins por var.)     (WOE por bin)        (seleção final)
```

Ver `scripts/pipeline_completo_credito_real.py` para a composição completa
rodando de ponta a ponta, e `docs/experimentos/pipeline-completo-credito-real.md`
para o resultado (pipeline completo bate o baseline cru: KS 0.42 vs. 0.40).
Cada módulo é standalone (testável isolado) mas desenhado para essa costura.

- **`categorizacao/`** (binning): `bins_largura_igual`/`bins_frequencia_igual`
  (baseline não-supervisionado), `bins_arvore` (supervisionado via árvore
  rasa), `bins_monotonicos` (merge guloso até taxa de evento monotônica —
  aproximação pragmática do OptBinning/MIP, documentada como tal, não a
  solução ótima). Ver `docs/literatura/categorizacao.md`.
- **`transformacao/`** (WOE/IV): fecha a lacuna histórica do lab — `_woe` era
  só convenção de nome até isso existir. Convenção de sinal: WOE positivo =
  mais não-evento (Siddiqi). `ajustar_woe`/`aplicar_woe` seguem fit/transform
  (anti-leakage: tabela ajustada só no dev). `classificar_iv` dá a régua de
  interpretação prática (>0.5 = suspeito de vazamento — já pegou um caso real
  no `credito_real`, `PAY0` IV=0.83). Ver `docs/literatura/transformacao.md`.
- **`construcao/`** (feature engineering): escopo v1 **deliberadamente
  mínimo** — razões/diferenças interpretáveis, não busca automática
  (GP/RL/Deep Feature Synthesis). Motivo documentado em
  `docs/literatura/construcao-variaveis.md` — é o módulo menos maduro na
  literatura (duas escolas divergentes), maior risco de over-engineering.
- **`pedro_wise/`** (treinamento/seleção — pilar histórico do lab): busca
  greedy multi-nível para GLM binomial que otimiza KS. Preserva a *lógica de
  seleção* do R original mas corrige anti-padrões e generaliza métrica/família
  (protocolos plugáveis). Leia `docs/algoritmos-originais/pedro-wise-resumo.md`
  antes de portar mais — não decifre o `.R` do zero.

### Semântica e convenções que atravessam os módulos

- **Variáveis têm sufixo de transformação** (`_woe`, `_log`, ...). A "base" é
  o prefixo antes do último `_` (`pedro_wise.base.extrair_base`). A seleção
  nunca coloca duas versões da mesma base no modelo ao mesmo tempo.
  **Datasets reais fora dessa convenção precisam de prep** — ver
  `docs/referencias/datasets.md` (`credito_real`: colunas UCI como `PAY_0`
  tiveram os underscores removidos antes de entrar no Pedro_Wise, senão
  colidiam de base com `PAY_AMT1`).
- **KS via score Gaussiano**: o R transforma probabilidade → `xbeta` → score
  0-1000 truncado por faixas de percentil, depois roda `ks.test`. No port,
  isso é *uma* implementação da interface de métrica plugável, não a única.
- **SOTA importa aqui.** Cada módulo deve conviver com alternativas modernas
  (LASSO/elastic net, component-wise boosting, stability selection,
  shadow-variable probing, AutoML, OptBinning, target encoding regularizado).
  O `stats-advisor` conhece essas conexões; ver o SOTA tracker e
  `docs/literatura/` (organizada pelos mesmos 4 módulos).
- **Fontes de literatura só abertas.** arXiv (XML, sem chave), Semantic
  Scholar (100 req/5min sem chave — bate rate limit fácil, já aconteceu),
  OpenAlex e CrossRef (sem chave, polite pool via `mailto`), PubMed
  E-utilities (3 req/s sem chave). Detalhes em `docs/referencias/apis-fontes-abertas.md`.
- **Última verificação SOTA**: 2026-07-08 (ampliação grande — ver
  `docs/planos/expansao-modulos-2026-07-08.md`). Reveja com `buscar-literatura`
  quando encostar em técnica não listada no tracker.
