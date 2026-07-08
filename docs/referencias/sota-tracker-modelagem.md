# SOTA Tracker — Modelagem Estatística / ML

> Coração do lab. Estado da arte para seleção de variáveis, construção de modelos e
> análises. Ancore recomendações do `stats-advisor` aqui. Atualize via `buscar-literatura`
> quando encostar em técnica não listada.
>
> **Última verificação**: 2026-07-07 · **Próxima revisão sugerida**: 2026-10-07

---

## 1. Seleção de Variáveis

Três famílias: **filtro** (independente do modelo), **wrapper** (usa o modelo — é onde
o Pedro_Wise vive), **embedded** (seleção durante o treino — o SOTA atual).

### Wrapper (clássico) — onde o Pedro_Wise se encaixa
- **Stepwise (forward/backward/both)**: greedy, interpretável, guiável por métrica de
  negócio (KS). Fraquezas: instável, ótimo local, caro (refit por candidata), ruim em
  alta dimensão. O Pedro_Wise é um stepwise multi-nível sofisticado — seu diferencial é
  otimizar KS e explorar transformações da mesma variável-base.

### Embedded / Regularização (SOTA prático)
- **LASSO (L1)**: seleção + shrinkage num fit; zera coeficientes irrelevantes.
- **Elastic Net (L1+L2)**: melhor sob colinearidade e grupos de variáveis correlacionadas.
- **SCAD / MCP**: penalidades não-convexas que reduzem o viés do LASSO nos coeficientes grandes.
- **Group LASSO**: seleção em grupos (útil para dummies de uma categórica, ou versões de uma base).
- Trade-off: escolha de λ (via CV), viés de shrinkage, pressupõe estrutura (quase-)linear.

### Boosting como seleção
- **Component-wise / model-based boosting** (`mboost`): forward stagewise para GLM, Cox,
  quantílica. Em cada passo atualiza só o coeficiente do melhor modelo univariável
  condicional. **Early stopping = seleção + shrinkage tipo LASSO.** Bom em alta dimensão
  com estrutura aditiva.
- **Importância em gradient boosting** (LightGBM/XGBoost/CatBoost) + SHAP: seleção
  não-linear; cuidado com viés a favor de variáveis de alta cardinalidade.

### Robustez / controle de falsos positivos (SOTA)
- **Stability selection**: reamostra e mantém variáveis selecionadas com frequência
  alta; controla falsos positivos. Competitiva com o SOTA em alta dimensão.
  Ver síntese completa em [`docs/literatura/stability-selection.md`](../literatura/stability-selection.md).
  **Cautela** (Faletto & Bien 2022): com lasso puro, falha quando há proxies
  correlacionados de um fator latente — nenhum atinge frequência alta individualmente,
  podendo ficar pior que o método base sem estabilização. Use *cluster stability
  selection* (agrupar variáveis correlacionadas antes) quando esse cenário for
  plausível. Não é o mesmo problema que a semântica de "base" do Pedro_Wise resolve
  (essa agrupa *transformações da mesma variável*, não variáveis diferentes e
  correlacionadas) — mecanismos complementares.
- **Shadow-variable probing**: aumenta os dados com versões permutadas ("shadow") e para
  o forward quando uma shadow entraria — seleção em um único fit, **quase sem tuning**.

### Bayesiano
- **Spike-and-slab**, **horseshoe prior**: seleção via priors esparsos; quantifica
  incerteza da seleção. Custo computacional maior (MCMC/VI).

---

## 2. Construção de Modelos

### GLMs e regressão penalizada
- **statsmodels** para inferência (coeficientes, p-valores, IC) — interpretabilidade.
- **scikit-learn** (`LogisticRegression` L1/L2/elasticnet, `LassoCV`, `ElasticNetCV`)
  para predição/pipeline.

### Gradient boosting tabular (padrão-forte)
- **LightGBM / XGBoost / CatBoost**: SOTA para tabular estruturado. `predict_proba`
  **mal calibrado por padrão** → `CalibratedClassifierCV` (isotonic/sigmoid) ou calibração
  pós-treino em conjunto separado. Reporte **Brier** + curva de calibração.

### AutoML (baseline forte, SOTA 2025)
- **AutoGluon (1.2+)**: SOTA no AutoML Benchmark 2025; stacking multi-camada em vez de só
  HPO. Vence com 5 min o que outros fazem em 1h; muito estável. Use como piso de desempenho.
- **FLAML**: custo-eficiente (ordena trials do mais barato ao mais caro).
- **TabPFN**: transformer pré-treinado para datasets tabulares pequenos; resultados
  competitivos em segundos, com priors "causal-inspired".
- **MLZero / AutoGluon Assistant**: AutoML agêntico (LLM multi-agente) end-to-end — fronteira 2025.
- Limite: caixa-preta. Baseline e sanity check, não resposta final quando interpretabilidade manda.

---

## 3. Inferência Causal (preditivo ≠ causal)

Se a pergunta é sobre **efeito/intervenção**, seleção preditiva de variáveis é armadilha.
- **Double / Debiased Machine Learning (DML)**: `DoubleML`, `EconML`. Usa ML para nuisance
  (propensão, outcome) com ortogonalização + cross-fitting → estimativa de efeito com
  garantias.
- **CausalML** (Uber): uplift/CATE.
- AutoML para causal ainda é imaturo (ex.: OpportunityFinder), mas priors causais já
  aparecem em modelos tabulares (TabPFN).

---

## 4. Avaliação e Validação (transversal)

- **Anti-leakage**: seleção e tuning DENTRO do fold; nada de olhar o teste antes.
- **Temporal**: `TimeSeriesSplit` / walk-forward quando há ordem.
- **Métrica casada ao problema**: classificação de risco → KS/Gini/AUC + calibração
  (Brier); regressão → RMSE/MAE/R²aj; seleção → AIC/BIC vs. métrica de validação.
- **Estabilidade da seleção**: rode a seleção em reamostragens e reporte frequência das variáveis.

---

## 5. Conexão com o Pedro_Wise (pilar 1)

O Pedro_Wise é um wrapper stepwise otimizando KS. No port Python, ele deve **conviver**
com as alternativas acima: métrica plugável abre caminho para AUC/Gini/log-loss/AIC/BIC;
estimador plugável abre para boosting. Comparar o Pedro_Wise portado contra LASSO/elastic
net e stability selection no mesmo dataset é um experimento natural do lab.

---

## Referências (fontes abertas)
- Review de seleção de variáveis (MDPI Mathematics 2025): https://www.mdpi.com/2227-7390/13/6/996
- Boosting para seleção esparsa e rápida (probing): https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5555005/
- Boosting: regularization, prediction, model fitting (Bühlmann/Hothorn): https://arxiv.org/pdf/0804.2752
- Feature selection via regularized trees: https://arxiv.org/pdf/1201.1587
- AutoGluon (SOTA AutoML tabular 2025): https://github.com/autogluon/autogluon
- Avaliação prática de AutoML (Sci Reports 2025): https://www.nature.com/articles/s41598-025-02149-x
