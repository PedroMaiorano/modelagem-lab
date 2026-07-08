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


class LogisticGLM:
    """GLM binomial (logística) via statsmodels — equivalente a `glm(y ~ ., family=binomial)`."""

    def fit(self, X: pd.DataFrame, y: pd.Series) -> _FittedGLM:
        variables = tuple(X.columns)
        X_design = sm.add_constant(X, has_constant="add")
        result = sm.GLM(y, X_design, family=sm.families.Binomial()).fit()
        return _FittedGLM(_result=result, variables=variables)
