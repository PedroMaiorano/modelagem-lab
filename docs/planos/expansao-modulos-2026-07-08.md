# Decisão: expansão para 4 módulos de modelagem (2026-07-08)

> Registrado durante uma sessão autônoma longa (usuário sem disponibilidade
> para responder por ~8h30). Este documento é também a **nota de
> continuidade** — se uma sessão futura (após reset de créditos ou nova
> conversa) precisar retomar o trabalho sem o contexto da conversa original,
> comece por aqui.

## O pedido do usuário (resumo fiel)

1. Objetivo final: construir uma série de **apps modulares** cobrindo
   **categorização, transformação, construção e treinamento de variáveis**
   (treinamento = o que já existia como "pilar 1"/Pedro_Wise).
2. Ampliar MUITO a documentação/referências antes de implementar — pelo
   menos **50 referências** (papers + livros) nesses 4 escopos.
3. Organizar a documentação.
4. Depois de documentar, **implementar essas abordagens, comparar e
   melhorar** — mesmo padrão de rigor já usado no pilar 1 (testes,
   experimentos reais, honestidade sobre o que funciona/não funciona).
5. **Modularizar de verdade**: categorização, construção e transformação
   como módulos SEPARADOS (não um pacote monolítico).
6. **Pedido adicional, para DEPOIS de terminar o acima**: uma interface
   melhor que o Streamlit atual — mais fluida, responsiva, mostrando
   progresso durante a execução, e visualmente mais cuidada ("achei feio o
   app atual"). Explicitamente adiado pelo usuário — não iniciar antes do
   resto estar pronto.
7. Autonomia total concedida — sem necessidade de aprovação a cada passo.
   Prioridade: **produzir**.

## Arquitetura decidida: 4 módulos

O lab tinha 3 "pilares" (port Pedro_Wise, scraping, interface). Isso vira
uma dimensão ortogonal: os 4 módulos de modelagem abaixo são o **conteúdo**
do pilar 1 (que era só "treinamento"/seleção); scraping e interface
continuam pilares 2 e 3 como antes, agora servindo aos 4 módulos.

```
python/
├── pedro_wise/       # treinamento/seleção — já existe, completo (níveis 1-3)
├── categorizacao/     # binning/discretização — NOVO
├── transformacao/     # WOE, encodings, Box-Cox/Yeo-Johnson — NOVO
└── construcao/        # feature engineering/construction — NOVO (escopo mínimo)
```

Cada módulo é standalone (import próprio, testes próprios), mas desenhado
para compor: `construcao/` produz variáveis novas → `categorizacao/` as
discretiza → `transformacao/` converte os bins em WOE (ou outra
transformação) → `pedro_wise/` seleciona quais entram no modelo final.

## Por que essa ordem de implementação

1. **Categorização e transformação primeiro** — são os módulos mais
   maduros na literatura (binning ótimo e WOE são problemas bem definidos,
   com soluções canônicas — OptBinning, MODL), e o WOE já é a convenção de
   nomenclatura usada em TODO o lab (`_woe` em todos os datasets) sem
   nunca ter sido implementado. É a lacuna mais óbvia.
2. **Construção fica com escopo mínimo nesta rodada** — é o módulo menos
   maduro (a própria literatura mostra duas escolas divergentes: automática
   exaustiva vs. busca guiada) e o de maior risco de over-engineering. V1
   minimalista: razões/interações simples e interpretáveis (ex.:
   `PAYAMT1/BILLAMT1` no `credito_real` = "proporção paga da fatura") — não
   um motor de busca genética/RL completo. Ver
   `docs/literatura/construcao-variaveis.md` para a discussão completa.
3. **Interface (pedido 6) fica para depois**, por instrução explícita do
   usuário.

## Referências catalogadas (contagem para o pedido de "≥50")

| Arquivo | Refs |
|---|---|
| `docs/literatura/categorizacao.md` | 13 |
| `docs/literatura/transformacao.md` | 11 |
| `docs/literatura/construcao-variaveis.md` | 12 |
| `docs/literatura/stability-selection.md` (já existia) | 5 |
| `docs/literatura/shadow-variable-probing.md` (já existia) | 3 |
| `docs/referencias/sota-tracker-modelagem.md` §Referências (já existia) | 6 |
| `docs/referencias/livros.md` (novo) | 8 livros |
| **Total** | **~58** |

Nota honesta sobre profundidade: os papers de `categorizacao.md`,
`transformacao.md` e `construcao-variaveis.md` foram sintetizados a partir
de título/autor/ano (a API do OpenAlex não retorna abstract — limitação
documentada em `scraping/openalex_client.py`) combinado com conhecimento
direto dos métodos, não a partir do abstract lido diretamente como nos
tópicos de `stability-selection`/`shadow-variable-probing` (que vieram do
Semantic Scholar, com abstract). Confirmar o abstract no link antes de
citar formalmente em qualquer relatório externo.

## Estado no momento deste registro (para retomada)

- [x] Pesquisa e documentação dos 3 módulos novos + livros — feito.
- [ ] Implementação `python/categorizacao/` — em andamento/próximo passo.
- [ ] Implementação `python/transformacao/` — próximo passo.
- [ ] Implementação `python/construcao/` (escopo mínimo) — próximo passo.
- [ ] Experimento comparativo usando os módulos novos no `credito_real`.
- [ ] Atualizar `CLAUDE.md`, agentes e skills para refletir os 4 módulos
      (hoje ainda descrevem só "3 pilares" com pilar 1 = só Pedro_Wise).
- [ ] Interface melhor (pós-Streamlit) — **não iniciar até o acima estar
      pronto**, por instrução do usuário.

Ver `MEMORY.md` do sistema de memória do Claude Code (fora deste repo) para
o ponteiro de resumo entre sessões, se este documento não for suficiente.
