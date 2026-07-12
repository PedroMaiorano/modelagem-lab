"""pipeline_lab — biblioteca de funções soltas pra montar o funil completo
de modelagem de crédito (agregação temporal → interação → categorização →
pré-seleção → Pedro_Wise) em cima de um `pandas.DataFrame` qualquer, sem
depender do backend FastAPI nem do disco.

Cada módulo é uma etapa opcional -- use só as que fizerem sentido pro seu
caso, na ordem abaixo (a única ordem que importa de verdade é Esfera 2
antes de `categorizar_e_transformar`, ver `esfera2` pro motivo):

    from pipeline_lab import divisao, esfera1, esfera2, categorizar, treinamento
    from preselecao import pre_selecionar

    # 1. divisão dev/teste -- a partir de uma coluna de amostra que já
    #    existe no seu dataframe (qualquer rótulo: "DES"/"OOT"/"treino"/...)
    df_dev, df_teste = divisao.dividir_por_amostra(
        df, coluna_amostra="amostra", valores_dev=["DES"], valores_teste=["OOT"]
    )

    # 2. esfera 1 (opcional) -- só se seu dataframe tem várias linhas por
    #    chave (painel). Agrega dev/teste separadamente, preserva o split.
    df_dev, df_teste, colunas_geradas = esfera1.aplicar(
        df_dev, df_teste, chave="id_cliente", coluna_tempo="safra",
        colunas_valor=["dias_atraso"], janelas=[3, 6],
    )

    # 3. esfera 2 (opcional) -- descobre regras de interação, materializa
    #    como coluna 0/1.
    df_dev, df_teste, colunas_regra = esfera2.aplicar(df_dev, df_teste)

    # 4. categorização + WOE -- sempre a última etapa antes da pré-seleção
    #    /treinamento (é aqui que idade_woe, idade_log etc. nascem).
    woe_dev, woe_teste, iv_por_variavel = categorizar.categorizar_e_transformar(df_dev, df_teste)

    # 5. pré-seleção (opcional, já existe pronta em python/preselecao)
    resultado_selecao = pre_selecionar(woe_dev, iv_por_variavel, limiar_iv=0.02)
    woe_dev = woe_dev[[*resultado_selecao["colunas_mantidas"], "y"]]
    woe_teste = woe_teste[[*resultado_selecao["colunas_mantidas"], "y"]]

    # 6. treinamento -- o Pedro_Wise de verdade (forward/backward, níveis 1-3)
    resultado = treinamento.treinar(woe_dev, woe_teste, criterio="teste")
    print(resultado.variaveis, resultado.ks_teste)

Nenhuma função aqui lê/escreve disco, nem sabe o que é FastAPI -- é por
isso que `app/backend/logica.py` e `app/backend/feature_lab.py` importam
daqui em vez de reimplementar (ver módulos lá: eles só adicionam progresso
em tempo real via fila e leitura de `dev.csv`/`teste.csv`, a computação de
verdade mora aqui).
"""

from pipeline_lab import categorizar, divisao, esfera1, esfera2, treinamento

__all__ = ["categorizar", "divisao", "esfera1", "esfera2", "treinamento"]
