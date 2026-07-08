# Construção de Variáveis (Feature Engineering/Construction)

> Busca em 2026-07-08 via OpenAlex. Escopo: criar variáveis NOVAS a partir
> das originais — interações, razões, agregações, features aprendidas —
> antes de categorizar (`categorizacao.md`) ou transformar (`transformacao.md`)
> qualquer coisa. Mesma ressalva: abstracts não vieram pela API; sínteses de
> conhecimento direto, confirmar no link antes de citar formalmente.

## Panorama

Duas escolas:
- **Automática/exaustiva**: gera candidatas em massa (todas as
  razões/produtos/agregações possíveis) e deixa a seleção de variáveis
  (pilar 1 do lab) filtrar depois. Deep Feature Synthesis é o exemplo
  canônico.
- **Guiada por busca/aprendizado**: usa programação genética ou
  reinforcement learning para *procurar* combinações promissoras em vez de
  gerar tudo — mais cara por candidata, mas evita explosão combinatorial.

## Papers-chave

1. **Deep feature synthesis: Towards automating data science endeavors** —
   J. M. Kanter, K. Veeramachaneni (2015). Paper fundador da construção
   automática de features a partir de dados relacionais (múltiplas
   tabelas) — aplica operações de agregação (soma, média, contagem, etc.)
   recursivamente ao longo de relacionamentos entre tabelas. Base da
   biblioteca `featuretools`. [OpenAlex](https://openalex.org/W2182353144).

2. **Evaluation of a Tree-based Pipeline Optimization Tool for Automating
   Data Science** (2016, *TPOT*). Não é só construção de features — é
   AutoML de pipeline completo (incl. construção/seleção/modelo) via
   programação genética. Relevante como "onde a construção de variáveis se
   encaixa dentro de um pipeline AutoML maior". [OpenAlex](https://openalex.org/W2309832917).

3. **Genetic programming for multiple-feature construction on
   high-dimensional classification** (2019). Usa programação genética para
   construir múltiplas features simultaneamente (não uma de cada vez) —
   relevante para alta dimensão, onde construir feature-a-feature é caro.
   [OpenAlex](https://openalex.org/W2944258394).

4. **Genetic programming for feature construction and selection in
   classification on high-dimensional data** (2021). Trata construção e
   seleção como um problema conjunto (não duas etapas sequenciais) — ponto
   de discussão interessante para o lab: hoje construção/categorização/
   transformação/seleção são pilares SEPARADOS; este paper questiona se
   deveriam ser. [OpenAlex](https://openalex.org/W4240337670).

5. **Genetic Programming for Feature Selection and Feature Construction in
   Skin Cancer Image Classification** (2018). Aplicação em imagem — fora do
   domínio tabular do lab, mas mesma técnica de base. [OpenAlex](https://openalex.org/W2884209928).

6. **Improving Land Cover Classification Using Genetic Programming for
   Feature Construction** (2021). Outra aplicação de domínio (sensoriamento
   remoto) — confirma que GP para construção de features é técnica madura
   e transversal a domínios, não nicho de um problema só. [OpenAlex](https://openalex.org/W3159431528).

7. **Feature Engineering for Predictive Modeling Using Reinforcement
   Learning** (2018). RL para decidir QUAIS transformações/combinações
   aplicar — alternativa à busca genética, mais próxima em espírito ao
   `stats-advisor` do lab (um agente "decidindo" a estratégia) do que a
   uma busca cega. [OpenAlex](https://openalex.org/W2759903677).

8. **A Survey of Evaluating AutoML and Automated Feature Engineering Tools
   in Modern Data Science** (2025). Survey recente comparando ferramentas
   (featuretools, TPOT, AutoGluon, etc.) — bom ponto de entrada atualizado
   antes de escolher o que integrar no lab. [OpenAlex](https://openalex.org/W4409287257).

9. **Automated data processing and feature engineering for deep learning
   and big data applications: A survey** (2024). Survey com foco em
   big data/deep learning — cobertura mais ampla que o escopo tabular do
   lab, mas útil como referência de fronteira. [OpenAlex](https://openalex.org/W4390667445).

10. **Automated Machine Learning** (2019, livro/survey editado — Hutter,
    Kotthoff, Vanschoren). Referência-base de AutoML em geral (HPO, NAS,
    e construção/seleção de features como subproblemas) — ponto de entrada
    para quem quer o panorama completo antes de mergulhar em uma técnica
    específica. [OpenAlex](https://openalex.org/W4213308398).

## Papers de contexto (feature engineering aplicado a crédito)

11. **Machine learning for credit scoring: Improving logistic regression
    with non-linear decision-tree effects** (2021). Usa efeitos não-lineares
    extraídos de árvores como FEATURES construídas para alimentar de volta
    numa regressão logística — um padrão de "construção assistida por
    modelo" diretamente aplicável ao Pedro_Wise (poderia usar
    profundidade/splits de uma árvore para sugerir candidatas de
    interação). [OpenAlex](https://openalex.org/W3173725123).

12. **Integrated framework for profit-based feature selection and SVM
    classification in credit scoring** (2017). Combina construção+seleção
    orientada a lucro esperado (não só métrica estatística) — ecoa a
    filosofia do Pedro_Wise de otimizar métrica de negócio (KS), mas aqui é
    lucro direto. [OpenAlex](https://openalex.org/W2765458100).

## Conexão com o acervo

- **Construção é o pilar menos maduro dos quatro no lab hoje** — só tem
  esta ficha de literatura, nenhuma implementação. Escopo v1 sugerido:
  gerar candidatas simples e interpretáveis primeiro (razões entre
  variáveis relacionadas, ex. `PAYAMT1/BILLAMT1` no dataset
  `credito_real` = "proporção paga da fatura" — uma feature de negócio
  óbvia que NÃO existe nas 23 colunas originais), antes de qualquer busca
  automática tipo GP/RL — mais barato, mais interpretável, e testável
  imediatamente com o Pedro_Wise já existente.
- Item 4 (construção+seleção conjuntas) é um contraponto direto à
  arquitetura modular pedida para o lab — vale registrar a tensão: pilares
  separados são mais simples de testar isoladamente, mas podem perder
  interações que só uma busca conjunta acharia. Não resolvido aqui, só
  registrado.
- Item 11 conecta diretamente ao Pedro_Wise: construção de features
  guiada por árvore é um caminho natural de expansão do
  `algorithm-porter`/`model-builder` depois que o módulo `construcao/`
  existir.
