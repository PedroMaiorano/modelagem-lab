---
name: scaffold-interface
description: Use APENAS quando o usuário pedir explicitamente para começar a interface/dashboard/app sobre o arcabouço de modelagem (Streamlit, FastAPI ou Shiny). Dispara em "vamos começar o dashboard", "cria um app Streamlit pra isso", "expõe o modelo numa API". SKILL DORMENTE — não acione proativamente; o pilar 3 é trabalho futuro.
---

# Skill: scaffold-interface (dormente)

Fazer o scaffolding inicial de uma interface sobre o arcabouço de modelagem. **Esta skill fica em espera** — o pilar 3 (interface) só começa quando o usuário pedir. Até lá, não gere nenhum código de UI.

## Quando usar
- Pedido EXPLÍCITO de iniciar a interface.

## Quando NÃO usar
- Qualquer outra coisa. Não sugira interface proativamente; o foco atual são os pilares 1 (port) e 2 (literatura).

## Antes de scaffoldar: 3 perguntas de calibração
Não escolha o framework sozinho. Pergunte:
1. **Público/uso**: exploração pessoal rápida, ou serviço para outros consumirem?
2. **Forma**: dashboard interativo (visualizar seleção/modelos) ou API (servir predições)?
3. **Ecossistema**: o modelo core vive em Python ou R?

## Mapa de decisão de framework
- **Streamlit** — dashboard pessoal/exploratório em Python, rápido de montar. Default para "quero ver meus modelos".
- **FastAPI** — servir predições como serviço (endpoints, validação Pydantic, docs automáticas). Para "quero uma API".
- **Shiny** (R/`shiny` ou `shiny for Python`) — se o core está em R ou o usuário prefere o ecossistema R.

## Processo (quando ativada)
1. Confirme as 3 respostas de calibração.
2. Crie a pasta `app/` (fora de `python/` core) com estrutura mínima: entrypoint, separação UI/lógica, `requirements` próprio.
3. Importe do core (`python/`) — a interface **consome** o arcabouço, não reimplementa modelagem.
4. Um caminho end-to-end funcionando (ex.: carregar um modelo serializado e mostrar/servir uma predição) antes de expandir.
5. Anote a decisão de framework em `docs/planos/`.

## Formato de Saída
- Framework escolhido + razão (as 3 respostas).
- Estrutura `app/` criada.
- Caminho end-to-end mínimo funcionando.

## Armadilhas Comuns
- Escolher framework sem as 3 respostas → retrabalho.
- Reimplementar lógica de modelagem na UI em vez de importar do core.
- Ativar esta skill antes de o pilar 1/2 estarem maduros — é trabalho futuro por design.
