---
name: port-r-python
description: Use no workflow de portar um algoritmo de R para Python com melhoria algorítmica. Dispara em "porta o Pedro_Wise", "traduz esse algoritmo R para Python", "reimplementa a seleção de variáveis em Python". O caso central é o Pedro_Wise (seleção stepwise multi-nível).
---

# Skill: port-r-python

Portar um algoritmo R para Python idiomático, testado e generalizado — **corrigindo anti-padrões, não copiando-os**. Aciona o agente `algorithm-porter`.

## Quando usar
- Port de qualquer algoritmo R legado, especialmente o Pedro_Wise.
- Refatoração de um port existente para performance/generalização.

## Quando NÃO usar
- Modelo novo sem origem em R (use a skill `selecao-variaveis` / agente `model-builder`).
- Decidir qual técnica usar (use o agente `stats-advisor`).

## Processo

### 1. Carregue o contexto do original
Leia `docs/algoritmos-originais/pedro-wise-resumo.md` (não decifre o `.R` do zero). Confirme qual unidade portar — porte **um nível por vez** (nível 1 → 2 → 2.5 → 3), não tudo de uma vez.

**Gate**: o resumo cobre a unidade escolhida? Se não, leia o trecho correspondente do `.R`.

### 2. Desenhe a interface antes de implementar
Defina os protocolos plugáveis:
- `Metric(model, X, y) -> float` (KS-Gaussiano é uma implementação, não a única — suporte AUC/Gini, log-loss, AIC/BIC, R²aj).
- `Estimator` injetável (statsmodels GLM, sklearn, boosting).
- Dataclasses de resultado (substituem os `data.frame` acumulados por `rbind`).

### 3. Implemente preservando a lógica de seleção
Em `python/`. Preserve a semântica de **base de variável** (`extrair_base` = prefixo antes do último `_`) e a regra de não coexistir duas versões da mesma base.

### 4. Teste de equivalência (obrigatório antes de otimizar)
Em `tests/`, contra dataset sintético pequeno: a seleção e o KS batem com o R original dentro de tolerância? Só avance com o teste verde.

### 5. Otimize (cada passo mantendo o teste verde)
- `rbind` em loop → acumular em `list` + construir DataFrame uma vez (O(n²)→O(n)).
- Refit total → isolar fit em função pura; investigar warm start.
- Fits independentes → `joblib.Parallel`.
- `cat()` → `logging` estruturado.
- Recursão do backward complexo → memoização por `frozenset` de variáveis + limite de profundidade.

### 6. Qualidade
`pytest`, `ruff`, `mypy`. Docstrings do PORQUÊ.

## Formato de Saída
- Arquivos criados (caminhos absolutos).
- Mapa "função R → função Python".
- Anti-padrões corrigidos.
- Resultado do teste de equivalência.
- Próxima unidade a portar.

## Armadilhas Comuns
- Portar tudo de uma vez em vez de nível a nível → impossível validar equivalência.
- Otimizar antes de provar equivalência → você não sabe se quebrou a lógica.
- Hardcodar KS/binomial → perde a generalização, que é metade do objetivo do port.
- Esquecer a semântica de "base"/transformações → o modelo passa a aceitar duas versões da mesma variável.
