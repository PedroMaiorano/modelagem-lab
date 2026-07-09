# INDEX — modelagem-lab

Mapa da base de conhecimento do lab.

## Referências (`docs/referencias/`)
- [sota-tracker-modelagem](referencias/sota-tracker-modelagem.md) — estado da arte: seleção de variáveis, modelos, AutoML, causal ML. **Coração do lab.**
- [apis-fontes-abertas](referencias/apis-fontes-abertas.md) — APIs acadêmicas abertas (arXiv, Semantic Scholar, OpenAlex, CrossRef, Europe PMC/PubMed): endpoints, limites, exemplos.
- [datasets](referencias/datasets.md) — datasets disponíveis em `data/` (gitignored, reproduzíveis via script), incluindo `credito_real` (UCI, dado real de crédito).
- [livros](referencias/livros.md) — livros-texto de referência (scorecards, feature engineering, modelagem estatística, AutoML), com link para versão aberta quando existe.
- [benchmark-paralelizacao](referencias/benchmark-paralelizacao.md) — medição de paralelização do port (backend/n_jobs).

## Algoritmos Originais (`docs/algoritmos-originais/`)
- [pedro-wise-resumo](algoritmos-originais/pedro-wise-resumo.md) — lógica do Pedro_Wise, anti-padrões e plano de port (**pilar 1 / módulo treinamento**).
- `Pedro_Wise_3.0.1.R` — cópia fiel do algoritmo R original.

## Literatura (`docs/literatura/`)
Wiki de técnicas documentadas — populada pelo `literature-scout`. Ver [README](literatura/README.md). Organizada pelos 4 módulos de modelagem do lab (ver `docs/guias/fluxo-de-trabalho.md`):

**Categorização** (binning/discretização):
- [categorizacao](literatura/categorizacao.md) — 13 refs. OptBinning (Navas-Palencia), MODL/Khiops (Boullé), família CAIM/ur-CAIM/Ameva, discretização por AUC, viés/variância do nº de bins.

**Transformação** (WOE, encodings, Box-Cox/Yeo-Johnson):
- [transformacao](literatura/transformacao.md) — 11 refs. Target encoding regularizado (Pargent et al.), similarity encoding (Cerda et al.), revisão Box-Cox (Atkinson et al.), quantile normalization.

**Construção** (feature engineering/construction):
- [construcao-variaveis](literatura/construcao-variaveis.md) — 12 refs. Deep Feature Synthesis (Kanter & Veeramachaneni), TPOT, programação genética para construção de features, feature engineering via árvore aplicado a crédito.

**Treinamento** (seleção de variáveis/modelos — pilar 1):
- [stability-selection](literatura/stability-selection.md) — 5 refs. Meta-procedimento de estabilização; achado do Faletto & Bien (2022) sobre falha com proxies correlacionados, conectado ao forward duplo do Pedro_Wise.
- [shadow-variable-probing](literatura/shadow-variable-probing.md) — 3 refs. Critério de parada em single-fit via variáveis permutadas; motivou a implementação em `python/pedro_wise/shadow_probing.py`.
- Mais referências de treinamento (boosting, AutoML, causal ML) em `sota-tracker-modelagem.md` §1-3.

**Total catalogado**: ~50 referências entre papers e livros, nos 4 escopos.

## Experimentos (`docs/experimentos/`)
- [pedro-wise-vs-alternativas](experimentos/pedro-wise-vs-alternativas.md) — Pedro_Wise vs. LASSO vs. stability selection no mesmo dataset sintético (gabarito conhecido). Achado central: LASSO/stability selection cravaram o modelo exato; o Pedro_Wise aceitou 1 variável de ruído por otimizar KS contra um split de teste fixo.
- [colinearidade-stability-selection](experimentos/colinearidade-stability-selection.md) — reproduz a falha do Faletto & Bien (2022) sob proxies quase-duplicadas (corr 0.919): stability selection retorna modelo vazio (AUC 0.500) numa janela estreita de regularização, enquanto LASSO/Pedro_Wise no mesmo C recuperam o sinal. Corrige hipótese: não é o `forward_duplo` que evita a falha, é não depender de consistência entre reamostragens.
- [pipeline-completo-credito-real](experimentos/pipeline-completo-credito-real.md) — primeira prova de integração dos 4 módulos (construção→categorização→WOE→treinamento) no dataset real. Pipeline completo supera o baseline cru (KS 0.42 vs. 0.40, AUC 0.76 vs. 0.73); variável construída (`proppaga1_woe`) entra no modelo final. Acha e reporta honestamente `PAY0` com IV=0.83 ("suspeito/possível vazamento" pela própria régua do lab).

## Guias (`docs/guias/`)
- [fluxo-de-trabalho](guias/fluxo-de-trabalho.md) — como os módulos (categorização, transformação, construção, treinamento) e os agentes/skills se encaixam.

## Planos (`docs/planos/`)
- [modelagem-lab-config](planos/modelagem-lab-config.md) — decisões de arquitetura da configuração Claude Code deste lab.
- [interface-streamlit](planos/interface-streamlit.md) — decisão de framework e escopo da interface v1 (dashboard Streamlit em `app/`).
- [expansao-modulos-2026-07-08](planos/expansao-modulos-2026-07-08.md) — decisão de expandir de "3 pilares" para 4 módulos de modelagem (categorização/transformação/construção/treinamento) + pedido de interface melhor (pós-Streamlit).
- [interface-v2-fastapi-react](planos/interface-v2-fastapi-react.md) — interface v2 (FastAPI + Next.js/Tailwind), progresso em tempo real via SSE sem tocar o core. Documenta 2 bugs reais encontrados e corrigidos (double-suffix `_woe`, separador de frame SSE `\r\n\r\n` vs `\n\n`) — só pegos testando o parsing de verdade contra o backend rodando.
