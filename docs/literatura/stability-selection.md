# Stability Selection

> Busca realizada em 2026-07-07 via `arXiv`, `Semantic Scholar` e `OpenAlex`
> (todas fontes abertas). `CrossRef` retornou majoritariamente teses/preprints
> não específicos ao tópico — descartados como ruído.

## O que é / quando usar

Stability selection não é um método de seleção por si só — é um **meta-procedimento**
que estabiliza qualquer método de seleção de variáveis existente (lasso, stepwise,
boosting...). Ideia central: aplique o método base repetidamente em subamostras
aleatórias dos dados e mantenha só as variáveis selecionadas com **alta frequência**
através das repetições. Isso dá controle de taxa de falsos descobrimentos com
garantias de amostra finita, sem depender de suposições fortes sobre o método base.

Use quando: alta dimensão, necessidade de controlar falsos positivos de forma
transparente, ou quando o método de seleção base (ex.: lasso, ou o próprio
Pedro_Wise) é instável entre reamostragens.

## Pressupostos e trade-offs (clássico vs. SOTA)

- **Clássico (Meinshausen & Bühlmann)**: requer só que o método base seja "razoável";
  não precisa das condições de consistência do lasso original valerem.
- **Melhoria de erro (Shah & Samworth)**: "complementary pairs stability selection"
  aperta os limites de controle de erro sem exigir suposições extras de
  exchangeability — resultado mais forte que o original.
- **Extensão de eixo duplo (Beinrucker, Dogan & Blanchard)**: subamostra
  observações **e** covariáveis simultaneamente, generalizando a teoria original
  (que só cobria meio-a-meio de observações) para subamostras de tamanho arbitrário.
- **Achado importante para dados correlacionados (Faletto & Bien, 2022)**: stability
  selection com lasso puro **pode falhar completamente** quando há proxies altamente
  correlacionados de um fator latente importante — o lasso escolhe arbitrariamente
  um proxy por subamostra, nenhum atinge frequência alta, e a variável correta nunca
  é selecionada. Resultado: pior desempenho preditivo que o lasso simples. A correção
  proposta (*cluster stability selection*) exige agrupar variáveis correlacionadas
  antes de aplicar o procedimento.
- Trade-off geral: custo computacional (múltiplos refits) e a escolha de threshold
  de frequência/número de subamostras não é trivial — mais um hiperparâmetro.

## Papers-chave

