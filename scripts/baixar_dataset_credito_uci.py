"""Baixa e prepara um dataset REAL de risco de crédito: "Default of Credit
Card Clients" (UCI ML Repository #350, Yeh & Lien 2009) — 30.000 clientes de
cartão de crédito em Taiwan, alvo binário (inadimplência no mês seguinte).
Fonte aberta, sem licença restritiva: https://archive.ics.uci.edu/dataset/350

Uso: python scripts/baixar_dataset_credito_uci.py

Grava em `data/credito_real/{dev,teste}.csv` — aparece automaticamente no
seletor de dataset do dashboard (`app/streamlit_app.py`) e é usável direto
pelos scripts de experimento (`scripts/experimento_*.py`, `validar_port_python.py`).

## Por que renomear as colunas (não é só estética)

`pedro_wise.base.extrair_base` assume a convenção do lab: sufixo de
transformação após o ÚLTIMO `_` (ex.: `renda_woe`, `renda_log` -> base
`renda`). As colunas originais do UCI NÃO seguem essa convenção — `PAY_0` e
`PAY_AMT1` colapsariam para a mesma base `PAY` (o `rsplit("_", 1)` não vê
diferença), fazendo o Pedro_Wise tratar duas variáveis completamente
diferentes (status de pagamento vs. valor pago) como "versões uma da outra",
permitindo só uma das duas no modelo — errado para este dataset. A correção
é remover os underscores dos nomes originais (`PAY_0` -> `PAY0`, `BILL_AMT1`
-> `BILLAMT1`), tornando cada variável sua própria base, sem agrupamento
acidental. Datasets reais fora da convenção `_woe`/`_log` do lab sempre
precisam desse cuidado antes de entrar no Pedro_Wise.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import requests

_reconfigure = getattr(sys.stdout, "reconfigure", None)
if _reconfigure is not None and sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    _reconfigure(encoding="utf-8", errors="replace")

URL = "https://archive.ics.uci.edu/ml/machine-learning-databases/00350/default%20of%20credit%20card%20clients.xls"
DIR_SAIDA = Path(__file__).resolve().parent.parent / "data" / "credito_real"
CAMINHO_BRUTO = DIR_SAIDA / "raw.xls"


def baixar_se_necessario() -> None:
    if CAMINHO_BRUTO.exists():
        print(f"Já baixado: {CAMINHO_BRUTO}")
        return
    DIR_SAIDA.mkdir(parents=True, exist_ok=True)
    print(f"Baixando {URL} ...")
    resp = requests.get(URL, timeout=60)
    resp.raise_for_status()
    CAMINHO_BRUTO.write_bytes(resp.content)
    print(f"Escrito {CAMINHO_BRUTO} ({len(resp.content):,} bytes)")


def preparar() -> tuple[pd.DataFrame, pd.DataFrame]:
    df = pd.read_excel(CAMINHO_BRUTO, header=1)
    df = df.drop(columns=["ID"])
    df = df.rename(columns={"default payment next month": "y"})
    # Remove underscores dos nomes originais (ver docstring do módulo) — cada
    # variável vira sua própria base, sem agrupamento acidental por sufixo.
    df.columns = [c if c == "y" else c.replace("_", "") for c in df.columns]

    df = df.sample(frac=1.0, random_state=2026).reset_index(drop=True)  # embaralha antes de dividir
    metade = len(df) // 2
    return df.iloc[:metade].reset_index(drop=True), df.iloc[metade:].reset_index(drop=True)


def main() -> None:
    baixar_se_necessario()
    df_dev, df_teste = preparar()

    df_dev.to_csv(DIR_SAIDA / "dev.csv", index=False)
    df_teste.to_csv(DIR_SAIDA / "teste.csv", index=False)

    taxa_evento = df_dev["y"].mean()
    print(f"\nEscrito {DIR_SAIDA / 'dev.csv'} ({len(df_dev)} linhas)")
    print(f"Escrito {DIR_SAIDA / 'teste.csv'} ({len(df_teste)} linhas)")
    print(f"Taxa de evento (dev): {taxa_evento:.1%}")
    print(f"Candidatas: {[c for c in df_dev.columns if c != 'y']}")


if __name__ == "__main__":
    main()
