# Shadow-Variable Probing

> Busca em 2026-07-07 via OpenAlex e CrossRef (queries com "shadow variable" sozinho
> foram tomadas por astrofísica — "sombra do buraco negro M87" — e por sondas
> espaciais; refinado para "probing ... model-based boosting", termo específico
> da área). Semantic Scholar e arXiv indisponíveis nesta sessão (rate limit e
> timeouts persistentes — não é specific desse tópico, ver nota operacional no
> fim do arquivo).

## O que é / quando usar

Shadow-variable probing resolve o mesmo problema que stability selection, por um
caminho diferente e mais barato: **como decidir quando parar de adicionar
variáveis** num ajuste stepwise/boosting, sem precisar de reamostragem repetida
nem de tuning externo (CV/bootstrap) do número de iterações.

Ideia central (Thomas, Hepp, Mayr & Bischl, 2017): aumente o conjunto de dados
com cópias **permutadas aleatoriamente** das variáveis reais — as "shadow
variables", que por construção não têm relação real com `y`. Rode o ajuste
stepwise/boosting normalmente sobre dados reais + shadow. No momento em que uma
variável *shadow* seria selecionada, pare — isso sinaliza que o algoritmo está
prestes a começar a ajustar ruído. Resultado: seleção de variáveis **num único
fit**, sem separar dev/teste para escolher o ponto de parada.

Use quando: o custo de tuning por CV/bootstrap é proibitivo, ou quando se quer
uma régua de parada mais objetiva que "o KS parou de melhorar no conjunto de
teste" (que ainda pode super-ajustar ao ruído específico daquele split).

## Pressupostos e trade-offs (clássico vs. SOTA)

- Pressuposto chave: a permutação da shadow variable precisa realmente destruir
  toda relação com `y` — cuidado com variáveis com estrutura temporal/dependência,
  onde permutar ingenuamente pode ser insuficiente para "matar" o sinal (não
  discutido em profundidade no paper original; ponto de atenção para o lab).
- Comparado à stability selection: muito mais barato (1 fit vs. dezenas de
  refits em subamostras), mas dá uma garantia mais fraca — não há bound teórico
  de controle de falsos positivos tipo Meinshausen-Bühlmann/Shah-Samworth, é
  uma heurística validada empiricamente (competitiva em benchmark de alta
  dimensão e em 3 datasets de expressão gênica no paper original).
- Extensão relevante (Staerk & Mayr, 2021 — *Subspace Boosting*): em vez de
  1 variável por iteração de boosting, permite **base-learners multivariáveis**
  (atualizar várias variáveis juntas por iteração), com seleção do subespaço via
  critério de informação. Achado direto: esse ajuste multivariável ajuda
  **especialmente quando há alta correlação entre as variáveis-sinal** — o
  mesmo cenário de "proxies correlacionados de um fator latente" que aparece no
  achado do Faletto & Bien sobre stability selection (ver
  [`stability-selection.md`](stability-selection.md)). É o terceiro método
  independente na literatura que converge para o mesmo problema: seleção
  variável-a-variável falha ou fica subótima sob correlação; a solução recorrente
  é agrupar/atualizar em bloco.
- Extensão de nicho (Griesbach, Mayr & Bergherr, 2023): aplica boosting para
  alocar covariáveis entre sub-preditores de modelos conjuntos
  (longitudinal + tempo-até-evento) — relevante só se o lab entrar em dados de
  sobrevivência/longitudinais; não é central para o caso de uso atual.

## Papers-chave

