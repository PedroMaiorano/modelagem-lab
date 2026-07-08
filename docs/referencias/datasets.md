# Datasets disponíveis (`data/`, gitignored)

> `data/` não é versionado (`.gitignore`) — cada dataset é reproduzível via
> script. Rode o gerador correspondente antes de usar o dashboard ou os
> scripts de experimento pela primeira vez numa máquina nova.

| Pasta | Script gerador | Natureza | Uso |
|---|---|---|---|
| `data/validacao_r/` | `scripts/gerar_dataset_validacao.py` | Sintético, gabarito conhecido | Validação R↔Python, primeiro experimento comparativo |
| `data/experimento_colinearidade/` | `scripts/gerar_dataset_colinearidade.py` | Sintético, proxies quase-duplicadas (corr 0.919) | Reprodução da falha da stability selection (Faletto & Bien) |
| `data/credito_real/` | `scripts/baixar_dataset_credito_uci.py` | **Real** — UCI "Default of Credit Card Clients" | Teste do port em dados reais, escala realista |
| `data/papers/` | clients em `scraping/` | Cache de metadados de literatura | Não é dataset de modelagem — ver `docs/referencias/apis-fontes-abertas.md` |

## `credito_real` — UCI Default of Credit Card Clients

- **Fonte**: UCI ML Repository #350 (Yeh & Lien, 2009) —
  https://archive.ics.uci.edu/dataset/350. Aberto, sem licença restritiva.
- **30.000 clientes de cartão de crédito em Taiwan**, split 50/50 dev/teste
  (embaralhado, seed fixa). Alvo `y` = inadimplência no mês seguinte (~22%
  de taxa de evento).
- **23 candidatas**: `LIMITBAL`, `SEX`, `EDUCATION`, `MARRIAGE`, `AGE`,
  `PAY0`/`PAY2`..`PAY6` (status de pagamento nos últimos 6 meses),
  `BILLAMT1`..`6` (valor da fatura), `PAYAMT1`..`6` (valor pago).
- **Nomes sem underscore de propósito**: as colunas originais do UCI usam
  `_` sem seguir a convenção `_woe`/`_log` do lab — `pedro_wise.base.
  extrair_base` colapsaria `PAY_0` e `PAY_AMT1` na mesma base `PAY`
  (variáveis diferentes tratadas como "mesma base"). O script de preparo
  remove os underscores originais para que cada variável seja sua própria
  base. Ver docstring de `baixar_dataset_credito_uci.py` para o raciocínio
  completo — **qualquer dataset real fora da convenção do lab precisa desse
  mesmo cuidado antes de entrar no Pedro_Wise**.
- **Resultado de referência** (`run_pedro_wise`, `criterio="teste"`, config
  default): seleciona `PAY0, PAY2, PAY3, PAY4, PAYAMT1, PAYAMT2, PAYAMT5`
  — KS-teste ≈ 0.40, AUC ≈ 0.73. `PAY0` (status de pagamento mais recente)
  como top preditor bate com a literatura publicada sobre este dataset.
