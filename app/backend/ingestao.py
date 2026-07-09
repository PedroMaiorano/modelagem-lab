"""Ingestão de datasets via upload: detecção de tipo/data por coluna e as 3
estratégias de split (coluna de amostra já existente, OOT por data,
aleatório). Depois de "preparado", o dataset vira `data/<nome>/{dev,teste}.csv`
— exatamente o formato que `logica.py` (e todo o resto do backend) já
consome, sem duplicar nenhuma lógica de pipeline aqui.

Fluxo: `POST /api/dataset/upload` (grava um CSV bruto em staging + detecta
colunas) → usuário configura resposta/split no frontend → `POST
/api/dataset/preparar` (aplica o split escolhido, grava a versão final).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import pandas as pd

_RAIZ = Path(__file__).resolve().parent.parent.parent
DIR_DADOS = _RAIZ / "data"
DIR_STAGING = DIR_DADOS / "_uploads_staging"

# (formato strptime, comprimento de string esperado) — o comprimento filtra
# falsos positivos (ex.: uma coluna de idade "20", "45" não deve "parecer"
# um "%Y%m" só porque tem dígitos).
FORMATOS_DATA: list[tuple[str, int]] = [
    ("%Y%m%d", 8),
    ("%Y%m", 6),
    ("%Y-%m-%d", 10),
    ("%Y/%m/%d", 10),
    ("%d-%m-%Y", 10),
    ("%d/%m/%Y", 10),
    ("%m-%d-%Y", 10),
    ("%m/%d/%Y", 10),
    ("%Y-%m", 7),
    ("%Y/%m", 7),
]

TaxaSucessoMinima = 0.95


@dataclass
class ColunaDetectada:
    nome: str
    tipo: Literal["numerico", "data", "categorico"]
    formato_data: str | None = None
    n_distintos: int = 0
    exemplos: list[Any] = field(default_factory=list)


def _detectar_formato_data(serie: pd.Series) -> str | None:
    """Tenta os formatos cujo comprimento de string bate com o comprimento
    típico (moda) dos valores da coluna; aceita o primeiro que parseia
    >=95% dos valores não-nulos sem erro. `None` se nada servir.
    """
    valores = serie.dropna().astype(str).str.strip()
    if valores.empty:
        return None
    comprimentos = valores.str.len().mode()
    if comprimentos.empty:
        return None
    comprimento_tipico = int(comprimentos.iloc[0])

    candidatos = [formato for formato, comp in FORMATOS_DATA if comp == comprimento_tipico]
    for formato in candidatos:
        parseado = pd.to_datetime(valores, format=formato, errors="coerce")
        if parseado.notna().mean() >= TaxaSucessoMinima:
            return formato
    return None


def detectar_colunas(df: pd.DataFrame) -> list[ColunaDetectada]:
    resultado = []
    for coluna in df.columns:
        serie = df[coluna]
        formato_data = _detectar_formato_data(serie)
        if formato_data:
            tipo: Literal["numerico", "data", "categorico"] = "data"
        elif pd.api.types.is_numeric_dtype(serie):
            tipo = "numerico"
        else:
            tipo = "categorico"

        resultado.append(
            ColunaDetectada(
                nome=str(coluna),
                tipo=tipo,
                formato_data=formato_data,
                n_distintos=int(serie.nunique(dropna=True)),
                exemplos=serie.dropna().head(3).tolist(),
            )
        )
    return resultado


def salvar_staging(df: pd.DataFrame) -> str:
    DIR_STAGING.mkdir(parents=True, exist_ok=True)
    upload_id = uuid.uuid4().hex[:12]
    df.to_csv(DIR_STAGING / f"{upload_id}.csv", index=False)
    return upload_id


def carregar_staging(upload_id: str) -> pd.DataFrame:
    caminho = DIR_STAGING / f"{upload_id}.csv"
    if not caminho.exists():
        raise FileNotFoundError(
            f"Upload '{upload_id}' não encontrado (staging expira ao reiniciar o backend)"
        )
    return pd.read_csv(caminho)


def valores_distintos(upload_id: str, coluna: str, limite: int = 50) -> list[dict[str, Any]]:
    df = carregar_staging(upload_id)
    contagens = df[coluna].astype(str).value_counts().head(limite)
    return [{"valor": v, "contagem": int(c)} for v, c in contagens.items()]


def dividir_por_amostra_existente(
    df: pd.DataFrame, coluna: str, valores_dev: list[str], valores_teste: list[str]
) -> tuple[pd.DataFrame, pd.DataFrame]:
    serie = df[coluna].astype(str)
    df_dev = df[serie.isin(valores_dev)].reset_index(drop=True)
    df_teste = df[serie.isin(valores_teste)].reset_index(drop=True)
    return df_dev, df_teste


def calcular_corte_por_percentual(df: pd.DataFrame, coluna: str, formato: str, proporcao_teste: float) -> str:
    """Data de corte equivalente a "os N% mais recentes viram OOT" — usada
    pelo frontend pra sugerir um corte antes do usuário confirmar/ajustar.
    """
    datas = pd.to_datetime(df[coluna].astype(str).str.strip(), format=formato, errors="coerce").dropna()
    if datas.empty:
        raise ValueError(f"Nenhuma data válida na coluna '{coluna}' com o formato '{formato}'")
    quantil = pd.Timestamp(datas.quantile(1 - proporcao_teste))
    return quantil.strftime("%Y-%m-%d")


def dividir_por_data_oot(
    df: pd.DataFrame, coluna: str, formato: str, corte: str
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """`corte` é uma data ISO (YYYY-MM-DD). Linhas ANTES do corte viram dev;
    a partir do corte (inclusive) viram teste — out-of-time: o modelo nunca
    treina em dados do "futuro" em relação ao que valida.
    """
    datas = pd.to_datetime(df[coluna].astype(str).str.strip(), format=formato, errors="coerce")
    corte_ts = pd.Timestamp(corte)
    mascara_valida = datas.notna()
    mascara_teste = mascara_valida & (datas >= corte_ts)
    mascara_dev = mascara_valida & ~mascara_teste
    return df[mascara_dev].reset_index(drop=True), df[mascara_teste].reset_index(drop=True)


def dividir_aleatorio(
    df: pd.DataFrame, proporcao_teste: float, semente: int
) -> tuple[pd.DataFrame, pd.DataFrame]:
    embaralhado = df.sample(frac=1.0, random_state=semente).reset_index(drop=True)
    corte = int(len(embaralhado) * (1 - proporcao_teste))
    return embaralhado.iloc[:corte].reset_index(drop=True), embaralhado.iloc[corte:].reset_index(drop=True)


def gravar_dataset_preparado(nome: str, df_dev: pd.DataFrame, df_teste: pd.DataFrame) -> None:
    pasta = DIR_DADOS / nome
    pasta.mkdir(parents=True, exist_ok=True)
    df_dev.to_csv(pasta / "dev.csv", index=False)
    df_teste.to_csv(pasta / "teste.csv", index=False)
