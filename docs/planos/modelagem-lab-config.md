# Plano de Configuração — modelagem-lab

> Decisões de arquitetura da configuração Claude Code deste lab. Criado 2026-07-07.

## Contexto do projeto
- **Domínio**: ciência de dados (modelagem estatística/ML) em Python e R, agnóstico de
  domínio; risco de crédito como caso de uso suportado.
- **Porte**: projeto pessoal robusto (não enterprise). Calibração equivalente aos labs
  irmãos (bet-lab, estatistica-lab).
- **Maturidade**: greenfield — sem código ainda; a config orienta a implementação futura.
- **Três pilares**: (1) port+melhoria do Pedro_Wise R→Python, (2) scraping de literatura
  aberta, (3) interface futura (dormente).

## Decisões de arquitetura e razões

| Decisão | Razão |
|---------|-------|
| 4 agentes (`algorithm-porter`, `literature-scout`, `model-builder`, `stats-advisor`) | Um por responsabilidade real. Porter (opus) e advisor (opus) porque port+melhoria e escolha metodológica exigem raciocínio; scout e builder (sonnet) são execução guiada. |
| Separar `stats-advisor` de `model-builder` | Decidir QUAL técnica (metodologia, trade-off clássico×SOTA) é raciocínio distinto de implementar/treinar. Espelha a divisão "arquiteto × executor". |
| `algorithm-porter` carrega contexto do Pedro_Wise via `pedro-wise-resumo.md` | O `.R` é denso (níveis recursivos, bug no return do KS). Um resumo curado evita redecifrar e fixa os anti-padrões a corrigir. |
| 4 skills, incluindo `scaffold-interface` **dormente** | Pilar 3 é futuro; a skill existe pronta mas instrui a não ativar proativamente — prepara sem sobre-engenheirar. |
| Copiar o `.R` original para `docs/algoritmos-originais/` + hook que protege a pasta | O algoritmo é peça insubstituível do pilar 1. |
| SOTA tracker próprio + `apis-fontes-abertas.md` operacional | Ancora as recomendações do `stats-advisor` e torna o scraping operacional (endpoints/limites reais), não genérico. |
| `settings.json` sem `bypassPermissions` | Lab de trabalho real: permissões mínimas (Python, R, git leitura+commit, curl p/ APIs abertas). Diferente do repo `claudio` (fábrica de configs). |
| Hook `pre-bash-safety.js` protege `docs/`, `data/papers/`, `algoritmos-originais/` e git destrutivo | Regras que nunca podem ser violadas; assíncrono não cabe (precisa bloquear antes de executar). Testado (exit 2 no bloqueio, 0 no permitido). |
| Métrica e estimador **plugáveis** como princípio de CLAUDE.md | O maior defeito do original é o acoplamento a KS+binomial; a config eleva a generalização a regra inegociável. |

## O que foi incluído e por quê
- **CLAUDE.md** (~130 linhas): âncora com comandos-alvo, comportamento Sempre/Nunca,
  contexto de domínio (semântica de "base"/transformação, KS-Gaussiano).
- **docs/referencias/**: SOTA tracker + APIs abertas (base para pilares 1 e 2).
- **docs/algoritmos-originais/**: `.R` + resumo (base do pilar 1).
- **Estrutura de código** (`python/`, `r/`, `scraping/`, `tests/`, `notebooks/`) vazia
  com `.gitkeep` — próxima etapa é implementar.

## O que foi excluído e por quê
- **Slash commands**: os labs irmãos não usam; skills+agentes cobrem os workflows. Evita ruído.
- **Interface (código)**: pilar 3 é futuro; só a skill dormente foi preparada.
- **Código do port**: por design, é trabalho de sessão de implementação futura.
- **5º+ agente**: seria sobre-engenharia para um projeto pessoal; 4 papéis cobrem o escopo.
- **CI/CD, managed settings**: fora do escopo de um lab pessoal.

## Próximos passos de evolução
1. **Portar o Pedro_Wise nível 1** em `python/` com teste de equivalência (skill `port-r-python`).
2. **Rodar `buscar-literatura`** pela primeira vez para semear `docs/literatura/` (ex.: stability selection, component-wise boosting).
3. **Implementar os clients de scraping** em `scraping/` (arXiv + Semantic Scholar primeiro) com cache em `data/papers/`.
4. Comparar o port contra LASSO/elastic net/stability selection num dataset real (pilar 1 × SOTA tracker).
