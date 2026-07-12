# CLAUDE.md — modelagem-lab

> Laboratório pessoal de ciência de dados: modelagem estatística e ML em Python e R,
> técnicas clássicas e SOTA. Agnóstico de domínio; risco de crédito é um caso de uso
> suportado, não o único. **8 módulos de modelagem** (cada um um pacote Python
> separado top-level, costurados num funil por `pipeline_lab` — ver §7):
> `divisao` (split dev/teste) → `construcao` (razões/diferenças) → `agregacao_temporal`
> (behavioral scoring) → `interacao` (RuleFit-style) →
> `categorizacao` (binning) → `transformacao` (WOE/IV) → `preselecao` (filtros
> pré-Pedro_Wise) → `pedro_wise` (seleção final — treinamento). `modelagem_lab` é o
> pacote raiz que reexporta os 8 num namespace só, pra consumo externo (notebook);
> `pipeline_lab.Esteira` é o builder encadeável que compõe o funil sem desempacotar
> retorno na mão (ver `python/pipeline_lab/REFERENCIA.md`). Mais 2 pilares de
> suporte: scraping de literatura acadêmica aberta, e interface (2 versões: Streamlit
> v1 e FastAPI+Next.js v2, ambas em `app/`, ver §6-7).

---

## 1. Comandos

```bash
test:      pytest tests -x -v
lint:      ruff check python/ scraping/ scripts/ app/backend/
typecheck: mypy python/pedro_wise python/categorizacao python/transformacao python/construcao \
           python/agregacao_temporal python/interacao python/preselecao python/pipeline_lab \
           python/modelagem_lab scraping/
r-script:  Rscript r/<arquivo>.R
scraper:   python scraping/arxiv_client.py --query 'cat:stat.ML AND all:"variable selection"' --max 10
benchmark: python scripts/benchmark_paralelizacao.py
validar:   Rscript scripts/validar_port_r.R && python scripts/validar_port_python.py
pipeline:  python scripts/pipeline_completo_credito_real.py   # funil completo via pipeline_lab (ver REFERENCIA.md do módulo)
app-v1:    python -m streamlit run app/streamlit_app.py   # ver nota Windows em docs/planos/interface-streamlit.md
app-v2:    python -m uvicorn main:app --reload --port 8001 --app-dir app/backend  # + `cd app/frontend && npm run dev`
release:   git tag vX.Y.Z && git push --tags   # bump version em pyproject.toml antes -- Actions builda e anexa o wheel na Release
```
> Os 8 módulos de modelagem, scraping de literatura e as 2 versões de interface
> estão implementados e testados (143 testes Python + build/lint do frontend limpos).
> Todo código Python novo é type-hinted, testado e lintado.
>
> **Instalação como biblioteca** (fora do repo, ex.: notebook): não usar
> `git+https://...` com `--force-reinstall` (sintoma de falta de versão) —
> tagueie uma release (`git tag vX.Y.Z && git push --tags`, ver `.github/workflows/release.yml`)
> e instale o wheel publicado:
> `pip install https://github.com/PedroMaiorano/modelagem-lab/releases/download/vX.Y.Z/modelagem_lab-X.Y.Z-py3-none-any.whl`.
> Localmente, `pip install -e .` a partir da raiz do repo.

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
- Nunca reimplementar lógica de seleção/métrica/binning/WOE em `app/` (v1 ou v2) — a interface só consome os módulos `python/*` via `app/logica.py` (Streamlit) ou `app/backend/logica.py` (FastAPI).
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
| `model-builder` | agent | Construir/treinar modelos e pipelines — hoje cobre os 8 módulos do funil (`divisao`, `construcao`, `agregacao_temporal`, `interacao`, `categorizacao`, `transformacao`, `preselecao`, `pedro_wise`), não só seleção. Validação e avaliação. |
| `stats-advisor` | agent | Aconselha metodologia em qualquer um dos 8 módulos: qual técnica usar, clássica vs. SOTA, pressupostos. Decide o QUÊ; `model-builder` faz o COMO. |
| `port-r-python` | skill | Workflow passo-a-passo de port R→Python (usa `algorithm-porter`). |
| `buscar-literatura` | skill | Workflow de busca acadêmica com comandos concretos por API. |
| `selecao-variaveis` | skill | Workflow de seleção de variáveis (forward/backward/stepwise, regularização, boosting, stability selection). |
| `scaffold-interface` | skill | Scaffolding de Streamlit/FastAPI/Shiny. **Já ativada duas vezes** (v1 Streamlit e v2 FastAPI+Next.js, ambas em `app/`, ver `docs/planos/interface-streamlit.md` e `docs/planos/interface-v2-fastapi-react.md`) — reutilizar para expandir, não para recomeçar do zero. |

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
├── python/                             # cada pasta é um pacote top-level (ver pyproject.toml)
│   ├── modelagem_lab/                  # PACOTE RAIZ — reexporta os 8 módulos + Esteira num namespace só (consumo externo)
│   ├── pipeline_lab/                   # ORQUESTRAÇÃO do funil completo (divisao→...→treinamento) + esteira.py + REFERENCIA.md
│   ├── construcao/                     # razões/diferenças (escopo v1 mínimo, deliberado)
│   ├── agregacao_temporal/             # primitivas de janela móvel sobre painel (behavioral scoring)
│   ├── interacao/                      # descoberta de regras via RuleFit-style (GBM raso)
│   ├── categorizacao/                  # binning (largura/frequência/árvore/monotônico)
│   ├── transformacao/                  # WOE/IV (fit/transform anti-leakage)
│   ├── preselecao/                     # filtros (variância/IV/correlação) antes do Pedro_Wise
│   └── pedro_wise/                     # TREINAMENTO — port completo (níveis 1-3), métrica/estimador plugáveis
├── app/
│   ├── streamlit_app.py + logica.py    # interface v1 (Streamlit) — consome python/pedro_wise
│   ├── backend/                        # interface v2 — FastAPI + SSE (progresso em tempo real)
│   └── frontend/                       # interface v2 — Next.js 16 + TypeScript + Tailwind v4
├── r/                                  # protótipos/originais em R
├── scraping/                           # clients de APIs abertas (arXiv, S2, OpenAlex, CrossRef, Europe PMC)
├── scripts/                            # benchmark, validação R↔Python, experimentos, geração de datasets, pipeline completo
├── tests/                              # pytest (135 testes: 8 módulos + scraping)
├── notebooks/                          # exploração ad-hoc
└── data/papers/                        # cache imutável de metadados (gitignored)
```

---

## 7. Contexto de Domínio

### Os 8 módulos de modelagem — como compõem

`pipeline_lab` (coleção de funções soltas, nunca muta DataFrame de entrada,
nunca toca disco/rede) costura os módulos-núcleo nesta ordem — cada etapa
opcional exceto `divisao`/`categorizacao`/`treinamento`:

```
divisao → construcao (opc.) → agregacao_temporal (opc.) → interacao (opc.)
   → categorizacao+transformacao → preselecao (opc.) → pedro_wise
