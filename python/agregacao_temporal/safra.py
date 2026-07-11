"""Normalização de safra (período de referência) — fontes reais de painel
mensal chegam em formatos inconsistentes (`anomes` inteiro `202401`,
string `"2024-01"`, `"2024-01-15"` com dia, `datetime`/`Timestamp`...).
`construir_agregados_janela` só precisa de uma coluna ordenável por chave;
`normalizar_safra` converte qualquer um desses formatos pra um inteiro
`AAAAMM` comparável, resolvendo isso uma vez só antes de agregar — mantém
`primitivas.py` agnóstico de formato de data (só ordena o que já chegou
normalizado).
"""

from __future__ import annotations

import re

import pandas as pd

_PADRAO_ANOMES = re.compile(r"^\d{6}$")


def normalizar_safra(serie: pd.Series) -> pd.Series:
    """Converte uma coluna de safra em qualquer formato comum (`anomes` int
    `202401`, string `"202401"`, `"2024-01"`, `"2024-01-15"`, `datetime`/
    `Timestamp`) para inteiro `AAAAMM` — ordenável e comparável entre
    formatos diferentes na mesma base (útil quando fontes distintas do
    painel trazem safra em formatos diferentes).

    Levanta `ValueError` se algum valor não for reconhecível em nenhum dos
    formatos suportados, em vez de silenciosamente virar `NaT`/`NaN` (erro
    de parsing de data é o tipo de bug que só aparece muito depois, numa
    janela móvel com contagem errada).
    """
    valores_texto = serie.astype(str).str.strip()

    eh_anomes = valores_texto.str.match(_PADRAO_ANOMES)
    resultado = pd.Series(index=serie.index, dtype="Int64")
    resultado[eh_anomes] = valores_texto[eh_anomes].astype("int64")

    restante = valores_texto[~eh_anomes]
    if len(restante) > 0:
        # format="mixed": sem isso, pandas infere UM formato a partir do
        # primeiro valor e aplica pra série inteira -- quebra silenciosamente
        # (vira NaT) quando a mesma coluna mistura "2024-02" e "2024-03-15"
        # (cenário real citado: fontes diferentes do mesmo painel).
        datas = pd.to_datetime(restante, errors="coerce", format="mixed")
        invalidos = datas.isna()
        if invalidos.any():
            exemplos = restante[invalidos].unique()[:5]
            raise ValueError(f"Safra em formato não reconhecido: {list(exemplos)}")
        resultado[restante.index] = (datas.dt.year * 100 + datas.dt.month).astype("int64")

    return resultado.astype("int64")