1. **Stability Selection** — N. Meinshausen, P. Bühlmann (2008/2010, *JRSS-B*).
   Paper fundador. Introduz o procedimento geral (subsample + selection algorithm +
   frequência de seleção), prova consistência do lasso randomizado sob stability
   selection mesmo quando as condições do lasso original falham, demonstra em
   seleção de variáveis e grafos Gaussianos. [Semantic Scholar](https://www.semanticscholar.org/paper/73a8a205a37f0169e89d3f0819a8ec36b39d3d2a).
   *PDF aberto reportado pela fonte (Oxford Academic) — confirmar acesso antes de baixar em massa.*

2. **Variable Selection with Error Control: Another Look at Stability Selection** —
   R. D. Shah, R. Samworth (2011/2013, *JRSS-B*). Introduz "complementary pairs
   stability selection": deriva limites mais apertados no número esperado de
   variáveis de baixa probabilidade incluídas e de alta probabilidade excluídas,
   sem suposições extras sobre o modelo. Melhora direta sobre o paper original — é
   a referência a citar quando se quer controle de erro mais forte.
   [Semantic Scholar](https://www.semanticscholar.org/paper/cf6da91d65cf8f01c4708fd95044e55fa495478c).
   *Mesmo aviso de PDF acima.*

3. **Extensions of Stability Selection Using Subsamples of Observations and
   Covariates** — A. Beinrucker, Ü. Dogan, G. Blanchard (2014, *Machine Learning*).
   Generaliza a teoria de Meinshausen & Bühlmann (que assumia meio-a-meio de
   observações) para subamostras de tamanho arbitrário, e propõe subamostrar
   também as **covariáveis** candidatas, não só as observações. Valida em dados
   sintéticos e reais. [PDF aberto (arXiv)](https://arxiv.org/pdf/1407.4916).

4. **Cluster Stability Selection** — G. Faletto, J. Bien (2022). Mostra
   formalmente (primeiro resultado do tipo, segundo os autores) que stability
   selection com lasso puro pode **falhar** sob proxies correlacionados de um
   fator latente — ver seção acima. Propõe combinar variáveis por cluster
   (média ponderada pela frequência de seleção dentro do cluster) antes de
   aplicar o procedimento; generaliza as garantias teóricas de Meinshausen &
   Bühlmann e Shah & Samworth para o caso com clusters.
   [Semantic Scholar](https://www.semanticscholar.org/paper/c6a8d9ee0fc89a3eb2c4af0c411d064cf5928789).
   *PDF aberto não confirmado por esta fonte — buscar diretamente no arXiv se necessário.*

5. **Stability Selection for Genome-Wide Association** — D. H. Alexander, K. Lange
   (2011, *Genetic Epidemiology*). Aplicação em GWAS: usa stability selection para
   checar se regiões genômicas originalmente sinalizadas se sustentam, e se
   descobre regiões novas. Exemplo de uso aplicado em domínio de alta dimensão
   real (biomédico) — ilustra o procedimento fora do contexto puramente teórico.
   *PDF aberto não confirmado por esta fonte (journal fechado por padrão) — não
   incluir nesta wiki sem verificar acesso aberto.*

## Conexão com o acervo (Pedro_Wise / seleção de variáveis)

- O Pedro_Wise é um **wrapper stepwise guloso** — exatamente o tipo de método
  "instável entre reamostragens" que stability selection foi desenhado para
  estabilizar. Um experimento natural do lab: rodar `run_pedro_wise` como o
  "método base" dentro de um laço de subamostragem (bootstrap ou subsample sem
  reposição) e reportar frequência de seleção por variável — dá uma medida de
  robustez que o algoritmo original nunca teve.
- **Achado do Faletto & Bien é diretamente relevante ao design do port.** O
  Pedro_Wise já tem uma noção de agrupamento — a semântica de "base"
  (`extrair_base`, `docs/algoritmos-originais/pedro-wise-resumo.md`) impede duas
  *transformações da mesma variável* de coexistirem no modelo. Mas isso é
  diferente do problema que Faletto & Bien descrevem: variáveis com bases
  **diferentes** que são correlacionadas por compartilhar um fator latente comum
  (exatamente o cenário que `tests/test_level2.py::test_forward_duplo_encontra_par_sinergico...`
  já exercita no port, mostrando que o **forward duplo** do próprio Pedro_Wise já
  lida bem com esse caso ao testar pares conjuntamente). Vale registrar essa
  distinção explicitamente: agrupamento por "base" (mesma variável, versão
  diferente) vs. agrupamento por "cluster" (variáveis diferentes, correlacionadas)
  são mecanismos complementares, não substitutos.
- Atualiza `docs/referencias/sota-tracker-modelagem.md` §1 "Robustez / controle de
  falsos positivos": adicionar a referência ao achado de cluster stability
  selection como nota de cautela ao recomendar stability selection sozinha em
  dados com clusters de variáveis correlacionadas.

## Papers descartados nesta busca (ruído)

- "False discovery and its control in low rank estimation" (Taeb et al., 2018) —
  contexto de matrizes de baixo posto, não seleção de variáveis em GLM/tabular;
  fora do escopo direto do lab.
- "Comment" (Barut & Wang, 2015) — sem abstract recuperável; provavelmente um
  comentário/discussão de outro paper, não uma contribuição própria.
- Resultados do CrossRef para a mesma query retornaram majoritariamente
  teses/dissertações e preprints não focados especificamente em stability
  selection (ex.: "whitening elastic net", "particle swarm feature selection")
  — descartados por relevância baixa.
