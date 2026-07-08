# Experimento: Pedro_Wise vs. LASSO vs. Stability Selection

> Registrado como "experimento natural do lab" em
> `docs/referencias/sota-tracker-modelagem.md` §5. Script:
> `scripts/experimento_pedro_wise_vs_alternativas.py`. Dataset:
> `data/validacao_r/{dev,teste}.csv` (gerado por `gerar_dataset_validacao.py`,
> mesmo dataset usado para validar o port contra o R — processo gerador
> conhecido, permite avaliar contra gabarito, não só KS/AUC).

## Gabarito (processo gerador conhecido)

- Bases informativas: `xa`, `xb` (proxies ruidosas de um fator latente `u`),
  `x1`, `x2`, `x3`.
- Bases de ruído puro (independentes de `y`): `x_ruido`, `x_ruido2`.
- `x1_log` é outra versão (mesma base `x1`) mais ruidosa — nem sinal
  independente nem ruído puro.

## Resultado

| Método | Variáveis selecionadas | KS-teste | AUC | Recall (bases reais) | Ruído incluído |
|---|---|---|---|---|---|
| Pedro_Wise | x1_woe, x2_woe, x3_woe, x_ruido_log, xa_woe, xb_woe | 0.3956 | 0.764 | 100% | 1 base |
| Pedro_Wise + shadow probing | mesmas do acima | 0.3956 | 0.764 | 100% | 1 base |
| LASSO (CV) | x1_woe, x2_woe, x3_woe, xa_woe, xb_woe | 0.3929 | 0.764 | 100% | 0 |
| Stability Selection | x1_woe, x2_woe, x3_woe, xa_woe, xb_woe | 0.3929 | 0.764 | 100% | 0 |

Frequência de seleção (stability selection, 100 reamostragens, C=0.05):
`xa/xb/x1/x2/x3 = 1.00`; ruído entre `0.04` e `0.14` — separação limpa.

## Achados

1. **Todos os métodos recuperam 100% do sinal real.** Nenhum perdeu uma base
   informativa — o dataset não é adversarial o bastante para diferenciar por
   recall.

2. **LASSO e Stability Selection convergiram para o modelo exato (zero
   ruído), com KS quase idêntico entre si.** Nesta base sintética, a robustez
   extra da stability selection não se paga — o LASSO regularizado sozinho já
   acerta. Isso é esperado: o cenário em que stability selection ganha de
   verdade é o de proxies correlacionados de um fator latente competindo
   entre si (ver `docs/literatura/stability-selection.md`, achado do Faletto &
   Bien) — não é o caso aqui, onde `xa`/`xb` são proxies do mesmo `u` mas
   **ambos** entram sem competição (LASSO não penaliza correlação por si só).

3. **Pedro_Wise (com ou sem shadow probing) aceitou 1 variável de ruído
   (`x_ruido_log`) e teve KS-teste ligeiramente MAIOR (0.3956 vs 0.3929) que
   os métodos que não a incluíram.** Isso não é o Pedro_Wise "achando mais
   sinal" — é o sintoma exato que motivou o shadow probing e já tinha
   aparecido na validação contra o R (`x_ruido2_woe` lá, `x_ruido_log` aqui):
   uma métrica greedy otimizada contra um split de teste FIXO (não
   cross-validado) pode capturar um pedaço de ruído específico daquele split
   e reportar isso como "melhora". LASSO/stability selection não sofrem disso
   porque não perseguem a métrica candidata-a-candidata — decidem via
   regularização/frequência de reamostragem, não via KS contra um teste fixo.

4. **Shadow probing não preveniu esse caso específico.** Mesmo achado do
   experimento sintético em `tests/test_shadow_probing.py`: é heurística, não
   garantia — reduz o risco (documentado com varredura de sementes: nunca
   piora, às vezes zera o ruído), mas não elimina 100% dos casos. Aqui a
   variável de ruído entrou numa rodada em que sua própria sombra não venceu.

## Conclusão prática para o lab

- **Para decisão de negócio onde falso positivo de variável é caro** (ex.:
  variável espúria que não vai se sustentar em produção): preferir
  LASSO/stability selection ou Pedro_Wise **com validação cruzada do KS**, não
  um único split fixo de teste — o ponto fraco aqui não é o Pedro_Wise em si,
  é usar um split único como critério de aceitação greedy.
- **Para manter o Pedro_Wise como ferramenta**: o `criterio="min"` do
  `KSGaussianMetric` (mínimo entre KS-dev e KS-teste, já implementado) é a
  correção mais barata a testar a seguir — penaliza candidatas que só
  melhoram num dos dois splits.
- Não há, neste experimento, evidência de que o Pedro_Wise recupera sinal que
  os métodos embedded não recuperam — a vantagem histórica do wrapper
  stepwise (guiar por métrica de negócio como KS) não apareceu como ganho
  líquido aqui, só como risco adicional de ruído.

## Limitações deste experimento

- Um único dataset sintético, gerado com sinal aditivo-linear em logit — não
  testa colinearidade adversarial forte nem alta dimensão (p >> n).
- `C` da stability selection foi ajustado manualmente para este dataset (ver
  docstring de `rodar_stability_selection` no script) — não há garantia de
  que o mesmo C funcione tão bem noutro dataset; a escolha de regularização
  para stability selection continua sendo um ponto de atenção prático, não
  resolvido automaticamente pelo método.
- ✅ **Feito**: [`docs/experimentos/colinearidade-stability-selection.md`](colinearidade-stability-selection.md)
  repete com `xa`/`xb` fortemente colineares (corr 0.919). A falha da
  stability selection foi reproduzida de forma dramática (modelo vazio), mas
  **não foi o `forward_duplo` que evitou o problema** — hipótese de entrada
  daquele experimento corrigida no próprio documento: qualquer método com fit
  único e determinístico (LASSO simples ou o próprio Pedro_Wise em nível 1)
  já é imune, porque o problema é específico de consistência entre
  reamostragens, não de testar variáveis uma a uma vs. em pares.
