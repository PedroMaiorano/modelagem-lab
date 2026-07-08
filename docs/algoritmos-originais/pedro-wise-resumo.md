# Pedro_Wise 3.0.1 — Resumo do Algoritmo Original (R)

> Documento-âncora do **pilar 1** (port R→Python). Leia isto antes de portar —
> evita decifrar o `.R` do zero. Fonte fiel: `Pedro_Wise_3.0.1.R` (nesta pasta).

## O que o algoritmo faz

Busca **greedy multi-nível** de seleção de variáveis para **GLM binomial (logística)**,
otimizando uma métrica de separação (**KS**) calculada sobre um score transformado.
Parte de um modelo inicial (tipicamente o nulo `y ~ 1`) e adiciona/remove/troca
variáveis enquanto o KS melhorar, subindo de nível de complexidade quando um nível
"empaca".

## A métrica: `calc_ks_score`

1. Prediz probabilidade do GLM e converte em `xbeta = -log(1/p - 1)`.
2. Score Gaussiano: `trunc(500 + xbeta * (100/log(2)))`.
3. Define 11 quebras por quantis fixos `q = c(0, .025, .07, .15, .3, .5, .7, .85, .93, .975, 1)`.
4. Reescala linearmente por faixa para um **SCORE 0–1000** (interpolação entre quebras).
5. Roda `ks.test` entre o SCORE dos `y==1` e dos `y==0`, na base de **desenvolvimento** e na de **teste**.
6. Retorna a estatística KS (obs.: o `return(as.numeric(ks_value_1, ks_value_2))` no
   original efetivamente devolve só o KS de desenvolvimento — **bug conhecido**, o
   segundo argumento é ignorado por `as.numeric`; o port deve decidir explicitamente
   se otimiza KS-dev, KS-teste, ou uma combinação penalizada por overfit).

## Conceito de "base" e transformações

Variáveis têm sufixo de transformação (`_woe`, `_log`, etc.). `extrair_base(var)` =
`sub("_[^_]+$", "", var)` = prefixo antes do último `_`. Regras:
- Uma **base** entra no modelo em no máximo **uma** versão por vez.
- `filtrar_variaveis_fora_modelo` só oferece bases ainda não usadas.
- **Troca simples** (`teste_troca_simples`): remove uma versão e insere outra versão
  da **mesma base** (mesma `extrair_base`), testando se a transformação alternativa
  melhora o KS.

## Estrutura de níveis (lógica de seleção a preservar)

- **Nível 1**
  1. `forward_simples`: testa adicionar cada variável fora do modelo, uma por vez; fica com a de maior KS se melhora.
  2. `transformacao_simples`: troca versão de uma base já no modelo por outra versão da mesma base.
  3. `backward_simples`: remove uma variável por vez (só se o modelo tem >5 vars) se o KS melhora.
- **Nível 2** (aciona quando nível 1 não melhora mais)
  1. `forward_duplo`: pega top-`n_best_duplo` do forward simples e testa pares de variáveis.
  2. `transformacao_simples` nível 2.
  3. `backward_simples` nível 2.
- **Nível 2.5**: `forward_triplo` — combina top-`n_best_triplo_1` × `n_best_triplo_2` do forward duplo em triplas.
- **Nível 3**: `backward_complexo` — para cada uma das `n_best_backward` variáveis mais
  promissoras de remover, remove a variável e **rechama o Pedro_Wise inteiro** a partir
  dali (recursão, com `backward_complexo=FALSE` na chamada filha), comparando os
  modelos resultantes. É o ponto de maior custo e risco combinatorial.

Quando qualquer nível encontra melhora, o algoritmo volta ao nível 1 com o novo melhor
modelo. Para quando nenhum nível melhora ou a `n_max_complexidade` é atingida.

## Parâmetros principais

`modelo_inicial`, `df_treino`, `df_teste`, flags liga/desliga por etapa,
`n_best_duplo=5`, `n_best_triplo_1/2`, `n_best_backward`, `n_max_prolongamento`,
`n_max_complexidade=999`, `trace`.

## Anti-padrões conhecidos (o port DEVE corrigir)

