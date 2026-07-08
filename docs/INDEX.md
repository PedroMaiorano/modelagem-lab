# INDEX — modelagem-lab

Mapa da base de conhecimento do lab.

## Referências (`docs/referencias/`)
- [sota-tracker-modelagem](referencias/sota-tracker-modelagem.md) — estado da arte: seleção de variáveis, modelos, AutoML, causal ML. **Coração do lab.**
- [apis-fontes-abertas](referencias/apis-fontes-abertas.md) — APIs acadêmicas abertas (arXiv, Semantic Scholar, OpenAlex, CrossRef, Europe PMC/PubMed): endpoints, limites, exemplos.

## Algoritmos Originais (`docs/algoritmos-originais/`)
- [pedro-wise-resumo](algoritmos-originais/pedro-wise-resumo.md) — lógica do Pedro_Wise, anti-padrões e plano de port (**pilar 1**).
- `Pedro_Wise_3.0.1.R` — cópia fiel do algoritmo R original.

## Literatura (`docs/literatura/`)
Wiki de técnicas documentadas — populada pelo `literature-scout`. Ver [README](literatura/README.md).
- [stability-selection](literatura/stability-selection.md) — meta-procedimento de estabilização de seleção de variáveis; achado do Faletto & Bien (2022) sobre falha com proxies correlacionados, conectado ao forward duplo do Pedro_Wise.
- [shadow-variable-probing](literatura/shadow-variable-probing.md) — critério de parada em single-fit via variáveis permutadas; sugestão concreta de melhoria para o critério de parada do port (evitar seleção de ruído como `x_ruido2_woe` na validação).

## Experimentos (`docs/experimentos/`)
- [pedro-wise-vs-alternativas](experimentos/pedro-wise-vs-alternativas.md) — Pedro_Wise vs. LASSO vs. stability selection no mesmo dataset sintético (gabarito conhecido). Achado central: LASSO/stability selection cravaram o modelo exato; o Pedro_Wise aceitou 1 variável de ruído por otimizar KS contra um split de teste fixo.

## Guias (`docs/guias/`)
- [fluxo-de-trabalho](guias/fluxo-de-trabalho.md) — como os 3 pilares e os agentes/skills se encaixam.

## Planos (`docs/planos/`)
- [modelagem-lab-config](planos/modelagem-lab-config.md) — decisões de arquitetura da configuração Claude Code deste lab.
