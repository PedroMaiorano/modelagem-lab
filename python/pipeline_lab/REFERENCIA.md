# pipeline_lab — Referência Completa

> Toda função pública de `pipeline_lab`, todos os parâmetros, e a passagem
> de literatura que justifica cada decisão de design. Fonte primária: os
> docstrings dos módulos em `python/pipeline_lab/` e do core que eles
> empacotam (`agregacao_temporal`, `interacao`, `categorizacao`,
> `transformacao`, `construcao`, `preselecao`, `pedro_wise`). As citações
> vêm da base de literatura já curada em `docs/literatura/` — não são
> adicionadas aqui, só referenciadas ao parâmetro/decisão que justificam.

## Sumário

1. [Filosofia e convenções](#1-filosofia-e-convenções)
2. [`divisao`](#2-divisao)
3. [`construcao`](#3-construcao)
4. [`esfera1`](#4-esfera1)
5. [`esfera2`](#5-esfera2)
6. [`categorizar`](#6-categorizar)
7. [`preselecao`](#7-preselecao)
8. [`treinamento`](#8-treinamento)

---

## 1. Filosofia e convenções

`pipeline_lab` é uma coleção de **funções soltas** (não uma API fluente/
orientada a objeto) — cada etapa recebe DataFrames e devolve DataFrames
novos, nunca muta o original, nunca lê/escreve disco, nunca importa
FastAPI. Isso permite plugar um `pandas.DataFrame` qualquer e escolher só
os módulos que fazem sentido para o seu caso, na ordem:

```
divisao → construcao (opcional) → esfera1 (opcional) → esfera2 (opcional)
→ categorizar → preselecao (opcional) → treinamento
```

**Convenção de coluna-alvo**: a partir de `divisao`, a variável resposta
deve se chamar `"y"` em `df_dev`/`df_teste` — todas as etapas seguintes
acessam `df["y"]` diretamente. `dividir_por_amostra`/`dividir_aleatorio`
aceitam `coluna_y` para fazer esse rename automaticamente.

**Anti-leakage por construção**: toda etapa que "ajusta" algo a partir de
`y` (WOE, tabela de bins monotônicos, regras de interação) faz isso **só em
dev**, e reaplica a mesma tabela/regra em teste sem reajustar — nunca
recalcula usando o `y` de teste. É o mesmo padrão fit/transform do
scikit-learn, e é a lei mais repetida em toda a base de literatura do lab
(ver nota de anti-leakage em `docs/literatura/transformacao.md`, seção
"Conexão com o acervo").

**Convenção de "base"**: uma variável crua pode ter várias versões
(`idade_woe`, `idade_log`, `idade_bin`) — todas compartilham o mesmo
prefixo semântico ("base"). O Pedro_Wise (`treinamento`) usa isso para
nunca deixar duas versões da mesma variável coexistirem no modelo (ver
`docs/algoritmos-originais/pedro-wise-resumo.md`, seção "Conceito de
'base'").

---

## 2. `divisao`

Divide um DataFrame em `(df_dev, df_teste)`. Não depende de nenhuma etapa
anterior — é sempre o primeiro passo.

### `dividir_por_amostra(df, coluna_amostra, valores_dev, valores_teste, coluna_y=None)`

Split por uma coluna de amostra que **já existe** no seu dataframe — não
assume nomes fixos tipo "dev"/"teste": você diz quais rótulos contam como
dev e quais contam como teste.

| Parâmetro | Tipo | Default | Explicação |
|---|---|---|---|
| `df` | `DataFrame` | — | Dataframe completo, ainda não dividido. |
| `coluna_amostra` | `str` | — | Nome da coluna que identifica a amostra de cada linha (ex.: `"split"`, `"amostra"`). Valores livres — `"DES"/"OOT"`, `"train"/"val"`, `"treino"/"teste"`, o que já vier na sua fonte. |
| `valores_dev` | `list[str]` | — | Quais valores de `coluna_amostra` contam como desenvolvimento. |
| `valores_teste` | `list[str]` | — | Quais valores contam como teste. Linhas com valor fora das duas listas são **descartadas** (não aparecem em nenhum dos dois retornos) — útil para uma terceira amostra tipo "validação" que você não quer usar agora. |
| `coluna_y` | `str \| None` | `None` | Se passado, renomeia essa coluna para `"y"` antes de dividir — evita um `.rename` manual antes de cada chamada seguinte do pipeline. |

### `dividir_aleatorio(df, proporcao_teste=0.5, semente=42, coluna_y=None)`

Split aleatório simples — embaralha e corta. Use quando não há coluna de
amostra pré-definida.

| Parâmetro | Tipo | Default | Explicação |
|---|---|---|---|
| `df` | `DataFrame` | — | Dataframe completo. |
| `proporcao_teste` | `float` | `0.5` | Fração das linhas que vai para teste. |
| `semente` | `int` | `42` | `random_state` — garante que o mesmo dataframe sempre produz o mesmo split (reprodutibilidade). |
| `coluna_y` | `str \| None` | `None` | Ver acima. |

---

## 3. `construcao`

Razões e diferenças **interpretáveis** entre pares de variáveis
relacionadas — ex.: `pago / fatura` = "proporção paga da fatura", uma
feature de negócio óbvia que não existe nas colunas originais.

**Escopo deliberadamente mínimo** (não é busca automática tipo Deep
Feature Synthesis ou programação genética) — ver
`docs/literatura/construcao-variaveis.md`, seção "Conexão com o acervo":
construção é o pilar menos maduro do lab, e a escolha de v1 foi gerar
candidatas simples e interpretáveis primeiro, mais barato e testável
imediatamente contra o Pedro_Wise, em vez de gerar tudo e deixar a
pré-seleção filtrar depois (a escola "automática/exaustiva" descrita no
paper fundador — **Kanter & Veeramachaneni, 2015**, *Deep Feature
Synthesis: Towards automating data science endeavors* — que aplica
operações de agregação recursivamente sobre relações entre tabelas; base
da biblioteca `featuretools`).

Um paralelo direto em crédito: **Dumitrescu et al., 2021** (*Machine
learning for credit scoring: Improving logistic regression with
non-linear decision-tree effects*) usa efeitos extraídos de árvores como
features construídas de volta para uma regressão logística — o mesmo
espírito de "construção assistida" que `esfera2` (RuleFit-style) aplica
depois de `construcao` no funil.

### `construir_razao(numerador, denominador, nome, epsilon=1e-6)`

| Parâmetro | Tipo | Default | Explicação |
|---|---|---|---|
| `numerador` | `Series` | — | Coluna do numerador. |
| `denominador` | `Series` | — | Coluna do denominador. |
| `nome` | `str` | — | Nome da série resultante. |
| `epsilon` | `float` | `1e-6` | Substitui denominador exatamente zero (mantém o sinal no resto — só evita divisão por zero literal). Comum em variáveis monetárias reais (ex.: fatura=0). |

### `construir_diferenca(a, b, nome)`

`a - b` — útil para variáveis na mesma unidade (ex.: fatura mês atual menos
fatura mês anterior = "variação de fatura"). Sem parâmetros de
configuração além dos nomes das colunas.

### `construir_razoes_em_lote(df, pares, epsilon=1e-6)`

| Parâmetro | Tipo | Default | Explicação |
|---|---|---|---|
| `df` | `DataFrame` | — | Dataframe de origem. |
| `pares` | `list[tuple[str, str, str]]` | — | Lista de `(numerador, denominador, nome)` — aplica `construir_razao` para cada tripla. |
| `epsilon` | `float` | `1e-6` | Ver acima. Retorna só as colunas construídas — combine com `pd.concat([df, resultado], axis=1)`. |

---

## 4. `esfera1`

Agregação temporal (agregação "comportamental"/behavioral scoring) — a
partir de um painel (chave + tempo + variável observada mês a mês),
constrói primitivas de janela móvel (máximo, média, mínimo,
desvio-padrão, tendência) e devolve uma linha por chave, pronta pra
entrar no funil.

Catálogo de primitivas inspirado no vocabulário de agregação do **Deep
Feature Synthesis** (Kanter & Veeramachaneni, 2015 — mesma referência de
`construcao`) — sem adotar a biblioteca inteira, só o vocabulário relevante
para painéis de crédito mensal.

**Garantia sem look-ahead**: cada linha de saída usa só observações até e
incluindo o próprio período — nunca dados futuros da mesma chave. É o que
torna essas features seguras de usar num modelo de scoring (senão vazaria
informação do futuro para o ponto de observação).

**Preservação de split**: `aplicar` agrega `df_dev`/`df_teste`
**separadamente** — nunca junta as duas bases para agregar e depois
re-divide. Misturar dev/teste antes de agregar contaminaria a fronteira
temporal do split.

### `agregar(df, chave, coluna_tempo, colunas_valor, janelas)`

Core de agregação, sem split — uma chamada por base (dev ou teste).

| Parâmetro | Tipo | Default | Explicação |
|---|---|---|---|
| `df` | `DataFrame` | — | Painel: uma linha por (chave, tempo). |
| `chave` | `str` | — | Coluna que identifica a entidade (ex.: `id_cliente`). |
| `coluna_tempo` | `str` | — | Coluna ordenável por chave (safra/mês/data). |
| `colunas_valor` | `list[str]` | — | Quais colunas numéricas agregar (ex.: `dias_atraso`, `valor_transacao`). |
| `janelas` | `list[int]` | — | Tamanhos de janela móvel em períodos (ex.: `[3, 6, 12]`) — gera um conjunto de primitivas por janela. |

Retorna `(df_agregado, colunas_geradas)`.

### `aplicar(df_dev, df_teste, chave, coluna_tempo, colunas_valor, janelas)`

Wrapper que chama `agregar` separadamente em dev e teste (preservação de
split, ver acima). Mesmos parâmetros de `agregar`, duplicados para as duas
bases. Retorna `(df_dev_agregado, df_teste_agregado, colunas_geradas)`.

---

## 5. `esfera2`

Descoberta de interação — **RuleFit-style** (**Friedman & Popescu, 2008**,
*Predictive learning via rule ensembles*, Annals of Applied Statistics):
treina um ensemble de árvores rasas (`GradientBoostingClassifier`) sobre as
candidatas já construídas, extrai os caminhos raiz-folha como regras de
interação ("tendência alta E severidade alta"), e devolve as regras como
candidatas avaliáveis para o funil.

**Diferença deliberada do RuleFit original**: no paper, as regras
extraídas das árvores viram termos de uma regressão com penalização L1
(Lasso) que decide os pesos finais. Aqui as regras viram colunas 0/1 que
entram no funil normal (categorização → pré-seleção → Pedro_Wise) — quem
decide o que fica no modelo final continua sendo a busca stepwise do
Pedro_Wise, não uma regressão L1 própria. Mantém a esfera 2 desacoplada da
seleção final.

### `transformar_categoricas_woe(dev, teste, colunas_x, colunas_categoricas=None)`

Pré-processamento interno: o `GradientBoostingClassifier` só aceita entrada
numérica, então colunas categóricas (texto, ou um código numérico sem
ordem real) são WOE-codificadas antes de entrar na árvore — um corte
`<=`/`>` sobre WOE faz sentido (é uma escala de log-odds); sobre um código
categórico arbitrário, não.

| Parâmetro | Tipo | Default | Explicação |
|---|---|---|---|
| `dev` | `DataFrame` | — | Base de desenvolvimento (WOE ajustado aqui). |
| `teste` | `DataFrame` | — | Base de teste (WOE só reaplicado, nunca reajustado — anti-leakage). |
| `colunas_x` | `list[str]` | — | Candidatas a entrar na árvore. |
| `colunas_categoricas` | `list[str] \| None` | `None` | Quais marcar como categóricas explicitamente. Colunas de texto (dtype não-numérico) em `colunas_x` são tratadas como categóricas automaticamente, mesmo sem estar aqui. |

Esse é um encoding "ingênuo" (WOE sem regularização/shrinkage) — a
literatura de encoding de alta cardinalidade (**Pargent, Pfisterer,
Thomas & Bischl, 2022**, *Regularized target encoding outperforms
traditional methods...*) mostra que versões regularizadas do target
encoding superam a versão ingênua, que pode vazar informação do target e
overfittar. Ponto de atenção registrado em
`docs/literatura/transformacao.md` — ainda não implementado aqui, já que o
WOE final que o modelo vê (etapa `categorizar`) é ajustado só em dev, o
mesmo cuidado anti-leakage do resto do lab.

### `aplicar(df_dev, df_teste, colunas_categoricas=None, profundidade_maxima=2, n_arvores=60, min_suporte=0.02, max_suporte=0.5, max_regras=10, permitir_cruzamento_entre_bases=True, proporcao_variaveis_por_split=None, iv_minimo=0.02)`

| Parâmetro | Tipo | Default | Explicação |
|---|---|---|---|
| `df_dev`, `df_teste` | `DataFrame` | — | Bases de entrada (colunas originais, não WOE-codificadas — a codificação interna é só para alimentar a árvore). |
| `colunas_categoricas` | `list[str] \| None` | `None` | Ver `transformar_categoricas_woe`. |
| `profundidade_maxima` | `int` | `2` | Profundidade das árvores do ensemble — controla o tamanho máximo de uma regra (nº de condições). Análogo ao parâmetro de profundidade em qualquer GBM raso do estilo RuleFit. |
| `n_arvores` | `int` | `60` | Número de árvores no `GradientBoostingClassifier` — mais árvores, mais candidatas de regra extraídas (antes da deduplicação/filtro). |
| `min_suporte` | `float` | `0.02` | Suporte mínimo (fração de linhas que satisfaz a regra) — descarta regras quase nunca verdadeiras, superajustadas a poucos casos. |
| `max_suporte` | `float` | `0.5` | Suporte máximo — descarta regras quase sempre verdadeiras, pouco informativas (viram uma constante disfarçada). |
| `max_regras` | `int` | `10` | Teto de regras candidatas devolvidas após os filtros. |
| `permitir_cruzamento_entre_bases` | `bool` | `True` | Se `False`, restringe regras a combinarem só primitivas da MESMA variável bruta (ex.: `atraso_tendencia_3m` com `atraso_maximo_3m`, nunca com `renda_tendencia_3m`) — útil quando regra de negócio não quer misturar domínios numa condição só (fica difícil de auditar). |
| `proporcao_variaveis_por_split` | `float \| None` | `None` | Fração de variáveis candidatas consideradas em cada split da árvore (equivalente a `max_features` do sklearn) — injeta aleatoriedade extra entre árvores, útil para diversificar as regras extraídas. |
| `iv_minimo` | `float` | `0.02` | Limiar de estabilidade: só regras com **IV de teste** >= esse valor viram coluna. Nunca o IV de dev, que já foi usado para escolher a regra em `extrair_candidatas` e está inflado por construção (mesmo raciocínio de `avaliar_estabilidade`, ver `interacao/estabilidade.py`). |

Retorna `(df_dev, df_teste, colunas_geradas)` — as colunas de regra (0/1)
concatenadas às tabelas originais (não às WOE-codificadas internamente).

---

## 6. `categorizar`

Categorização (binning monotônico) + WOE — sempre a **última** etapa antes
da pré-seleção/treinamento, porque é aqui que as versões alternativas de
cada variável (`_woe`, `_log`, `_bin`, etc.) nascem.

**Por que Esfera 2 vem antes**: as transformações de potência só existem a
partir daqui — nesse ponto do funil o GBM da Esfera 2 nunca viu `idade` e
`idade_log` ao mesmo tempo, então não precisa de filtro extra para evitar
regra redundante entre escalas da mesma variável.

### `categorizar_e_transformar(df_dev, df_teste, gerar_transformacoes_potencia=True, gerar_bin_ordinal=True, ao_processar_coluna=None)`

Para cada coluna (exceto `y`):

- **Numérica contínua** (`nunique > 2`): binning monotônico primeiro
  (`bins_monotonicos` — merge guloso que força a taxa de evento a ser
  monotônica entre bins adjacentes; versão pragmática, não ótima via MIP,
  da ideia central do **OptBinning** — **Navas-Palencia, 2020**, *Optimal
  binning: mathematical programming formulation*, hoje o padrão prático de
  mercado para binning em crédito). Monotonicidade importa mais aqui do
  que em ML genérico: um scorecard onde o risco não é monotônico na faixa
  de renda é rejeitado por negócio mesmo que estatisticamente válido (ver
  `docs/literatura/categorizacao.md`, seção "Conexão com o acervo").
- **Categórica/binária** (texto, ou numérica com só 2 valores — ex.: uma
  flag 0/1 de regra da Esfera 2): sem binning, cada valor já é o "bin".
  Antes da correção de 2026-07, colunas binárias eram descartadas
  silenciosamente aqui (`bins_monotonicos` numa coluna de 2 valores gera
  só 2 edges, insuficiente para discretizar) — bug real corrigido, testado
  em `app/backend/test_logica_categorizacao.py`.

Depois do binning: `ajustar_woe` (**Siddiqi**, *Credit Risk Scorecards* —
convenção de sinal `WOE = ln(%não-evento / %evento)`, positivo quando o
bin tem mais "bons pagadores" relativo à distribuição total, a mais comum
em scorecards de crédito) ajustado **só em dev**, reaplicado em teste.

| Parâmetro | Tipo | Default | Explicação |
|---|---|---|---|
| `df_dev`, `df_teste` | `DataFrame` | — | Bases de entrada (saída de Esfera 1/2/Construção, ou direto de `divisao`). |
| `gerar_transformacoes_potencia` | `bool` | `True` | Gera também log/raiz/quad/cubo/inversas como candidatas extras — o Pedro_Wise (nível 1, `transformacao_simples`) testa trocar a versão WOE por uma dessas via a semântica de "base" (mesmo prefixo). Só numérica contínua. Descarta automaticamente transformações com domínio inválido (ex.: log de negativo) em dev OU teste. Análogo em espírito a Box-Cox/Yeo-Johnson (**Atkinson, Riani & Corbellini, 2021**, *The Box–Cox Transformation: Review and Extensions*) — aqui um catálogo fixo de expoentes em vez de um `λ` ajustado por máxima verossimilhança. |
| `gerar_bin_ordinal` | `bool` | `True` | Gera também o índice do bin (faixa, como número) como candidata extra — outra "versão" da mesma base. Só numérica contínua. |
| `ao_processar_coluna` | `Callable[[str, float], None] \| None` | `None` | Callback chamado após cada coluna processada com sucesso, recebendo `(coluna, iv)` — gancho para progresso em tempo real (ex.: `app/backend/logica.py` publica isso numa fila SSE) sem esta biblioteca precisar saber o que é uma fila ou WebSocket. |

Retorna `(woe_dev, woe_teste, iv_por_variavel)` — os dois primeiros
prontos para `preselecao`/`treinamento`, o terceiro é IV por
variável-base, a chave usada por `preselecao.pre_selecionar`.

---

## 7. `preselecao`

Reduz o volume de candidatas antes do Pedro_Wise. Motivação: depois que
Construção (razões sem limite) e as transformações de potência de
`categorizar` passam a gerar dezenas/centenas de colunas extras por
variável-base, o volume de candidatas pode explodir — mais lento para o
Pedro_Wise e maior risco de selecionar ruído por acaso (o problema de
**múltiplos testes**, o mesmo pano de fundo da literatura de *stability
selection*: **Meinshausen & Bühlmann, 2008/2010**, *Stability Selection*,
JRSS-B — controle de falsos positivos em métodos de seleção instáveis
entre reamostragens).

Três filtros, aplicados em sequência (do mais barato ao mais informativo),
cada um independente e opcional (`limiar=None` pula o filtro):

### `filtrar_variancia(df, colunas, limiar=1e-6)`

| Parâmetro | Tipo | Default | Explicação |
|---|---|---|---|
| `df` | `DataFrame` | — | Base com as colunas candidatas. |
| `colunas` | `list[str]` | — | Candidatas a filtrar. |
| `limiar` | `float` | `1e-6` | Mantém colunas com variância > limiar — descarta quase-constantes, comuns entre transformações de potência quando a variável original tem pouca variação (ex.: `1/x` quando `x` é quase constante). |

### `filtrar_iv(colunas, iv_por_base, limiar=0.02)`

| Parâmetro | Tipo | Default | Explicação |
|---|---|---|---|
| `colunas` | `list[str]` | — | Candidatas a filtrar. |
| `iv_por_base` | `dict[str, float]` | — | Saída de `categorizar_e_transformar` (terceiro retorno). |
| `limiar` | `float` | `0.02` | Mantém colunas cuja variável-base tem IV >= limiar. Bases sem entrada em `iv_por_base` são tratadas como IV=0 (descartadas) — evita manter candidatas "órfãs" por engano. |

### `filtrar_correlacao(df, colunas, iv_por_base, limiar=0.9)`

| Parâmetro | Tipo | Default | Explicação |
|---|---|---|---|
| `df` | `DataFrame` | — | Base com as colunas candidatas. |
| `colunas` | `list[str]` | — | Candidatas (já filtradas por variância/IV, tipicamente). |
| `iv_por_base` | `dict[str, float]` | — | Usado como critério de desempate: entre pares correlacionados, mantém o de maior IV. |
| `limiar` | `float` | `0.9` | Correlação de Pearson absoluta acima da qual dois candidatos são considerados redundantes. **Pares da mesma variável-base são ignorados de propósito** — são sempre correlacionados entre si por construção (mesma variável, encoding diferente) e filtrar aqui colapsaria a família inteira num só sobrevivente antes do Pedro_Wise (`transformacao_simples`) ter a chance de escolher a melhor versão para o modelo. |

Este design — filtrar correlação **entre bases diferentes**, nunca dentro
da mesma base — evita justamente o modo de falha descrito por **Faletto &
Bien, 2022** (*Cluster Stability Selection*): quando há proxies altamente
correlacionados de um fator latente, um filtro de correlação ingênuo (ou
lasso puro sob stability selection) pode escolher arbitrariamente um
proxy e nunca convergir no correto. Aqui a distinção "mesma base = nunca
filtra por correlação, base diferente = filtra" é a fronteira que evita
esse problema por construção (ver `docs/literatura/stability-selection.md`,
seção "Conexão com o acervo", que já registra esse raciocínio para o
Pedro_Wise em geral).

### `pre_selecionar(df, iv_por_base, limiar_variancia=1e-6, limiar_iv=0.02, limiar_correlacao=0.9)`

Aplica os 3 filtros em sequência.

| Parâmetro | Tipo | Default | Explicação |
|---|---|---|---|
| `df` | `DataFrame` | — | Saída de `categorizar_e_transformar` (`woe_dev`). |
| `iv_por_base` | `dict[str, float]` | — | Terceiro retorno de `categorizar_e_transformar`. |
| `limiar_variancia` | `float \| None` | `1e-6` | Ver `filtrar_variancia`. `None` pula o filtro. |
| `limiar_iv` | `float \| None` | `0.02` | Ver `filtrar_iv`. `None` pula o filtro. |
| `limiar_correlacao` | `float \| None` | `0.9` | Ver `filtrar_correlacao`. `None` pula o filtro. |

Retorna um dicionário com `colunas_mantidas`, contagens em cada etapa do
funil (`n_inicial`, `n_apos_variancia`, `n_apos_iv`, `n_final`), e
`pares_correlacionados_descartados` (para auditoria de por que uma coluna
saiu).

---

## 8. `treinamento`

O "famigerado" Pedro_Wise — busca **greedy multi-nível** (forward/
backward, níveis 1 a 3) sobre GLM binomial (logística), otimizando **KS**
(estatística de Kolmogorov-Smirnov entre a distribuição de score de
eventos e não-eventos). Ver
`docs/algoritmos-originais/pedro-wise-resumo.md` para o algoritmo
completo (port fiel de um script R original, validado numericamente
contra o R — ver seção "Validação contra o R original" nesse documento:
KS-dev bate em 10 casas decimais).

### `treinar(df_dev, df_teste, criterio="teste", shadow_probing=False, forward_simples=True, transformacao_simples_nivel1=True, backward_simples_nivel1=True, min_vars_para_backward=5, forward_duplo=True, forward_triplo=True, transformacao_simples_nivel2=True, backward_simples_nivel2=True, n_best_duplo=5, n_best_triplo_1=3, n_best_triplo_2=3, nivel3_ativado=False, n_best_backward=2, profundidade_maxima_nivel3=2, p_valor_maximo=None)`

Todas as colunas de `df_dev`/`df_teste` exceto `y` são candidatas.

| Parâmetro | Tipo | Default | Explicação |
|---|---|---|---|
| `criterio` | `"teste"\|"dev"\|"min"` | `"teste"` | **Não é cosmético** — é o que o forward/backward otimiza em TODA a busca, decide se uma variável entra ou sai a cada passo. O R original tem um bug que faz o algoritmo decidir só por KS-dev (`docs/algoritmos-originais/Pedro_Wise_3.0.1.R`, o `return()` da métrica ignora o segundo argumento) — a validação do port mostrou que, sob `criterio="dev"`, o algoritmo aceita uma variável de puro ruído (`x_ruido2_woe`) por acaso amostral. `criterio="teste"` é o default recomendado para uso real justamente por evitar esse viés. |
| `shadow_probing` | `bool` | `False` | Reservado para um critério de parada alternativo (ainda não implementado como regra de parada plugável — ver backlog em `docs/algoritmos-originais/pedro-wise-resumo.md`, item 7) inspirado em **Thomas, Hepp, Mayr & Bischl, 2017** (*Probing for Sparse and Fast Variable Selection with Model-Based Boosting*): aumentar o conjunto de candidatas com cópias permutadas aleatoriamente ("shadow variables", sem relação real com `y` por construção) e parar assim que uma shadow seria selecionada — sinal de que o algoritmo está prestes a ajustar ruído, sem precisar separar dev/teste para decidir o ponto de parada. Ataca diretamente o caso `x_ruido2_woe` acima. |
| `forward_simples` | `bool` | `True` | Nível 1: testa adicionar cada variável fora do modelo, uma por vez; fica com a de maior KS se melhora. |
| `transformacao_simples_nivel1` | `bool` | `True` | Nível 1: troca a versão de uma base já no modelo por outra versão da mesma base (ex.: `idade_woe` → `idade_log`), testando se melhora o KS. |
| `backward_simples_nivel1` | `bool` | `True` | Nível 1: remove uma variável por vez, se o KS melhora. |
| `min_vars_para_backward` | `int` | `5` | Backward só é tentado se o modelo já tem mais que esse número de variáveis — evita backward degenerar um modelo pequeno. |
| `forward_duplo` | `bool` | `True` | Nível 2 (aciona quando nível 1 não melhora mais): pega o top-`n_best_duplo` do forward simples e testa **pares** de variáveis juntos — pega sinergias que forward variável-a-variável não descobre sozinho (o mesmo ponto cego estrutural sob correlação discutido em `docs/literatura/stability-selection.md`/`shadow-variable-probing.md`: seleção variável-a-variável falha ou fica subótima sob correlação; a correção recorrente na literatura é sempre "considerar em grupo" — aqui, testar pares). |
| `forward_triplo` | `bool` | `True` | Nível 2.5: combina top-`n_best_triplo_1` × `n_best_triplo_2` do forward duplo em triplas. |
| `transformacao_simples_nivel2` | `bool` | `True` | Mesma troca de versão de base, repetida no nível 2. |
| `backward_simples_nivel2` | `bool` | `True` | Mesmo backward, repetido no nível 2. |
| `n_best_duplo` | `int` | `5` | Quantas variáveis do forward simples entram na busca de pares. |
| `n_best_triplo_1`, `n_best_triplo_2` | `int` | `3`, `3` | Quantas variáveis de cada "lado" entram na busca de triplas. |
| `nivel3_ativado` | `bool` | `False` | Ativa o **backward complexo** (nível 3): para cada uma das `n_best_backward` variáveis mais promissoras de remover, remove e re-roda o Pedro_Wise inteiro a partir dali (recursão), comparando os modelos resultantes. Ponto de maior custo e risco combinatorial — desligado por default. |
| `n_best_backward` | `int` | `2` | Quantas variáveis avalia para remoção no nível 3. |
| `profundidade_maxima_nivel3` | `int` | `2` | Limite de profundidade da recursão do nível 3 (memoizado por conjunto de variáveis, ver anti-padrão #6 corrigido em `pedro-wise-resumo.md`). |
| `p_valor_maximo` | `float \| None` | `None` | Filtro opcional de significância estatística sobre candidatas — **não é o critério de seleção** (o Pedro_Wise nunca usou p-valor para decidir nada, nem no R original nem no port — a seleção é 100% guiada por KS). É um filtro adicional opcional para quem quer exigir significância além do ganho de KS. |

Retorna `ResultadoTreinamento` (dataclass congelado): `variaveis`,
`ks_dev`, `ks_teste`, `auc_teste`, `taxa_evento_dev`, `taxa_evento_teste`,
`coeficientes`, `estatisticas` (coeficiente + erro padrão + p-valor por
variável, só diagnóstico pós-hoc, não influencia a seleção),
`tabela_decis` (tabela de decis/gains, para relatório de negócio).

---

## Bibliografia citada

- Friedman, J. H., & Popescu, B. E. (2008). *Predictive learning via rule
  ensembles*. Annals of Applied Statistics. — base de `esfera2`.
- Kanter, J. M., & Veeramachaneni, K. (2015). *Deep feature synthesis:
  Towards automating data science endeavors*. — vocabulário de primitivas
  de `construcao`/`esfera1`.
- Navas-Palencia, G. (2020). *Optimal binning: mathematical programming
  formulation*. arXiv:2001.08025. — inspiração de `bins_monotonicos` em
  `categorizar`.
- Siddiqi, N. *Credit Risk Scorecards*. — convenção de WOE em `categorizar`.
- Meinshausen, N., & Bühlmann, P. (2008/2010). *Stability Selection*.
  JRSS-B. — motivação de `preselecao`.
- Faletto, G., & Bien, J. (2022). *Cluster Stability Selection*. — desenho
  de `filtrar_correlacao` (exceção para mesma base).
- Thomas, J., Hepp, T., Mayr, A., & Bischl, B. (2017). *Probing for
  Sparse and Fast Variable Selection with Model-Based Boosting*.
  Computational and Mathematical Methods in Medicine. — `shadow_probing`
  em `treinamento` (backlog).
- Pargent, F., Pfisterer, F., Thomas, J., & Bischl, B. (2022).
  *Regularized target encoding outperforms traditional methods...* —
  nota de cautela em `transformar_categoricas_woe`.
- Atkinson, A. C., Riani, M., & Corbellini, A. (2021). *The Box–Cox
  Transformation: Review and Extensions*. — paralelo às transformações de
  potência de `categorizar`.

Ver `docs/literatura/` para a lista completa com links e sínteses mais
longas por tópico.
