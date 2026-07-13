"""pipeline_lab — biblioteca de funções soltas pra montar o funil completo
de modelagem de crédito (divisão → construção → agregação temporal →
interação → categorização → pré-seleção → Pedro_Wise) em cima de um
`pandas.DataFrame` qualquer, sem depender do backend FastAPI nem do disco.

Cada módulo é uma etapa opcional -- use só as que fizerem sentido pro seu
caso, na ordem abaixo (a única ordem que importa de verdade é `interacao`
antes de `categorizar_e_transformar`, ver `interacao` pro motivo). Todo
hiperparâmetro que a interface expõe pra cada etapa está disponível aqui
como argumento nomeado da função -- não há nada escondido só na UI.

Duas formas de usar: o estilo funcional abaixo (cada passo é uma chamada
solta, você mesmo encadeia os retornos) ou `Esteira`, um builder que já
encadeia tudo isso e guarda o estado (`df_dev`/`df_teste`/artefatos
intermediários) por você -- ver `pipeline_lab.esteira.Esteira`.

    from pipeline_lab import divisao, agregacao_temporal, interacao, construcao
    from pipeline_lab import categorizar, preselecao, treinamento

    # 1. divisão dev/teste -- a partir de uma coluna de amostra que já
    #    existe no seu dataframe (qualquer rótulo: "DES"/"OOT"/"treino"/...).
    #    `coluna_y` já renomeia sua coluna de resposta pra "y" (o nome que
    #    todo o resto do pipeline exige) -- não precisa de rename manual.
    df_dev, df_teste = divisao.dividir_por_amostra(
        df, coluna_amostra="amostra", valores_dev=["DES"], valores_teste=["OOT"],
        coluna_y="target",
    )

    # 2. construção (opcional) -- razões/diferenças interpretáveis entre
    #    pares de colunas relacionadas (ex.: pago/fatura). Não é busca
    #    automática, você diz quais pares fazem sentido de negócio.
    df_dev = pd.concat([df_dev, construcao.construir_razoes_em_lote(
        df_dev, pares=[("pago", "fatura", "pct_pago")]
    )], axis=1)
    df_teste = pd.concat([df_teste, construcao.construir_razoes_em_lote(
        df_teste, pares=[("pago", "fatura", "pct_pago")]
    )], axis=1)

    # 3. agregação temporal (opcional) -- só se seu dataframe tem várias
    #    linhas por chave (painel). Agrega dev/teste separadamente,
    #    preserva o split.
    df_dev, df_teste, colunas_geradas = agregacao_temporal.aplicar(
        df_dev, df_teste, chave="id_cliente", coluna_tempo="safra",
        colunas_valor=["dias_atraso"], janelas=[3, 6],
    )

    # 4. interação (opcional) -- descobre regras de interação, materializa
    #    como coluna 0/1. Todos os hiperparâmetros da UI (profundidade,
    #    n_arvores, min/max suporte, max_regras, iv_minimo etc.) são
    #    argumentos aqui -- ver `interacao.aplicar`.
    df_dev, df_teste, colunas_regra = interacao.aplicar(df_dev, df_teste)

    # 5. categorização + WOE -- sempre a última etapa antes da pré-seleção
    #    /treinamento (é aqui que idade_woe, idade_log etc. nascem).
    #    ResultadoCategorizacao.iv_teste_por_variavel é diagnóstico (compara
    #    com iv_dev_por_variavel pra flagar bin overfitado), não é usado
    #    pra filtrar nada abaixo.
    resultado_cat = categorizar.categorizar_e_transformar(df_dev, df_teste)
    woe_dev, woe_teste = resultado_cat.woe_dev, resultado_cat.woe_teste

    # 6. pré-seleção (opcional) -- variância → IV → correlação, cada
    #    limiar configurável (ou `None` pra pular o filtro).
    resultado_selecao = preselecao.pre_selecionar(
        woe_dev, resultado_cat.iv_dev_por_variavel, limiar_iv=0.02
    )
    woe_dev = woe_dev[[*resultado_selecao["colunas_mantidas"], "y"]]
    woe_teste = woe_teste[[*resultado_selecao["colunas_mantidas"], "y"]]

    # 7. treinamento -- o Pedro_Wise de verdade (forward/backward, níveis
    #    1-3). Todos os hiperparâmetros de cada nível (criterio,
    #    shadow_probing, min_vars_para_backward, n_best_duplo,
    #    nivel3_ativado, p_valor_maximo etc.) são argumentos aqui -- ver
    #    `treinamento.treinar`.
    resultado = treinamento.treinar(woe_dev, woe_teste, criterio="teste")
    print(resultado.variaveis, resultado.ks_teste)

O mesmo funil via `Esteira` (equivalente aos 7 passos acima, sem
desempacotar retorno nenhum na mão):

    from pipeline_lab import Esteira

    resultado = (
        Esteira.dividir_por_amostra(df, coluna_amostra="amostra", valores_dev=["DES"],
                                     valores_teste=["OOT"], coluna_y="target")
        .construir_razoes(pares=[("pago", "fatura", "pct_pago")])
        .agregar_temporal(chave="id_cliente", coluna_tempo="safra",
                           colunas_valor=["dias_atraso"], janelas=[3, 6])
        .descobrir_interacoes()
        .categorizar_e_transformar()
        .pre_selecionar(limiar_iv=0.02)
        .treinar(criterio="teste")
    )
    print(resultado.variaveis, resultado.ks_teste)

Nenhuma função aqui lê/escreve disco, nem sabe o que é FastAPI -- é por
isso que `app/backend/logica.py` e `app/backend/feature_lab.py` importam
daqui em vez de reimplementar (ver módulos lá: eles só adicionam progresso
em tempo real via fila e leitura de `dev.csv`/`teste.csv`, a computação de
verdade mora aqui).
"""

from pipeline_lab import (
    agregacao_temporal,
    categorizar,
    construcao,
    divisao,
    interacao,
    preselecao,
    treinamento,
)
from pipeline_lab.esteira import Esteira, EtapaForaDeOrdemError

__all__ = [
    "agregacao_temporal",
    "categorizar",
    "construcao",
    "divisao",
    "interacao",
    "preselecao",
    "treinamento",
    "Esteira",
    "EtapaForaDeOrdemError",
]
