# Transformação de Variáveis

> Busca em 2026-07-08 via OpenAlex. Escopo: transformar uma variável (já
> categorizada ou não) num formato mais útil ao modelo — WOE, encodings
> categóricos, transformações de potência (Box-Cox/Yeo-Johnson), scaling.
> Mesma ressalva de `categorizacao.md`: abstracts não vieram pela API
> (limitação do client), sínteses baseadas em conhecimento direto dos
> métodos — confirmar no link antes de citar formalmente.

## Panorama

Quatro famílias:
- **WOE (Weight of Evidence)**: transforma cada bin/categoria no log-odds
  do evento naquele grupo — a transformação canônica de scorecards, porque
  o coeficiente resultante da regressão logística vira diretamente
  interpretável em pontos de score.
- **Encoding de categóricas de alta cardinalidade**: target encoding,
  similarity encoding — quando há categorias demais para dummy/one-hot.
- **Transformações de potência**: Box-Cox, Yeo-Johnson — corrigem
  assimetria/heterocedasticidade antes de um modelo linear.
- **Scaling/normalização**: menos crítico para árvores/boosting, essencial
  para regularização (LASSO) e métodos baseados em distância.

## Papers-chave

1. **Regularized target encoding outperforms traditional methods in
   supervised machine learning with high cardinality features** — F.
   Pargent, F. Pfisterer, J. Thomas, B. Bischl (2022). Comparação empírica
   ampla de estratégias de target encoding (incl. regularização via CV
   interna e shrinkage Bayesiano) — mostra que a versão regularizada
   supera one-hot e target encoding "ingênuo" (sem regularização, que
   vaza informação do target e overfitta). Mesmo grupo de autores do
   paper de shadow-variable probing já sintetizado no lab — ver
   `shadow-variable-probing.md`. [Link](https://link.springer.com/content/pdf/10.1007/s00180-022-01207-6.pdf).

2. **Similarity encoding for learning with dirty categorical variables** —
   P. Cerda, G. Varoquaux, B. Kégl (2018). Para categorias "sujas" (erros
   de digitação, variantes de string da mesma categoria semântica — comum
   em dados reais, não em benchmarks limpos): codifica por similaridade de
   string em vez de igualdade exata. Base da biblioteca `dirty_cat`/`skrub`.
   [Link](https://link.springer.com/content/pdf/10.1007/s10994-018-5724-2.pdf).

3. **A Deep-Learned Embedding Technique for Categorical Features Encoding**
   (2021). Embeddings aprendidos (estilo NLP) para categóricas de altíssima
   cardinalidade — alternativa não-linear ao target encoding, custo maior
   de treino. [OpenAlex](https://openalex.org/W3195971125).

4. **Effective Methods of Categorical Data Encoding for Artificial
   Intelligence Algorithms** (2024). Survey recente comparando encodings
   (one-hot, target, ordinal, binary, hashing) — bom ponto de entrada para
   decidir qual usar por cenário. [OpenAlex](https://openalex.org/W4401702537).

5. **Survey on categorical data for neural networks** (2020). Foco em
   redes neurais especificamente — embeddings categóricos, entity
   embeddings (Guo & Berkhahn) — relevante se o lab expandir para deep
   learning tabular. [OpenAlex](https://openalex.org/W3020873385).

6. **The Box–Cox Transformation: Review and Extensions** — A. C. Atkinson,
   M. Riani, A. Corbellini (2021). Revisão moderna da transformação
   Box-Cox clássica (1964) — escolhe o expoente `λ` que mais aproxima a
   distribuição de uma normal, corrigindo assimetria. Discute extensões
   para dados com zeros/negativos (ponte direta para Yeo-Johnson).
   [Link](https://researchonline.lse.ac.uk/id/eprint/103537/2/Supplementary.pdf).

7. **Automatic robust Box–Cox and extended Yeo–Johnson transformations in
   regression** (2022). Versões robustas (menos sensíveis a outliers) das
   duas transformações — outliers podem distorcer a escolha do parâmetro
   ótimo se não tratados. [OpenAlex](https://openalex.org/W4281738175).

8. **Improving your data transformations: Applying the Box-Cox
   transformation** (2020). Texto aplicado/didático — bom para
   documentação interna de quando/como aplicar. [OpenAlex](https://openalex.org/W2118988523).

9. **Ordered quantile normalization: a semiparametric transformation built
   for the cross-validation era** (2019). Transforma qualquer variável para
   ter distribuição aproximadamente normal via rank + quantil — mais
   flexível que Box-Cox/Yeo-Johnson (não assume família paramétrica), mas
   perde interpretabilidade da escala original. [OpenAlex](https://openalex.org/W2953159213).

## Papers de contexto (crédito/scoring especificamente)

10. **Credit Scoring and the Availability, Price, and Risk of Small
    Business Credit** (2005). Contexto de negócio de por que WOE/scorecard
    dominam o setor (regulação, auditabilidade) — não é um paper de método,
    é o "porquê" institucional. [OpenAlex](https://openalex.org/W2171896830).

11. **Credit scoring models for the microfinance industry using neural
    networks: Evidence from Peru** (2012). Caso aplicado comparando
    abordagens em crédito fora do contexto WOE-tradicional — referência de
    contraste. [OpenAlex](https://openalex.org/W2059447090).

## Conexão com o acervo

- **WOE já é a convenção de nomenclatura do lab** (`_woe` em todos os
  datasets sintéticos e no dataset real `credito_real` após binning) — mas
  o lab ainda **não tem uma implementação própria de WOE**, só o nome. Essa
  é a lacuna mais óbvia a fechar no módulo `transformacao/`.
- **Anti-leakage crítico aqui**: WOE e target encoding calculados no
  dataset inteiro (sem separar fold) vazam a variável-resposta para dentro
  do preditor — a mesma regra "anti-leakage é lei" do `CLAUDE.md` do lab se
  aplica com força total nesta etapa, talvez mais do que em qualquer outra
  (é o erro mais comum e mais silencioso em pipelines de crédito reais).
- Regularização de target encoding (item 1) é diretamente análoga à lição
  do experimento de colinearidade
  (`docs/experimentos/colinearidade-stability-selection.md`): regularização
  malcalibrada quebra o método mesmo com sinal real forte — o mesmo cuidado
  de varrer a força de regularização antes de confiar cegamente se aplica
  a target encoding.
