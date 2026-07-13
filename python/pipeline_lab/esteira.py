"""`Esteira` — builder mutável e encadeável por cima das funções soltas de
`pipeline_lab` (`divisao`, `construcao`, `agregacao_temporal`, `interacao`,
`categorizar`, `preselecao`, `treinamento`). Existe porque cada uma dessas
funções devolve um formato diferente (tuple de 2, tuple de 3, dict,
dataclass) — compor a esteira manualmente exige desempacotar cada retorno
do jeito certo e manter `df_dev`/`df_teste` sincronizados na mão. `Esteira`
guarda esse estado, e cada etapa encadeia com `.metodo()`, devolvendo
`self` (exceto `treinar`, que é terminal e devolve o resultado).

Nenhuma função funcional foi removida ou alterada -- quem já usa o estilo
`divisao.dividir_por_amostra(...)` direto continua funcionando; `Esteira`
é só uma camada de conveniência por cima.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from pipeline_lab import (
    agregacao_temporal,
    categorizar,
    construcao,
    divisao,
    interacao,
    preselecao,
    treinamento,
)
from pipeline_lab.treinamento import ResultadoTreinamento


class EtapaForaDeOrdemError(RuntimeError):
    """Uma etapa que precisa rodar ANTES de `categorizar_e_transformar()`
    foi chamada depois dela. Motivo: a partir da categorização, as colunas
    passam a ter versões alternativas da mesma base (`_woe`, `_log`,
    `_bin`...) -- `construir_razoes`/`agregar_temporal`/`descobrir_interacoes`
    esperam as colunas originais, não essas derivadas."""


class Esteira:
    """Estado de uma esteira de modelagem em construção: `df_dev`/`df_teste`
    mais os artefatos que cada etapa produz, disponíveis como atributos pra
    inspeção (`iv_por_variavel`, `iv_teste_por_variavel`, `colunas_geradas`,
    `resultado_selecao`, `resultado_treinamento`).
    """

    def __init__(self, df_dev: pd.DataFrame, df_teste: pd.DataFrame) -> None:
        self.df_dev = df_dev
        self.df_teste = df_teste
        self.colunas_geradas: dict[str, list[str]] = {}
        self.iv_por_variavel: dict[str, float] | None = None
        self.iv_teste_por_variavel: dict[str, float] | None = None
        self.resultado_selecao: dict[str, Any] | None = None
        self.resultado_treinamento: ResultadoTreinamento | None = None
        self._categorizado = False

    @classmethod
    def dividir_por_amostra(
        cls,
        df: pd.DataFrame,
        coluna_amostra: str,
        valores_dev: list[str],
        valores_teste: list[str],
        coluna_y: str | None = None,
    ) -> Esteira:
        """Ponto de entrada a partir de um dataframe com uma coluna de
        amostra já existente. Ver `pipeline_lab.divisao.dividir_por_amostra`."""
        df_dev, df_teste = divisao.dividir_por_amostra(
            df, coluna_amostra, valores_dev, valores_teste, coluna_y
        )
        return cls(df_dev, df_teste)

    @classmethod
    def dividir_aleatorio(
        cls,
        df: pd.DataFrame,
        proporcao_teste: float = 0.5,
        semente: int = 42,
        coluna_y: str | None = None,
    ) -> Esteira:
        """Ponto de entrada com split aleatório simples. Ver
        `pipeline_lab.divisao.dividir_aleatorio`."""
        df_dev, df_teste = divisao.dividir_aleatorio(df, proporcao_teste, semente, coluna_y)
        return cls(df_dev, df_teste)

    def _checar_nao_categorizado(self, nome_etapa: str) -> None:
        if self._categorizado:
            raise EtapaForaDeOrdemError(
                f"{nome_etapa}() precisa rodar ANTES de categorizar_e_transformar() "
                "-- ver docstring de EtapaForaDeOrdemError."
            )

    def construir_razoes(
        self, pares: list[tuple[str, str, str]], epsilon: float = 1e-6
    ) -> Esteira:
        """Razões/diferenças interpretáveis entre pares de colunas (ex.:
        `pago/fatura`). Aplica em dev e teste internamente com os mesmos
        parâmetros -- ver `pipeline_lab.construcao.construir_razoes_em_lote`."""
        self._checar_nao_categorizado("construir_razoes")
        novas_dev = construcao.construir_razoes_em_lote(self.df_dev, pares, epsilon)
        novas_teste = construcao.construir_razoes_em_lote(self.df_teste, pares, epsilon)
        self.df_dev = pd.concat([self.df_dev, novas_dev], axis=1)
        self.df_teste = pd.concat([self.df_teste, novas_teste], axis=1)
        self.colunas_geradas["construcao"] = list(novas_dev.columns)
        return self

    def agregar_temporal(
        self,
        chave: str,
        coluna_tempo: str,
        colunas_valor: list[str],
        janelas: list[int],
    ) -> Esteira:
        """Behavioral scoring: agrega um painel (várias linhas por chave)
        a uma linha por chave via janelas móveis. Ver
        `pipeline_lab.agregacao_temporal.aplicar`."""
        self._checar_nao_categorizado("agregar_temporal")
        self.df_dev, self.df_teste, geradas = agregacao_temporal.aplicar(
            self.df_dev, self.df_teste, chave, coluna_tempo, colunas_valor, janelas
        )
        self.colunas_geradas["agregacao_temporal"] = geradas
        return self

    def descobrir_interacoes(self, **kwargs: Any) -> Esteira:
        """Descoberta de regras de interação estilo RuleFit. Ver
        `pipeline_lab.interacao.aplicar` pros hiperparâmetros aceitos em
        `**kwargs` (profundidade_maxima, n_arvores, min_suporte, ...)."""
        self._checar_nao_categorizado("descobrir_interacoes")
        self.df_dev, self.df_teste, geradas = interacao.aplicar(self.df_dev, self.df_teste, **kwargs)
        self.colunas_geradas["interacao"] = geradas
        return self

    def categorizar_e_transformar(self, **kwargs: Any) -> Esteira:
        """Binning monotônico + WOE/IV -- sempre a última etapa antes da
        pré-seleção/treinamento. Ver
        `pipeline_lab.categorizar.categorizar_e_transformar`. Preenche
        `iv_por_variavel` (dev, usado por `pre_selecionar`) e
        `iv_teste_por_variavel` (diagnóstico -- compare os dois pra flagar
        variável com bin overfitado)."""
        resultado = categorizar.categorizar_e_transformar(self.df_dev, self.df_teste, **kwargs)
        self.df_dev = resultado.woe_dev
        self.df_teste = resultado.woe_teste
        self.iv_por_variavel = resultado.iv_dev_por_variavel
        self.iv_teste_por_variavel = resultado.iv_teste_por_variavel
        self._categorizado = True
        return self

    def pre_selecionar(self, **kwargs: Any) -> Esteira:
        """Filtros de variância/IV/correlação, já aplicando o fatiamento de
        colunas resultante em `df_dev`/`df_teste`. Ver
        `pipeline_lab.preselecao.pre_selecionar`."""
        if self.iv_por_variavel is None:
            raise EtapaForaDeOrdemError(
                "pre_selecionar() precisa rodar depois de categorizar_e_transformar() "
                "-- é de lá que vem iv_por_variavel."
            )
        self.resultado_selecao = preselecao.pre_selecionar(self.df_dev, self.iv_por_variavel, **kwargs)
        colunas = [*self.resultado_selecao["colunas_mantidas"], "y"]
        self.df_dev = self.df_dev[colunas]
        self.df_teste = self.df_teste[colunas]
        return self

    def treinar(self, **kwargs: Any) -> ResultadoTreinamento:
        """Etapa terminal: roda o Pedro_Wise sobre o estado atual da
        esteira. Ver `pipeline_lab.treinamento.treinar` pros hiperparâmetros
        de cada nível de busca."""
        self.resultado_treinamento = treinamento.treinar(self.df_dev, self.df_teste, **kwargs)
        return self.resultado_treinamento