| # | Anti-padrão no R | Correção no port |
|---|------------------|------------------|
| 1 | `rbind` em loop (O(n²)) | acumular em `list` → `pd.DataFrame(rows)` uma vez |
| 2 | Refit completo do GLM por candidata testada | isolar fit em função pura; investigar warm start/update incremental |
| 3 | Fits independentes sem paralelização | `joblib.Parallel` / `concurrent.futures` |
| 4 | `cat()` como logging | `logging` estruturado, nível configurável (era `trace`) |
| 5 | Acoplamento a KS + família binomial | métrica e estimador **injetáveis** (protocolos); suportar AUC/Gini, log-loss, AIC/BIC, R²aj e outras famílias/modelos |
| 6 | Recursão do backward complexo sem memoização | memoizar por `frozenset` de variáveis + limite de profundidade/budget |
| 7 | `data.frame` como estrutura de trabalho | numpy / matriz de design pré-computada |
| 8 | Sem testes, type hints, docstrings | tudo type-hinted, testado, docstring do PORQUÊ |
| 9 | `return` do KS ignora o 2º argumento (bug) | decidir explicitamente o critério (dev/teste/combinado) |
| 10 | Bug de sintaxe em `forward_simples`: `%>%` órfão antes do `if` (linha ~197) — o R original **não executa** sem esse ajuste | corrigido implicitamente: o port não tem essa classe de bug (sem pipe mágico), mas ver nota de validação abaixo |
| 11 | Backward complexo (nível 3) recalcula `ks_atual` a partir do último `modelo_bwc` da variável de laço, não do ramo vencedor (bug) | `level3.py` usa sempre o score do ramo de fato escolhido |

## Plano de port sugerido (incremental) — status

1. ✅ Métricas plugáveis (`metrics.py`): KS-Gaussiano fiel ao original + AUC.
2. ✅ Estimador plugável e utilitários de "base"/transformação (`estimators.py`, `base.py`).
3. ✅ Nível 1 (forward/troca/backward simples) — `selection.py`.
4. ✅ Níveis 2 e 2.5 — `level2.py`, orquestrado por `pipeline.py`.
5. ✅ Nível 3 (backward complexo) com memoização e limite de profundidade — `level3.py`.
6. ✅ Paralelização (`joblib`, backend `threading`) — medida e ativada, ver
   `docs/referencias/benchmark-paralelizacao.md` (2.9x em uso real).

Ver a skill `port-r-python` e o agente `algorithm-porter` para o workflow operacional.

## Validação contra o R original (2026-07-07)

Rodei o R original de verdade (R 4.5.1, pacotes instalados) contra o mesmo
dataset sintético usado pelo Python, com a config de exemplo do próprio
script (`n_best_duplo=5, n_best_triplo_1=3, n_best_triplo_2=3,
backward_complexo_nivel_3=FALSE`). Scripts em `scripts/`:
`gerar_dataset_validacao.py`, `validar_port_r.R`, `validar_port_python.py`.

**Achado**: o R original, como está em
`docs/algoritmos-originais/Pedro_Wise_3.0.1.R`, **não roda** — `forward_simples`
tem um `%>%` órfão (linha ~197, provável artefato de copy-paste) que causa
`Error in if (.) !is.null(mod_temp) else { : the condition has length > 1`
assim que a primeira variável é testada. Não é um anti-padrão de estilo, é um
bug de sintaxe que impede a execução. Documentado agora como item #10 da
tabela acima. Para validar, usei uma cópia com **uma única linha corrigida**
(`scripts/Pedro_Wise_3.0.1_corrigido_para_validacao.R`, diff documentado no
cabeçalho do arquivo) — o arquivo "cópia fiel" nesta pasta permanece
intocado.

**Resultado**: rodando o port Python com `KSGaussianMetric(criterio="dev")`
(espelhando o critério de decisão que o R de fato usa, por causa do bug do
item #9 — o R decide só por KS-dev apesar de calcular os dois), a seleção de
variáveis e o KS batem com o R corrigido:

| | R (corrigido só na sintaxe) | Python (port) |
|---|---|---|
| Variáveis selecionadas | `x1_woe, x2_woe, x3_woe, xa_woe, xb_woe, x_ruido2_woe` | idênticas |
| KS-dev | 0.402315057876447 | 0.4023150578764469 |
| KS-teste | 0.394468001252362 | 0.3944680012523619 |
| Nº de atualizações aceitas | 6 (só forward simples) | 6 (mesma sequência) |

Match exato (diferença só na precisão de exibição do R). O port reproduz a
lógica de seleção do original fielmente — incluindo o comportamento
"indesejável" esperado de um algoritmo guloso sobre dados ruidosos: ambos
aceitaram `x_ruido2_woe` (uma variável de puro ruído) por acaso amostral, o
que é esperado e não um bug — é o motivo pelo qual `criterio="teste"` (não
`"dev"`) é o default recomendado do port para uso real.
