from pedro_wise.base import extrair_base, variaveis_disponiveis, versoes_alternativas


def test_extrair_base_pega_prefixo_antes_do_ultimo_underscore():
    assert extrair_base("renda_woe") == "renda"
    assert extrair_base("idade_log") == "idade"
    assert extrair_base("tempo_emprego_log") == "tempo_emprego"


def test_extrair_base_sem_underscore_retorna_a_propria_variavel():
    assert extrair_base("renda") == "renda"


def test_variaveis_disponiveis_exclui_bases_ja_no_modelo():
    todas = ["renda_woe", "renda_log", "idade_woe", "idade_log", "y"]
    disponiveis = variaveis_disponiveis(["renda_woe"], todas)
    # renda_log tem a mesma base (renda) já usada -> não deve aparecer
    assert "renda_log" not in disponiveis
    assert "idade_woe" in disponiveis
    assert "idade_log" in disponiveis
    assert "y" not in disponiveis


def test_versoes_alternativas_retorna_so_a_mesma_base():
    todas = ["renda_woe", "renda_log", "idade_woe", "y"]
    alternativas = versoes_alternativas("renda_woe", todas)
    assert alternativas == ["renda_log"]
