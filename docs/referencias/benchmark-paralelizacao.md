# Benchmark de paralelização — port Python do Pedro_Wise

> Decisão registrada: `backend="threading"` fixo em `pedro_wise.selection.PARALLEL_BACKEND`,
> `n_jobs` default = 8 (`pedro_wise.types.N_JOBS_PADRAO`). Reproduzível via
> `python scripts/benchmark_paralelizacao.py` (chamada isolada) — o número que
> importa (uso real) está documentado aqui porque leva minutos para reproduzir.

## Por que medir duas formas diferentes

Uma chamada isolada a `Parallel()` mede principalmente o **custo fixo** do
backend (subir processos vs. threads). O uso real do algoritmo faz dezenas de
chamadas a `Parallel()` dentro da mesma busca (`run_level1`/`run_pedro_wise`),
e o `loky` (baseado em processos) reaproveita o pool entre chamadas — seu
custo fixo dilui. Só a medição end-to-end revela o ganho real.

## Chamada isolada (processo novo a cada medição)

Máquina: 8 vCPUs, Windows.

| Cenário | sequencial | loky n_jobs=4 | threading n_jobs=4 | threading n_jobs=8 |
|---|---|---|---|---|
| 1.5k linhas, 40 candidatas | 0.40s | 3.9-4.0s | 0.48-0.57s | 0.53-0.57s |
| 30k linhas, 80 candidatas | 5.6s | 1.8-1.9s* | 2.2-2.3s | 1.8-1.9s |

\* O `loky` nesse cenário reaproveitou o pool entre repetições do próprio
script de benchmark (que roda várias configurações em sequência no mesmo
processo Python) — não reflete o custo de um processo novo por execução.

## Uso real: `run_level1` completo

Dataset: 15.000 linhas, 30 variáveis candidatas, convergindo para 11
variáveis selecionadas (várias dezenas de chamadas a `Parallel()` ao longo da
busca — forward simples, troca, backward, repetidos até convergir).

Medição original (2026-07-07):

| Backend | n_jobs | Tempo total | Speedup |
|---|---|---|---|
| threading | 1 (sequencial) | 64.7s | 1.0x |
| threading | 4 | 22.4s | 2.9x |
| loky | 4 | 26.1s | 2.5x |

Re-medição (2026-07-09, mesma máquina, mesmo cenário) comparando `n_jobs` no
regime que importa — a medição original nunca tinha testado `n_jobs=8` no
uso real, só na chamada isolada:

| Backend | n_jobs | Tempo total | Speedup vs. n_jobs=4 |
|---|---|---|---|
| threading | 4 | 27.5s | 1.0x |
| threading | 6 | 23.1s | 1.19x |
| threading | 8 | 21.3s | **1.29x** |

(O tempo absoluto de `n_jobs=4` variou entre as duas medições — 22.4s vs.
27.5s — por ruído de máquina/carga do sistema entre sessões; o que importa é
a comparação relativa dentro da mesma rodada de medição.)

## Conclusão

- `threading` vence em ambos os regimes (isolado e real) — nunca pior que
  `loky`, e sem o custo de serializar `df_dev`/`df_teste` por worker.
- O ganho real só aparece em uso normal (busca completa), não numa
  comparação isolada de candidatas — por isso o benchmark rápido
  (`scripts/benchmark_paralelizacao.py`) subestima o benefício; este
  documento existe para registrar o número que de fato importa.
- **`n_jobs=8` é o default atual** (`N_JOBS_PADRAO`) — supera `n_jobs=4` em
  ~29% no uso real nesta máquina (8 vCPUs). A medição original tinha fixado
  `n_jobs=4` sem testar 8 no regime real; corrigido nesta re-medição.
- Para datasets de desenvolvimento minúsculos (milhares de linhas, poucas
  iterações), a diferença é irrelevante em termos absolutos — `n_jobs=1`
  continua uma opção razoável se quiser o mínimo de overhead/determinismo de
  debug.

**Última medição**: 2026-07-09, nesta máquina. Re-medir se a forma de uso
mudar significativamente (datasets muito maiores, máquina com perfil de CPU
diferente) — os números absolutos não são portáveis entre máquinas.
