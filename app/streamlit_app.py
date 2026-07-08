"""Dashboard exploratório do Pedro_Wise — pilar 3 (interface) do modelagem-lab.

Uso: `streamlit run app/streamlit_app.py` (a partir da raiz do repo).

Consome `python/pedro_wise` via `app/logica.py` — não reimplementa seleção
nem métricas aqui, só orquestra widgets e exibição.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st
from logica import carregar_dataset, listar_datasets, rodar_selecao

st.set_page_config(page_title="Pedro_Wise — modelagem-lab", layout="wide")
st.title("Pedro_Wise — dashboard exploratório")
st.caption("Pilar 3 do modelagem-lab. Roda o port Python sobre um dataset e visualiza a seleção.")

datasets = listar_datasets()

with st.sidebar:
    st.header("Dataset")
    if not datasets:
        st.error(
            "Nenhum dataset em `data/`. Rode um gerador primeiro, ex.:\n\n"
            "`python scripts/gerar_dataset_validacao.py`"
        )
        st.stop()
    nome_dataset = st.selectbox("Pasta em data/", datasets)

    st.header("Critério de parada")
    criterio = st.radio(
        "Métrica de decisão (KS-Gaussiano)",
        options=["teste", "dev", "min"],
        index=0,
        help="'min' penaliza candidatas que só melhoram num dos dois splits — mais conservador.",
    )
    shadow_probing = st.toggle(
        "Shadow probing", value=False, help="Para o forward quando uma variável permutada venceria a rodada."
    )

    st.header("Nível 1")
    forward_simples = st.checkbox("Forward simples", value=True)
    transformacao_simples = st.checkbox("Transformação simples", value=True)
    backward_simples = st.checkbox("Backward simples", value=True)

    st.header("Nível 2 / 2.5")
    forward_duplo = st.checkbox("Forward duplo", value=True)
    forward_triplo = st.checkbox("Forward triplo", value=True)
    n_best_duplo = st.number_input("n_best_duplo", min_value=1, max_value=20, value=5)
    n_best_triplo_1 = st.number_input("n_best_triplo_1", min_value=1, max_value=10, value=3)
    n_best_triplo_2 = st.number_input("n_best_triplo_2", min_value=1, max_value=10, value=3)

    rodar = st.button("Rodar seleção", type="primary")

df_dev, df_teste = carregar_dataset(nome_dataset)

col_info, col_preview = st.columns([1, 2])
with col_info:
    st.metric("Linhas (dev)", len(df_dev))
    st.metric("Linhas (teste)", len(df_teste))
    st.metric("Candidatas", len(df_dev.columns) - 1)
with col_preview:
    st.dataframe(df_dev.head(5), width="stretch")

if rodar:
    with st.spinner("Rodando Pedro_Wise..."):
        resultado = rodar_selecao(
            df_dev,
            df_teste,
            criterio=criterio,
            forward_simples=forward_simples,
            transformacao_simples=transformacao_simples,
            backward_simples=backward_simples,
            forward_duplo=forward_duplo,
            forward_triplo=forward_triplo,
            shadow_probing=shadow_probing,
            n_best_duplo=n_best_duplo,
            n_best_triplo_1=n_best_triplo_1,
            n_best_triplo_2=n_best_triplo_2,
        )

    st.subheader("Resultado")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("KS (dev)", f"{resultado.ks_dev:.4f}")
    c2.metric("KS (teste)", f"{resultado.ks_teste:.4f}")
    c3.metric("AUC (teste)", f"{resultado.auc_teste:.3f}")
    c4.metric("Variáveis selecionadas", len(resultado.variaveis))

    if resultado.variaveis:
        st.write("**Variáveis selecionadas:**", ", ".join(resultado.variaveis))
    else:
        st.warning("Nenhuma variável selecionada.")

    if resultado.ks_por_passo:
        st.subheader("Progresso do KS ao longo da busca")
        serie = pd.Series(resultado.ks_por_passo, name="KS", index=range(1, len(resultado.ks_por_passo) + 1))
        serie.index.name = "passo"
        st.line_chart(serie)

    st.subheader("Trace da busca")
    if resultado.eventos:
        st.dataframe(pd.DataFrame({"evento": resultado.eventos}), width="stretch")
    else:
        st.caption("Nenhuma atualização aceita (modelo nulo permaneceu o melhor).")
else:
    st.info("Configure na barra lateral e clique em **Rodar seleção**.")
