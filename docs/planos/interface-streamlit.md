# Decisão: interface (pilar 3) — Streamlit

> Registrado ao ativar a skill `scaffold-interface` (2026-07-08).

## As 3 respostas de calibração (skill `scaffold-interface`)

1. **Público/uso**: exploração pessoal rápida — rodar o Pedro_Wise num
   dataset e ver a seleção/KS, não servir para terceiros.
2. **Forma**: dashboard interativo — visualizar seleção de variáveis, KS,
   trace da busca.
3. **Ecossistema**: o core vive em `python/pedro_wise` — Python.

→ Framework: **Streamlit** (default da skill para "quero ver meus modelos").

## Estrutura criada

```
app/
├── streamlit_app.py   # entrypoint — só widgets/exibição
├── logica.py           # consome python/pedro_wise; nenhuma lógica de seleção aqui
└── requirements.txt
```

`logica.py` é a fronteira: `streamlit_app.py` nunca importa `pedro_wise`
diretamente, só via `logica.rodar_selecao()`. Mantém a regra da skill —
"a interface consome o arcabouço, não reimplementa modelagem".

## Caminho end-to-end validado

1. Lista datasets em `data/*/` (pastas com `dev.csv`+`teste.csv`, geradas
   pelos `scripts/gerar_*.py`).
2. Sidebar configura critério de parada, flags de nível 1/2, shadow probing.
3. Roda `run_pedro_wise` via `logica.rodar_selecao()`.
4. Mostra KS-dev/teste, AUC, variáveis selecionadas, gráfico de progresso do
   KS ao longo da busca, e o trace completo em tabela.

Testado: `python -m streamlit run app/streamlit_app.py` sobe, `/healthz`
responde `ok`, e `logica.rodar_selecao()` chamada diretamente (fora do
Streamlit) reproduz o mesmo resultado dos scripts de experimento — ex. no
dataset `experimento_colinearidade`: seleciona `xa_woe, xb_woe, x_ruido_woe`,
KS-teste=0.5121, AUC=0.829 (bate com
`docs/experimentos/colinearidade-stability-selection.md`).

## Uso

```bash
pip install -r app/requirements.txt
python -m streamlit run app/streamlit_app.py
```

**Nota Windows**: use `python -m streamlit run ...`, não `streamlit run ...`
direto — nesta máquina o executável `streamlit` no PATH resolvia para um
ambiente Python diferente (3.12) daquele onde o pacote foi instalado (3.14),
causando falha silenciosa. `python -m streamlit` sempre usa o interpretador
correto.

## Não fiz (escopo do v1)

- Sem comparação embutida com LASSO/stability selection na UI — os scripts
  em `scripts/experimento_*.py` continuam sendo o caminho para isso; pode
  virar uma aba futura se for útil no dia a dia.
- Sem upload de CSV arbitrário — só datasets já gerados em `data/`. Trivial
  de adicionar (`st.file_uploader`) quando precisar.
- Sem paleta/tema customizado (skill `dataviz` consultada; para uma
  ferramenta pessoal de um usuário só, os componentes padrão do Streamlit
  foram considerados suficientes — não há necessidade de validar uma paleta
  de marca aqui). O gráfico de progresso do KS é uma série única (sem
  legenda necessária) via `st.line_chart`.