```

Ver `python/pipeline_lab/REFERENCIA.md` para a referência completa (toda
função pública, parâmetros, e a literatura que justifica cada decisão de
design) e `scripts/pipeline_completo_credito_real.py` para a composição
rodando de ponta a ponta — `docs/experimentos/pipeline-completo-credito-real.md`
tem o resultado (pipeline completo bate o baseline cru: KS 0.42 vs. 0.40).
Cada módulo é standalone (testável isolado) mas desenhado para essa costura.
Convenção de coluna-alvo a partir de `divisao`: a resposta sempre se chama `"y"`.

- **`modelagem_lab/`** (pacote raiz): reexporta os 8 pacotes-núcleo +
  `Esteira` num namespace só (`import modelagem_lab as ml`) — pensado pra
  consumo de fora do repo (notebook, outro projeto), evitando colisão de
  nome com pacotes genéricos de outros labs (`construcao`, `interacao`...)
  no mesmo ambiente Python. Nenhum código interno do repo precisa importar
  daqui — é só a porta de entrada externa.
- **`pipeline_lab/`** (orquestração): `divisao` (split dev/teste por amostra
  existente ou aleatório), `construcao`/`agregacao_temporal`/`interacao`
  (wrappers dos módulos-núcleo abaixo), `categorizar` (categorização+WOE
  juntos, última etapa antes de gerar as versões `_woe`/`_log`/`_bin` de
  cada base), `preselecao`, `treinamento`. Único lugar que sabe a ORDEM
  certa do funil. `esteira.py` (`Esteira`) é um builder mutável encadeável
  por cima dessas mesmas funções — resolve a inconsistência de retorno
  entre etapas (tuple/dict/dataclass) e impõe a ordem em runtime
  (`EtapaForaDeOrdemError`) em vez de só documentada.
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
- **`agregacao_temporal/`** (behavioral scoring): a partir de um
  painel (chave + tempo + variável mês a mês), gera primitivas de janela
  móvel (máximo/média/mínimo/desvio-padrão/tendência) — catálogo inspirado no
  vocabulário do Deep Feature Synthesis. Garante ausência de look-ahead (só
  usa histórico até o próprio período) e preserva o split dev/teste (agrega
  cada base separadamente). `safra.py` normaliza formatos inconsistentes de
  período (`anomes` int, string, `datetime`) antes de agregar.
- **`interacao/`** (descoberta de regras): RuleFit-style
  (Friedman & Popescu, 2008) — treina um ensemble de árvores rasas sobre as
  candidatas já construídas e extrai caminhos raiz-folha como regras de
  interação (≥2 condições), viram colunas 0/1 avaliadas por IV. Diferença
  deliberada do RuleFit original: aqui quem decide o que entra no modelo
  final continua sendo o Pedro_Wise, não uma regressão L1 própria.
  `estabilidade.py` reavalida suporte/IV de cada regra em teste (nunca
  reajusta) — regra é artefato de overfitting local até provar que generaliza.
- **`preselecao/`** (filtro pré-Pedro_Wise): 3 filtros em sequência e opcionais
  (variância → IV → correlação) — motivado por múltiplos testes (mesmo pano
  de fundo de stability selection) quando construção+transformações de
  potência geram dezenas de candidatas por base. Correlação nunca filtra
  entre versões da MESMA base (deixa o Pedro_Wise escolher a melhor versão).
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
