# Guia — Fluxo de Trabalho do modelagem-lab

Como os três pilares e os agentes/skills se encaixam.

## Os três pilares
1. **Port + melhoria do Pedro_Wise (R→Python)** — pilar central atual.
2. **Scraping de literatura acadêmica aberta** — alimenta a wiki e o SOTA tracker.
3. **Interface futura** — dormente até o usuário pedir.

## Mapa de "quando usar o quê"

| Situação | Artefato |
|----------|----------|
| Portar/refatorar o Pedro_Wise ou outro algoritmo R | skill `port-r-python` → agente `algorithm-porter` |
| "Qual técnica de seleção/modelagem usar para X?" | agente `stats-advisor` |
| Implementar/treinar um modelo ou rodar seleção | skill `selecao-variaveis` / agente `model-builder` |
| Buscar papers recentes sobre uma técnica | skill `buscar-literatura` → agente `literature-scout` |
| Iniciar dashboard/API (só quando pedido) | skill `scaffold-interface` (dormente) |

## Fluxo típico — port do Pedro_Wise
1. Ler `docs/algoritmos-originais/pedro-wise-resumo.md`.
2. `stats-advisor` valida a estratégia de generalização (métrica/estimador plugáveis).
3. `algorithm-porter` porta **nível a nível**, com teste de equivalência antes de otimizar.
4. `model-builder` compara o port contra LASSO/elastic net/stability selection no mesmo dataset.

## Fluxo típico — pesquisa de técnica
1. `buscar-literatura` sobre o tópico (fontes abertas, cache primeiro).
2. `literature-scout` sintetiza em `docs/literatura/{topico}.md`.
3. Se muda o estado da arte, atualizar `docs/referencias/sota-tracker-modelagem.md`.

## Princípios que valem sempre
- Métrica e estimador **plugáveis**, nunca hardcoded.
- Validação honesta, **anti-leakage**.
- Só fontes de literatura **abertas**.
- Código novo: **type hints + testes + ruff**.
