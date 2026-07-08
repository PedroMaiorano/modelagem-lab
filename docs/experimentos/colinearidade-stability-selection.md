# Experimento: colinearidade forte e a falha da stability selection

> Segundo experimento comparativo, motivado pelo primeiro
> (`docs/experimentos/pedro-wise-vs-alternativas.md`) e pela leitura do
> Faletto & Bien (2022, ver `docs/literatura/stability-selection.md`). Script:
> `scripts/experimento_colinearidade.py`. Dataset:
> `data/experimento_colinearidade/{dev,teste}.csv`
> (`gerar_dataset_colinearidade.py`) — `xa_woe`/`xb_woe` são proxies
> quase-duplicadas de um único fator latente `u` (corr = 0.919).

## Hipótese de entrada (e por que estava parcialmente errada)

A hipótese ao propor este experimento era: "stability selection falha com
proxies correlacionados; o `forward_duplo` do Pedro_Wise teria vantagem real
porque testa pares conjuntamente". A segunda metade **não se confirmou** — ver
achado 3 abaixo. Registrando isso porque é mais útil corrigir a hipótese
publicamente do que só reportar o resultado que "deu certo".

## Setup

- `C=0.005` para LASSO/stability selection, achado por varredura manual
  específica deste dataset (não é o C de `pedro-wise-vs-alternativas.md` —
  cada dataset precisa da própria varredura, ver script). Comportamento por C:
  - `C=0.02` a `0.01`: `xa`/`xb` estáveis em ~100% de frequência cada.
  - `C=0.005`: **ambas colapsam juntas para ~27-36%** — a zona de falha.
  - `C=0.002`: ambas zeradas (regularização forte demais até para sinal real).
- Comparação direta no mesmo `C=0.005`: LASSO de fit único vs. stability
  selection (100 reamostragens) — isola o efeito da reamostragem em si, não
  da força de regularização (que é idêntica nos dois).

## Resultado

| Método | Bases selecionadas | KS-teste | AUC |
|---|---|---|---|
| Pedro_Wise (nível 1 só, sem forward_duplo) | x_ruido, xa, xb | 0.5121 | 0.829 |
| Pedro_Wise (com forward_duplo) | x_ruido, xa, xb | 0.5121 | 0.829 |
| LASSO (C ótimo por CV) | xa, xb | 0.5093 | 0.830 |
| LASSO (fit único, C=0.005 — mesmo da stability selection) | xa, xb | 0.5093 | 0.830 |
| **Stability Selection (C=0.005)** | **(nenhuma)** | **0.0000** | **0.500** |

Frequência de seleção (stability selection, C=0.005): `xb_woe=0.36`,
`xa_woe=0.26`, ruído em `0.00`. Limiar padrão 0.6 — **nenhuma variável
passa**, apesar do sinal real ser forte (AUC 0.83 com qualquer outro método).

## Achados

1. **A falha do Faletto & Bien foi reproduzida de forma dramática, não sutil.**
   Não é "stability selection perde um pouco de recall" — é "stability
   selection retorna um modelo vazio, equivalente a chute aleatório (AUC
   0.500)", enquanto um LASSO de fit único **no mesmo nível de
   regularização** recupera o sinal perfeitamente. A causa é a reamostragem
   em si: cada meia-amostra tende a favorecer arbitrariamente `xa` ou `xb`
   (nunca as duas com força total), então a frequência individual de cada uma
   nunca acumula os 60% necessários — mesmo que "pelo menos uma das duas"
   apareça em quase toda reamostragem.

2. **A janela de regularização onde a falha ocorre é estreita e não-óbvia.**
   Uma diferença de 4x em `C` (0.02 → 0.005) é a distância entre "estável a
   100%" e "colapsa para ruído". Isso é um risco operacional real, não só
   acadêmico: quem usa stability selection precisa varrer regularização
   *especificamente checando a zona de instabilidade*, não só otimizar para
   frequência alta na configuração default.

3. **Hipótese corrigida: o `forward_duplo` do Pedro_Wise NÃO foi o que evitou
   a falha — nível 1 sozinho já dá o resultado idêntico ao nível 1+2.** O
   motivo real: Pedro_Wise (como o LASSO de fit único) faz **um único ajuste
   determinístico** no dataset de desenvolvimento inteiro. A patologia da
   stability selection é especificamente sobre *consistência entre
   reamostragens* — um método que nunca reamostra é estruturalmente imune a
   ela, independente de testar variáveis uma a uma ou em pares. O
   `forward_duplo` continua tendo valor demonstrado (ver
   `tests/test_level2.py::test_forward_duplo_encontra_par_sinergico...`), mas
   para um problema **diferente**: pares fracos individualmente e fortes
   juntos (sinergia), não pares fortes individualmente e redundantes
   (colinearidade). Faletto & Bien também reconhecem isso — a solução deles
   (*cluster stability selection*) não é "testar pares", é agrupar variáveis
   correlacionadas antes de aplicar o procedimento, um mecanismo diferente do
   `forward_duplo`.

4. **Pedro_Wise ainda aceitou 1 variável de ruído (`x_ruido`)**, terceira
   ocorrência do mesmo padrão documentado em
   `docs/experimentos/pedro-wise-vs-alternativas.md` e na validação contra o
   R — reforça que `criterio="min"` (KS mínimo dev/teste) é o próximo teste
   prático a fazer, não mais uma hipótese isolada.

## Conclusão prática para o lab

- **Stability selection não é "sempre mais segura" que um LASSO simples** —
  pode ser estritamente pior (modelo vazio) se a regularização cair na zona
  de instabilidade sob colinearidade forte. Se for usar stability selection
  no lab, varrer a curva de frequência por `C` e desconfiar de quedas
  abruptas simultâneas em variáveis conhecidas por serem correlacionadas.
- **Para colinearidade forte especificamente, um LASSO de fit único (ou o
  Pedro_Wise) é mais confiável que stability selection "de manual"** —
  contra-intuitivo dado que stability selection é vendida como a opção mais
  robusta, mas é exatamente o cenário que a literatura já avisava.
- **O verdadeiro teste do `forward_duplo`** continua sendo o cenário de
  sinergia (não colinearidade) — já coberto pelos testes automatizados, não
  precisa de novo experimento ad-hoc a menos que surja um caso real do lab
  que pareça sinérgico.

## Limitações

- Regularização "ótima" de stability selection (varredura manual, C=0.005)
  foi escolhida deliberadamente para cair na zona de falha — o objetivo era
  reproduzir o fenômeno, não simular o uso "ingênuo" default de alguém que
  nunca varreria C. Um praticante que só rodasse `LogisticRegressionCV` (C
  ótimo por CV, ~0.5-1) não bateria nessa zona neste dataset específico — mas
  não há garantia disso em datasets reais com estrutura de correlação diferente.
- Um único dataset sintético (2 proxies + 2 ruído). Não testa o caso de 3+
  proxies correlacionadas nem correlação parcial/moderada (entre o cenário
  "fraco" do primeiro experimento e o "quase-duplicado" deste).
