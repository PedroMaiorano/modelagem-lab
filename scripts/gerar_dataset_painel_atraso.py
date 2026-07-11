"""Gera um painel sintético mensal (contrato x safra x dias_atraso x renda)
que reproduz DOIS padrões "gold" ao mesmo tempo, cada um numa metade dos
contratos:

- Grupo A: risco depende da interação DENTRO da mesma variável bruta
  (tendência de piora do atraso x severidade recente do atraso) -- o caso
  original, descrito pelo usuário.
- Grupo B: risco depende de uma interação ENTRE variáveis brutas diferentes
  (tendência de piora do atraso x queda de renda) -- prova que
  `interacao.extrair_candidatas` também descobre padrões cruzando bases, não
  só dentro de uma.

Serve pra comparar `permitir_cruzamento_entre_bases=True` (deveria achar os
dois padrões) vs. `False` (só deveria achar o padrão do grupo A, já que o do
grupo B exige misturar `dias_atraso` com `renda`).

Também exercita `normalizar_safra` de propósito com formatos heterogêneos na
mesma base (anomes inteiro, "AAAA-MM", "AAAA-MM-DD").

Uso: `python scripts/gerar_dataset_painel_atraso.py`

Escreve `data/painel_atraso/painel.csv` (painel bruto, uma linha por
contrato-mês, colunas `dias_atraso` e `renda`) e `data/painel_atraso/agregado.csv`
(uma linha por contrato, já com as primitivas de `agregacao_temporal`
aplicadas às duas variáveis) -- ambos gitignored (ver `.gitignore` -> `data/`).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "python"))

import numpy as np
import pandas as pd
from agregacao_temporal import construir_agregados_janela, normalizar_safra

SAIDA = Path(__file__).resolve().parent.parent / "data" / "painel_atraso"

N_CONTRATOS = 3000
N_MESES = 12

#: Formatos de safra alternando por contrato -- mesmo painel, fontes
#: "diferentes" (cenário real: joins de bases distintas com safra em
#: formatos diferentes).
_FORMATOS_SAFRA = ["anomes", "hifen", "hifen_dia"]


def _formatar_safra(ano: int, mes: int, formato: str) -> str:
    if formato == "anomes":
        return f"{ano}{mes:02d}"
    if formato == "hifen":
        return f"{ano}-{mes:02d}"
    return f"{ano}-{mes:02d}-01"


def _trajetoria(
    rng: np.random.Generator, tendencia_alvo: float, nivel_base: float, ruido: float
) -> np.ndarray:
    """Nível-base + tendência linear + ruído, truncada em 0 (nem atraso nem
    renda fazem sentido negativos aqui)."""
    trajetoria = nivel_base + tendencia_alvo * np.arange(N_MESES) + rng.normal(0, ruido, N_MESES)
    return np.clip(trajetoria, 0, None).round(1)


def main() -> None:
    rng = np.random.default_rng(7)
    linhas = []
    grupos = {}

    for i in range(N_CONTRATOS):
        contrato = f"C{i:05d}"
        formato_safra = _FORMATOS_SAFRA[i % len(_FORMATOS_SAFRA)]
        grupo = "A" if i % 2 == 0 else "B"
        grupos[contrato] = grupo

        tendencia_atraso = rng.choice([0.0, 3.5]) + rng.normal(0, 0.5)
        atraso = _trajetoria(rng, tendencia_atraso, nivel_base=rng.uniform(0, 20), ruido=5)

        tendencia_renda = rng.choice([0.0, -80.0]) + rng.normal(0, 20)
        renda = _trajetoria(rng, tendencia_renda, nivel_base=rng.uniform(2000, 6000), ruido=150)

        for mes_idx in range(N_MESES):
            ano, mes = 2024 + (mes_idx // 12), (mes_idx % 12) + 1
            linhas.append(
                {
                    "contrato": contrato,
                    "safra": _formatar_safra(ano, mes, formato_safra),
                    "dias_atraso": atraso[mes_idx],
                    "renda": renda[mes_idx],
                }
            )

    painel = pd.DataFrame(linhas)
    painel["safra_norm"] = normalizar_safra(painel["safra"])
    painel = painel.sort_values(["contrato", "safra_norm"]).reset_index(drop=True)

    agregado = construir_agregados_janela(
        painel, chave="contrato", tempo="safra_norm", valor="dias_atraso", janelas=[3]
    )
    agregado = construir_agregados_janela(
        agregado, chave="contrato", tempo="safra_norm", valor="renda", janelas=[3]
    )

    ultimo_mes = agregado.groupby("contrato", sort=False).tail(1).copy()
    ultimo_mes["grupo"] = ultimo_mes["contrato"].map(grupos)

    # Grupo A: interação DENTRO do atraso (tendência x severidade) -- o caso original.
    tendencia_atraso_alta = ultimo_mes["dias_atraso_tendencia_3m"] > 1.5
    severidade_atraso_alta = ultimo_mes["dias_atraso_maximo_3m"] > 25
    sinal_a = tendencia_atraso_alta & severidade_atraso_alta

    # Grupo B: interação ENTRE atraso e renda (tendência de piora do atraso
    # x queda de renda) -- exige cruzar bases diferentes pra ser descoberto.
    renda_caindo = ultimo_mes["renda_tendencia_3m"] < -20
    sinal_b = tendencia_atraso_alta & renda_caindo

    sinal = np.where(ultimo_mes["grupo"] == "A", sinal_a, sinal_b)
    logit_p = -2.5 + 4.0 * sinal.astype(float)
    p = 1 / (1 + np.exp(-logit_p))
    ultimo_mes["y"] = rng.binomial(1, p)

    SAIDA.mkdir(parents=True, exist_ok=True)
    painel.to_csv(SAIDA / "painel.csv", index=False)
    ultimo_mes.to_csv(SAIDA / "agregado.csv", index=False)

    taxa_a = ultimo_mes.loc[ultimo_mes["grupo"] == "A", "y"].mean()
    taxa_b = ultimo_mes.loc[ultimo_mes["grupo"] == "B", "y"].mean()

    print(f"Escrito {SAIDA / 'painel.csv'} ({len(painel)} linhas, {N_CONTRATOS} contratos)")
    print(f"Escrito {SAIDA / 'agregado.csv'} ({len(ultimo_mes)} linhas, 1 por contrato)")
    print(f"Taxa de evento: {ultimo_mes['y'].mean():.1%} (grupo A: {taxa_a:.1%}, grupo B: {taxa_b:.1%})")
    print(f"Formatos de safra usados: {_FORMATOS_SAFRA}")


if __name__ == "__main__":
    main()
