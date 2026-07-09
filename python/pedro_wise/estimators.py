"""Estimadores plugáveis. `LogisticGLM` é o análogo direto de `glm(family=binomial)`
no R — a implementação default, não a única (o protocolo `Estimator` permite trocar
por sklearn, boosting, etc. sem tocar `selection.py`).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
import statsmodels.api as sm


@dataclass(frozen=True)
class _FittedGLM:
    _result: sm.GLM
    variables: tuple[str, ...]

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        X_design = sm.add_constant(X[list(self.variables)], has_constant="add")
        X_design = X_design.reindex(columns=self._result.model.exog_names, fill_value=0.0)
        return np.asarray(self._result.predict(X_design))

    def coeficientes(self) -> dict[str, float]:
        """Coeficientes ajustados, incluindo o intercepto sob a chave
        `"const"` (nome que `statsmodels` usa pra ele) — pra exibir a
        fórmula do modelo final na interface.
        """
        return {str(nome): float(valor) for nome, valor in self._result.params.items()}

    def estatisticas(self) -> dict[str, dict[str, float]]:
        """Coeficiente + erro padrão + p-valor por variável (intercepto sob
        `"const"`) — o Pedro_Wise em si NUNCA usa p-valor pra decidir nada
        (a seleção é 100% guiada por KS, tanto no R original quanto aqui,
        ver `docs/algoritmos-originais/Pedro_Wise_3.0.1.R` — sem qualquer
        `summary()`/teste de significância no laço de busca). Isto aqui é
        só diagnóstico pós-hoc pra exibir na interface, não influencia a
        seleção.
        """
        return {
            str(nome): {
                "coeficiente": float(self._result.params[nome]),
                "erro_padrao": float(self._result.bse[nome]),
                "p_valor": float(self._result.pvalues[nome]),
            }
            for nome in self._result.params.index
        }


class LogisticGLM:
    """GLM binomial (logística) via statsmodels — equivalente a `glm(y ~ ., family=binomial)`."""

    def fit(self, X: pd.DataFrame, y: pd.Series) -> _FittedGLM:
        variables = tuple(X.columns)
        X_design = sm.add_constant(X, has_constant="add")
        result = sm.GLM(y, X_design, family=sm.families.Binomial()).fit()
        return _FittedGLM(_result=result, variables=variables)
