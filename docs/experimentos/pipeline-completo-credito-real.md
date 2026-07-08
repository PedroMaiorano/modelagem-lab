# Experimento: pipeline completo (construção→categorização→WOE→treinamento) no dataset real

> Terceiro experimento comparativo. Script:
> `scripts/pipeline_completo_credito_real.py`. Primeira prova de que os 4
> módulos do lab (`docs/planos/expansao-modulos-2026-07-08.md`) compõem —
> não só cada um isolado.

## Setup

Dataset `credito_real` (UCI, 30k clientes reais, ver `docs/referencias/datasets.md`).

1. **Construção**: 6 razões `PAYAMTi/BILLAMTi` ("proporção paga da fatura
   no mês i") — feature de negócio que não existe nas 23 colunas originais.
2. **Categorização**: `bins_monotonicos` (merge guloso) em cada uma das 29
   candidatas (23 originais + 6 construídas), ajustado só no dev.
3. **Transformação**: WOE ajustado nos bins do dev, aplicado em dev e teste.
4. **Treinamento**: `run_pedro_wise` (níveis 1-2.5) sobre as `_woe`
   resultantes, comparado contra rodar o mesmo Pedro_Wise **direto nas
   variáveis cruas** (sem os passos 1-3) — o baseline já conhecido de
   `docs/referencias/datasets.md`.

## Resultado

| Abordagem | KS-teste | AUC | Nº variáveis |
|---|---|---|---|
| Baseline (variáveis cruas) | 0.3995 | 0.7264 | 7 |
| **Pipeline completo** | **0.4215** | **0.7639** | 13 |

O pipeline completo supera o baseline em KS (+5.5%) e AUC (+3.8 pontos).
`proppaga1_woe` — a variável **construída**, não uma coluna original — entra
no modelo final, validando que o módulo `construcao/` contribui sinal real,
não é só exercício acadêmico.

## Achados

1. **A composição dos módulos funciona e ajuda**, não é só "mais uma
   camada de complexidade sem ganho" — primeira evidência concreta disso no
   lab.
2. **`PAY0` tem IV=0.83, classificado pela própria régua do lab
   (`classificar_iv`) como "suspeito (possível vazamento)".** Não escondido
   aqui: é uma característica conhecida deste dataset (o status de
   pagamento mais recente é extraordinariamente preditivo do default no mês
   seguinte — quase definição operacional do evento, não uma feature
   independente). Não é um bug do pipeline; é um sinal de que, num cenário
   real de produção, valeria investigar se `PAY0` está definido de forma
   temporal correta (sem overlap com a janela de definição de `y`) antes de
   usar esse IV como se fosse limpo.
3. **O pipeline final tem quase o dobro de variáveis (13 vs. 7)** — mais
   complexidade, ainda que com KS/AUC melhores em teste. Não avaliado aqui:
   estabilidade dessa seleção maior sob reamostragem (ver
   `docs/literatura/stability-selection.md` — próximo passo natural seria
   rodar stability selection sobre as `_woe` para checar se as 13 variáveis
   se sustentam).
4. **Tempo total: 68.7s** para 29 variáveis × 2 (categorização+WOE) + 2 runs
   completos do Pedro_Wise em 15k linhas — viável para uso exploratório
   interativo (ex.: dentro do dashboard).

## Adendo: `criterio="min"` testado (fechando o backlog anterior)

Mesma pipeline, trocando só `KSGaussianMetric(criterio="teste")` por
`criterio="min"` (mínimo entre KS-dev e KS-teste — pensado para penalizar
candidatas que só melhoram num dos dois splits, ver
`docs/experimentos/pedro-wise-vs-alternativas.md`).

| Critério | Nº vars | KS-teste | AUC |
|---|---|---|---|
| `"teste"` | 13 | 0.4215 | 0.7639 |
| `"min"` | 15 | 0.4196 | **0.7739** |

**Hipótese não confirmada**: esperava-se que `"min"` fosse mais conservador
e selecionasse *menos* variáveis (penalizando ruído específico do split de
teste). Na prática, selecionou **mais** (15 vs. 13) — incluindo uma segunda
variável construída (`proppaga2_woe`) — com KS praticamente igual e AUC
*melhor*. Duas leituras possíveis, nenhuma confirmada aqui: (a) o critério
`"min"` navega para um ótimo local diferente, não necessariamente mais
simples; (b) o dataset real tem sinal robusto o bastante que ambos os
critérios convergem para soluções de qualidade parecida, só com conjuntos
de variáveis diferentes. Vale registrar como resultado honesto, não como
confirmação da hipótese original — a recomendação de usar `"min"` para
reduzir risco de ruído continua válida (fundamentada no achado da validação
R↔Python), mas não por reduzir complexidade do modelo.

## Limitações

- `bins_monotonicos` é a versão gulosa/pragmática, não a ótima via MIP
  (ver `docs/literatura/categorizacao.md`) — resultado pode não ser o melhor
  binning possível para cada variável.
- Sem correção para o achado do item 2 (IV suspeito do `PAY0`) — o
  experimento reporta o número honesto, não filtra a variável. Decisão de
  produção ficaria a cargo de quem conhece a definição exata do dataset.
- Um único split dev/teste fixo (mesma limitação já documentada nos
  experimentos anteriores) — `criterio="min"` ainda não testado neste
  pipeline (backlog).