1. **Probing for Sparse and Fast Variable Selection with Model-Based Boosting** —
   J. Thomas, T. Hepp, A. Mayr, B. Bischl (2017, *Computational and Mathematical
   Methods in Medicine*). Paper fundador do método — descrito acima. Testado
   contra stability selection num benchmark de classificação em alta dimensão
   (competitivo) e em 3 datasets de expressão gênica. [CrossRef](https://doi.org/10.1155/2017/1421409),
   preprint aberto no [arXiv (1702.04561)](https://arxiv.org/abs/1702.04561).
   *Já citado no SOTA tracker antes desta busca (fonte NCBI PMC) — esta ficha
   formaliza a síntese.*

2. **Randomized Boosting with Multivariable Base-Learners for High-Dimensional
   Variable Selection and Prediction** — C. Staerk, A. Mayr (2021, *BMC
   Bioinformatics*). Introduz Subspace/Random Subspace/Adaptive Subspace
   Boosting — base-learners com múltiplas variáveis por iteração, seleção via
   critério de informação com parada automática. Mostra ganho especificamente
   sob alta correlação entre covariáveis-sinal, com modelos mais esparsos e
   desempenho preditivo competitivo com lasso/elastic net (relaxado).
   [CrossRef](https://doi.org/10.1186/s12859-021-04340-z) — *BMC Bioinformatics
   é acesso aberto por padrão (não confirmado por API nesta busca).*

3. **Variable Selection and Allocation in Joint Models via Gradient Boosting
   Techniques** — C. Griesbach, A. Mayr, E. Bergherr (2023, *Mathematics*,
   MDPI). Estende boosting para alocar automaticamente covariáveis entre
   sub-preditores de modelos conjuntos longitudinal+sobrevivência. Nicho —
   registrado para referência futura, não aplicável ao escopo atual do lab.
   [CrossRef](https://doi.org/10.3390/math11020411) — *MDPI Mathematics é
   acesso aberto por padrão.*

## Conexão com o acervo (Pedro_Wise / seleção de variáveis)

- **Conexão direta e acionável**: o Pedro_Wise decide quando parar de adicionar
  variáveis comparando KS-dev/teste antes/depois de cada candidata — exatamente
  o tipo de decisão que shadow-variable probing resolve de forma mais barata e
  com menos risco de overfitting ao split específico. A validação numérica do
  port (`docs/algoritmos-originais/pedro-wise-resumo.md`, seção "Validação
  contra o R original") mostrou o algoritmo aceitando `x_ruido2_woe` — uma
  variável de **puro ruído** — só por acaso amostral. Shadow-variable probing
  foi desenhado especificamente para pegar esse tipo de caso: se `x_ruido2_woe`
  fosse testada contra uma cópia permutada de si mesma no mesmo fit, a
  probabilidade de a shadow "vencer" primeiro cresce à medida que o modelo se
  aproxima do limite do sinal real.
- **Sugestão concreta de trabalho futuro**: implementar `ShadowProbingMetric`
  ou, mais precisamente, um **critério de parada alternativo** em
  `python/pedro_wise/metrics.py` — não é uma métrica de score por candidata
  (a interface `Metric` atual), é uma regra de parada do laço em `selection.py`.
  Pode valer a pena revisar a interface `Metric`/`Level1Config` para acomodar
  isso como uma opção de parada plugável, adicional ao "score não melhorou".
- **Confirma o padrão que já estava emergindo com stability selection**: três
  fontes independentes (Faletto & Bien; Staerk & Mayr; e implicitamente o
  próprio Pedro_Wise via `forward_duplo`) convergem para a mesma conclusão —
  seleção variável-a-variável tem um ponto cego estrutural sob correlação, e a
  correção é sempre "considerar variáveis em grupo". Vale uma entrada própria
  no SOTA tracker consolidando isso como um princípio transversal, não um
  detalhe de um método específico.

## Nota operacional desta busca

Semantic Scholar retornou `429 Too Many Requests` de forma persistente nesta
sessão (mesmo após espera de 15s) — o limite de 100 req/5min sem chave parece
compartilhado por IP e a sessão anterior (busca de `stability-selection`) já
tinha consumido boa parte da cota. arXiv também deu `ReadTimeout` em duas
tentativas (rede, não rate limit — resposta HTTP 429 explícita em outra
tentativa). OpenAlex e CrossRef não têm esse problema (sem chave, sem
throttling perceptível) e cobriram a busca sozinhos desta vez. Se isso se
repetir, considerar aumentar o intervalo do `RateLimiter` do Semantic Scholar
acima de 3s ou obter uma chave gratuita (ver `docs/referencias/apis-fontes-abertas.md`).
