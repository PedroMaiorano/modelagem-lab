"""Descoberta de interação (esfera 3 do feature-lab) — inspirado em RuleFit
(Friedman & Popescu, 2008): treina um ensemble de árvores rasas sobre as
candidatas já construídas (ex.: agregados de `agregacao_temporal`), extrai
os caminhos raiz-folha como regras de interação ("A > x E B > y"), e devolve
as regras como candidatas avaliáveis — não decide nada sozinho, só formaliza
padrões que uma combinação linear simples não capturaria (ver
docs/planos/ — motivação: tendência × severidade recente no atraso, onde o
risco de verdade só aparece quando os DOIS são altos ao mesmo tempo).

Diferença deliberada do RuleFit original: aqui as regras viram candidatas
pro funil que já existe (avaliação via IV, reutilizando `transformacao.woe`
— nunca reimplementado), não pesos de uma regressão L1 própria. Mantém a
esfera 3 desacoplada da seleção final (Pedro_Wise continua sendo quem decide
o que entra no modelo).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal

import pandas as pd
from agregacao_temporal import extrair_base_agregado
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.tree._tree import TREE_UNDEFINED
from transformacao.woe import ajustar_woe

Operador = Literal["<=", ">"]


@dataclass(frozen=True)
class Condicao:
    feature: str
    operador: Operador
    limiar: float


@dataclass(frozen=True)
class Regra:
    """Conjunção de condições extraída de um caminho raiz-folha de uma
    árvore do ensemble — `len(condicoes) >= 2` por construção em
    `extrair_candidatas` (regras de 1 condição só redescobririam binning
    univariado, que já existe em `categorizacao`).
    """

    condicoes: tuple[Condicao, ...]

    @property
    def nome(self) -> str:
        return " & ".join(f"{c.feature}{c.operador}{c.limiar:.4g}" for c in self.condicoes)

    def aplicar(self, df: pd.DataFrame) -> pd.Series:
        """Máscara booleana: linhas que satisfazem TODAS as condições."""
        mascara = pd.Series(True, index=df.index)
        for c in self.condicoes:
            coluna = df[c.feature]
            mascara &= (coluna <= c.limiar) if c.operador == "<=" else (coluna > c.limiar)
        return mascara


def _caminhos_da_arvore(tree_: Any, colunas: list[str]) -> list[tuple[Condicao, ...]]:
    """Percorre a estrutura interna de uma `sklearn.tree.Tree` e devolve
    cada caminho raiz-folha como uma tupla de condições. `feature == TREE_UNDEFINED`
    identifica folhas (constante interna do sklearn, não é -2 mágico).
    """
    caminhos: list[tuple[Condicao, ...]] = []

    def _percorrer(no: int, condicoes: tuple[Condicao, ...]) -> None:
        feature_idx = tree_.feature[no]
        if feature_idx == TREE_UNDEFINED:
            if condicoes:
                caminhos.append(condicoes)
            return
        nome = colunas[feature_idx]
        limiar = float(tree_.threshold[no])
        _percorrer(tree_.children_left[no], (*condicoes, Condicao(nome, "<=", limiar)))
        _percorrer(tree_.children_right[no], (*condicoes, Condicao(nome, ">", limiar)))

    _percorrer(0, ())
    return caminhos


def extrair_candidatas(
    X: pd.DataFrame,
    y: pd.Series,
    profundidade_maxima: int = 3,
    n_arvores: int = 50,
    min_suporte: float = 0.02,
    max_suporte: float = 0.5,
    max_regras: int = 30,
    semente: int | None = 0,
    permitir_cruzamento_entre_bases: bool = True,
    base_de: Callable[[str], str] = extrair_base_agregado,
    proporcao_variaveis_por_split: float | None = None,
) -> list[Regra]:
    """Treina um `GradientBoostingClassifier` raso sobre `X`/`y` e extrai
    regras de interação (>= 2 condições) dos caminhos das árvores.

    `permitir_cruzamento_entre_bases=False` restringe as regras a combinarem
    só primitivas da MESMA variável bruta (ex.: `atraso_tendencia_3m` com
    `atraso_maximo_3m`, nunca com `renda_tendencia_3m`) — útil quando regra
    de negócio não quer misturar domínios diferentes numa única condição
    (fica difícil de explicar/auditar). `base_de` identifica a variável
    bruta por trás do nome da coluna; o default (`extrair_base_agregado`)
    reverte a convenção de nomes de `agregacao_temporal.construir_agregados_janela` —
    troque se suas colunas seguirem outra convenção.

    Filtros aplicados, nessa ordem:
    - só caminhos com 2+ condições **sobre 2+ variáveis distintas** --
      uma árvore CART pode cortar a mesma coluna duas vezes no mesmo
      caminho (um corte perto da raiz, outro mais fino depois, refinando
      a mesma variável); isso teria 2+ condições mas é só binning
      univariado disfarçado (o corte mais apertado já implica o outro),
      não a interação que esta função existe pra achar;
    - se `permitir_cruzamento_entre_bases=False`, descarta caminhos cujas
      condições vêm de mais de uma base;
    - deduplicação exata (a mesma regra, mesmo limiar, pode aparecer em
      várias árvores);
    - suporte entre `min_suporte` e `max_suporte` (fração de linhas que
      satisfaz a regra) — descarta regras triviais (quase sempre ou quase
      nunca verdadeiras, pouco informativas ou superajustadas a poucos casos);
    - quase-duplicatas: a mesma combinação de variáveis+direção (ex.:
      `cloud<=61.5` e `cloud<=64.5`) reaparece com limiar ligeiramente
      diferente em árvores treinadas em subamostras diferentes — mantém só a
      de maior IV por "assinatura" (variáveis+operadores, ignorando o
      limiar), senão a tabela final fica cheia de linhas quase idênticas;
    - ranking por IV (via `transformacao.woe.ajustar_woe`, tratando a regra
      como variável binária), truncado em `max_regras`.

    `proporcao_variaveis_por_split`: sem isso (`None`), toda árvore vê todas
    as colunas em cada split -- se uma variável for muito mais forte que as
    outras, ela vence a disputa em praticamente toda árvore, e combinações
    envolvendo variáveis mais fracas nunca chegam a ser testadas (a árvore
    nem cogita usá-las). É o mesmo problema que motiva o `max_features` do
    Random Forest. Um valor tipo `0.5`-`0.7` limita cada split a uma amostra
    aleatória das colunas, dando chance de variáveis mais fracas aparecerem
    em algumas árvores mesmo com uma dominante no conjunto.
    """
    gbm = GradientBoostingClassifier(
        n_estimators=n_arvores,
        max_depth=profundidade_maxima,
        subsample=0.8,
        max_features=proporcao_variaveis_por_split,
        random_state=semente,
    )
    gbm.fit(X, y)

    colunas = list(X.columns)
    vistas: set[frozenset[tuple[str, Operador, float]]] = set()
    candidatas: list[Regra] = []

    for arvore in gbm.estimators_[:, 0]:
        for caminho in _caminhos_da_arvore(arvore.tree_, colunas):
            if len(caminho) < 2:
                continue
            if len({c.feature for c in caminho}) < 2:
                # Mesma variável cortada 2+ vezes no caminho (ex.: x>28.5
                # E x>57.5) -- o corte mais apertado já implica o mais
                # frouxo, então isso é só um bin univariado com 2 nomes,
                # não uma interação real entre variáveis diferentes.
                continue
            if not permitir_cruzamento_entre_bases:
                bases = {base_de(c.feature) for c in caminho}
                if len(bases) > 1:
                    continue
            chave = frozenset((c.feature, c.operador, round(c.limiar, 6)) for c in caminho)
            if chave in vistas:
                continue
            vistas.add(chave)
            candidatas.append(Regra(caminho))

    avaliadas = []
    for regra in candidatas:
        mascara = regra.aplicar(X)
        suporte = float(mascara.mean())
        if not (min_suporte <= suporte <= max_suporte):
            continue
        iv = ajustar_woe(mascara.astype(str), y).iv_total
        avaliadas.append((iv, regra))

    melhor_por_assinatura: dict[frozenset[tuple[str, Operador]], tuple[float, Regra]] = {}
    for iv, regra in avaliadas:
        assinatura = frozenset((c.feature, c.operador) for c in regra.condicoes)
        atual = melhor_por_assinatura.get(assinatura)
        if atual is None or iv > atual[0]:
            melhor_por_assinatura[assinatura] = (iv, regra)

    avaliadas_unicas = sorted(melhor_por_assinatura.values(), key=lambda par: par[0], reverse=True)
    return [regra for _, regra in avaliadas_unicas[:max_regras]]


def regras_para_colunas(regras: list[Regra], df: pd.DataFrame, sufixo: str = "_regra") -> pd.DataFrame:
    """Materializa cada regra como uma coluna 0/1 nomeada `{nome_da_regra}{sufixo}`
    — pronto pra entrar no funil existente (pré-seleção, Pedro_Wise)."""
    return pd.DataFrame({f"{r.nome}{sufixo}": r.aplicar(df).astype(int) for r in regras}, index=df.index)
