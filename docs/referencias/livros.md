# Livros de Referência

> Citações bibliográficas — título/autor/editora, e link para versão aberta
> quando existe uma (vários destes têm edição gratuita online dos próprios
> autores). Nunca baixar PDF pirata de livro fechado — se não houver versão
> aberta, a referência fica só bibliográfica, para compra/biblioteca.

## Scorecards / crédito (categorização + transformação + treinamento)

- **Siddiqi, N. (2017). *Credit Risk Scorecards: Developing and
  Implementing Intelligent Credit Scoring* (2nd ed.). Wiley.** — O livro-texto
  canônico do fluxo binning→WOE→regressão logística→scorecard que o
  Pedro_Wise automatiza. Referência obrigatória para calibrar o módulo
  `categorizacao/` e `transformacao/` contra a prática de mercado.

- **Anderson, R. (2007). *The Credit Scoring Toolkit: Theory and Practice
  for Retail Credit Risk Management and Decision Automation*. Oxford
  University Press.** — Cobertura mais ampla do ciclo de vida do modelo de
  crédito (não só a construção), incluindo monitoramento pós-implantação —
  fora do escopo atual do lab, mas relevante quando/se o lab tratar de
  monitoramento de modelo.

## Feature engineering / construção e transformação de variáveis

- **Zheng, A., & Casari, A. (2018). *Feature Engineering for Machine
  Learning: Principles and Techniques for Data Scientists*. O'Reilly.** —
  Cobre exatamente os 3 primeiros pilares do lab (categorização,
  transformação, construção) de forma prática e agnóstica de domínio.

- **Kuhn, M., & Johnson, K. (2019). *Feature Engineering and Selection: A
  Practical Approach for Predictive Models*. CRC Press.**
  **Versão aberta gratuita**: https://bookdown.org/max/FES/ — os mesmos
  autores de *Applied Predictive Modeling* disponibilizaram o livro inteiro
  online. Prioridade de leitura alta — cobre categorização + transformação
  + seleção de forma integrada, com código em R (paralelo direto ao
  pilar R↔Python do lab).

- **Kuhn, M., & Johnson, K. (2013). *Applied Predictive Modeling*.
  Springer.** — Precursor do livro acima, mais focado em modelagem
  preditiva geral (pré-processamento, tuning, comparação de modelos).

## Modelagem estatística / seleção de variáveis (treinamento — pilar 1)

- **Hastie, T., Tibshirani, R., & Friedman, J. (2009). *The Elements of
  Statistical Learning* (2nd ed.). Springer.**
  **Versão aberta gratuita**: https://hastie.su.domains/ElemStatLearn/ —
  cobre regularização (LASSO/ridge/elastic net), boosting, e a base
  teórica de quase tudo já citado em `sota-tracker-modelagem.md`.

- **James, G., Witten, D., Hastie, T., & Tibshirani, R. (2021). *An
  Introduction to Statistical Learning* (2nd ed., com Python). Springer.**
  **Versão aberta gratuita**: https://www.statlearning.com/ — versão mais
  acessível do livro acima, com edição em Python (`ISLP`) além de R. Melhor
  ponto de entrada que o ESL para quem quer prática rápida.

- **Bühlmann, P., & van de Geer, S. (2011). *Statistics for
  High-Dimensional Data: Methods, Theory and Applications*. Springer.** —
  Base teórica formal de stability selection e boosting em alta dimensão
  (Bühlmann é coautor do paper fundador de stability selection já
  sintetizado em `docs/literatura/stability-selection.md`).

## AutoML / construção automática

- **Hutter, F., Kotthoff, L., & Vanschoren, J. (Eds.) (2019). *Automated
  Machine Learning: Methods, Systems, Challenges*. Springer.**
  **Versão aberta gratuita**: https://automl.org/book/ — já catalogado como
  paper em `docs/literatura/construcao-variaveis.md` (é tecnicamente um
  livro editado, listado nos dois lugares por ser referência central de
  ambos os temas).

## Como usar esta lista

- Antes de implementar qualquer técnica clássica de categorização/
  transformação, checar se Siddiqi ou Kuhn & Johnson já documentam a
  prática de mercado — evita reinventar convenções que scorecard/ML
  profissionais já usam.
- Ao adicionar um livro novo: só citação bibliográfica + link se houver
  versão aberta legítima (site do próprio autor/editora, não agregador de
  PDF pirata). Se não houver versão aberta, registrar mesmo assim (só sem
  link de download).
