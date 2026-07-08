# Categorização / Discretização de Variáveis

> Busca em 2026-07-08 via OpenAlex e CrossRef. Escopo: transformar uma
> variável contínua em faixas/categorias (binning) — a etapa central de
> qualquer scorecard tradicional e um pré-processamento comum antes do WOE
> (ver `transformacao.md`). Nota: nenhum destes registros trouxe abstract via
> a API (limitação conhecida do client OpenAlex, documentada em
> `scraping/openalex_client.py` — não parseia `abstract_inverted_index`);
> as sínteses abaixo vêm de conhecimento direto sobre os métodos, não de
> abstract copiado. Confirme o abstract no link antes de citar formalmente.

## Panorama

Três famílias de discretização:
- **Não-supervisionada**: equal-width, equal-frequency (quantis) — baseline,
  ignora a variável-resposta.
- **Supervisionada estatística**: usa `y` para decidir os cortes — ChiMerge,
  CAIM/ur-CAIM, MODL/Khiops, discretização baseada em AUC.
- **Supervisionada por otimização**: formula o binning como problema de
  otimização com restrições (monotonicidade, tamanho mínimo de bin) —
  OptBinning é o estado da arte prático aqui.

## Papers-chave

1. **Optimal binning: mathematical programming formulation** — G.
   Navas-Palencia (2020). Formula o binning ótimo (com restrição de
   monotonicidade da taxa de evento — essencial para scorecards
   interpretáveis) como programação matemática (MIP/CP). Base do pacote
   `optbinning` (Python), hoje o padrão prático de mercado para binning em
   crédito. [arXiv](https://arxiv.org/pdf/2001.08025).

2. **MODL: A Bayes optimal discretization method for continuous attributes**
   — M. Boullé (2006). Discretização Bayes-ótima: escolhe o número e a
   posição dos cortes maximizando a probabilidade a posteriori do modelo de
   discretização, sem parâmetro de significância a ajustar (diferença chave
   vs. ChiMerge/chi-quadrado clássicos, que exigem threshold).
   [OpenAlex](https://openalex.org/W2001592424).

3. **Khiops: A Statistical Discretization Method of Continuous Attributes**
   — M. Boullé (2004). Precursor do MODL — mesma família Bayes-ótima,
   restrita a discretização em intervalos. [OpenAlex](https://openalex.org/W2133121564).

4. **ur-CAIM: improved CAIM discretization for unbalanced and balanced data**
   — A. Cano, D. T. Nguyen, S. Ventura, K. J. Cios (2014). Estende o CAIM
   (Class-Attribute Interdependence Maximization) original para dados
   desbalanceados — relevante para crédito, onde o evento (inadimplência) é
   sempre minoritário. [OpenAlex](https://openalex.org/W2100048438).

5. **Ameva: An autonomous discretization algorithm** (2008). Discretização
   supervisionada baseada em medida de contingência análoga ao CAIM, com
   critério de parada automático (não precisa fixar número de bins a priori).
   [OpenAlex](https://openalex.org/W2071332125).

6. **LAIM discretization for multi-label data** (2015). Extensão do CAIM
   para problemas multi-rótulo — fora do escopo direto do lab (y binário),
   registrado por completude conceitual da família CAIM.
   [OpenAlex](https://openalex.org/W2191619632).

7. **Improved Use of Continuous Attributes in C4.5** — J. R. Quinlan (1996).
   O binning "de dentro de uma árvore de decisão": corte recursivo por
   ganho de informação. Base conceitual de qualquer discretização
   tree-based (inclusive uma alternativa simples ao MDLP formal).
   [OpenAlex](https://openalex.org/W1833977909).

8. **A discretization method based on maximizing the area under ROC curve**
   (2013). Em vez de entropia/qui-quadrado, escolhe cortes que maximizam
   AUC diretamente — conecta a discretização à métrica de avaliação final,
   ideia que ecoa a filosofia do próprio Pedro_Wise (otimizar a métrica de
   negócio, não um proxy estatístico). [OpenAlex](https://openalex.org/W2119745037).

9. **Discretization for naive-Bayes learning: managing discretization bias
   and variance** (2008). Discute o trade-off viés/variância do número de
   bins — relevante mesmo fora do contexto Naive Bayes: poucos bins perdem
   sinal (viés), muitos bins overfittam em faixas raras (variância).
   [OpenAlex](https://openalex.org/W2113001205).

10. **Proportional k-Interval Discretization for Naive-Bayes Classifiers**
    (2001). Regra prática simples para escolher `k` (número de bins)
    proporcional ao tamanho da amostra — heurística útil para um baseline
    rápido. [OpenAlex](https://openalex.org/W2115870505).

11. **Discretization of continuous features in clinical datasets** (2012).
    Aplicação em dados clínicos (domínio de alto risco, interpretabilidade
    importa) — paralelo direto ao crédito. [OpenAlex](https://openalex.org/W2184549704).

12. **Learning Discrete Bayesian Networks from Continuous Data** (2017).
    Discretização como pré-requisito para redes Bayesianas discretas —
    fora do escopo imediato, mas mostra a generalidade do problema além de
    classificação supervisionada simples. [OpenAlex](https://openalex.org/W2964209429).

13. **Induction of Decision Trees** — J. R. Quinlan (1986, *ID3*). A raiz
    histórica de toda discretização tree-based subsequente (incluindo o
    item 7). Citação obrigatória de contexto. [OpenAlex](https://openalex.org/W2149706766).

## Conexão com o acervo

- O binning é o passo que normalmente **precede** o WOE (`transformacao.md`)
  — WOE é calculado *sobre* os bins, não sobre a variável contínua crua.
  Um módulo `categorizacao/` no lab deve produzir bins que alimentam
  diretamente o módulo `transformacao/`.
- **Monotonicidade importa mais aqui do que em ML genérico**: um scorecard
  onde o risco não é monotônico na faixa de renda (ex.: risco sobe, desce,
  sobe de novo) é vendido para negócio como "não faz sentido", mesmo que
  estatisticamente válido. OptBinning (item 1) trata isso como restrição de
  primeira classe — é o motivo de ser o padrão prático, não só acadêmico.
- Conecta com a semântica de "base" do Pedro_Wise: uma variável `renda`
  pode ter várias VERSÕES de binning candidatas (ex.: `renda_bin5`,
  `renda_bin10`) — a mesma lógica de "só uma versão por vez no modelo" que
  já existe em `pedro_wise.base.extrair_base` se aplica aqui.
