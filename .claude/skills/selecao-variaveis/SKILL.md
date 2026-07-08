---
name: selecao-variaveis
description: Use no workflow de selecionar variáveis para um modelo — escolher a técnica e rodar a seleção. Dispara em "seleciona as variáveis para esse modelo", "roda um stepwise/LASSO aqui", "quais variáveis entram no scorecard?". Cobre clássico (stepwise) e SOTA (regularização, boosting, stability selection).
---

# Skill: selecao-variaveis

Selecionar variáveis com honestidade metodológica — escolhendo a técnica certa e validando sem leakage. Coordena `stats-advisor` (decide o quê) e `model-builder` (implementa).

## Quando usar
- Precisar reduzir/selecionar variáveis para um modelo.
- Comparar técnicas de seleção num dataset.

## Quando NÃO usar
- Portar o algoritmo Pedro_Wise legado (use `port-r-python`).
- Buscar literatura sobre uma técnica (use `buscar-literatura`).

## Processo

### 1. Diagnóstico (via stats-advisor)
Levante os pressupostos que ditam a técnica:
- **n vs. p** (alta dimensão?).
- Colinearidade / grupos de variáveis.
- Tipo de alvo (binário/contínuo/contagem) e família.
- Interpretabilidade/inferência vs. só predição.
- Métrica de decisão (KS/Gini padrão de crédito? AUC? AIC/BIC?).
- Há ordem temporal? (define o esquema de validação anti-leakage).

**Gate**: os pressupostos estão claros? Se não, pergunte antes de rodar qualquer coisa.

### 2. Escolha da técnica (trade-off explícito)
- **Stepwise** (métrica de negócio não-padrão + interpretabilidade; ruim em alta dim).
- **LASSO / elastic net** (escalável, seleção+shrinkage; elastic net p/ colinearidade).
- **Component-wise boosting** (alta dim, estrutura aditiva, early stopping).
- **Stability selection / probing** (controle de falsos positivos, quase sem tuning).
- **AutoML** como baseline/sanity check, nunca como resposta final se interpretabilidade manda.

Ancore em `docs/referencias/sota-tracker-modelagem.md`.

### 3. Implementação (via model-builder)
Split treino/validação/teste (ou temporal) ANTES de selecionar. Métrica e estimador plugáveis. Seed fixa.

### 4. Avaliação
Métrica de validação (não treino), estabilidade da seleção (rodar em folds/reamostragens), e — para classificação de risco — calibração.

## Formato de Saída
- Técnica escolhida + por quê (trade-off).
- Variáveis selecionadas.
- Esquema de validação e métrica no conjunto de teste.
- Auditoria de leakage.
- Estabilidade da seleção (se rodada em reamostragens).

## Armadilhas Comuns
- Selecionar antes de separar treino/teste → leakage clássico.
- Stepwise em alta dimensão → instável e caro; prefira regularização.
- Confundir seleção preditiva com identificação causal → se a pergunta é de efeito, isso é armadilha (aponte causal ML).
- Reportar a métrica no mesmo dado usado para selecionar.
