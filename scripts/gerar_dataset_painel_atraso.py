"""Gera um painel sintético mensal (contrato x safra x dias_atraso) que
reproduz o padrão "gold" descrito pelo usuário: o risco de verdade depende
da INTERAÇÃO entre tendência de piora e severidade recente (máximo_3m), não
de cada um isoladamente -- uma combinação linear simples dos dois não
capturaria isso bem, o que é exatamente o motivo de precisar de uma esfera
de descoberta de interação (RuleFit/H-statistic) depois da agregação.

Também exercita `normalizar_safra` de propósito com formatos heterogêneos
na mesma base (anomes inteiro, "AAAA-MM", "AAAA-MM-DD") -- cenário real
citado: fontes diferentes do mesmo painel trazem safra em formatos
diferentes.

Uso: `python scripts/gerar_dataset_painel_atraso.py`

Escreve `data/painel_atraso/painel.csv` (painel bruto, uma linha por
contrato-mês) e `data/painel_atraso/agregado.csv` (uma linha por
contrato-mês já com as primitivas de `agregacao_temporal` aplicadas) --
ambos gitignored (ver `.gitignore` -> `data/`).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "python"))

import numpy as np
import pandas as pd
from agregacao_temporal import construir_agregados_janela, normalizar_safra

SAIDA = Path(__file__).resolve().parent.parent / "data" / "painel_atraso"

N_CONTRATOS = 2000
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


def _trajetoria_atraso(rng: np.random.Generator, tendencia_alvo: float, nivel_base: float) -> np.ndarray:
    """Simula uma trajetória de dias em atraso: nível-base + tendência linear
    + ruído, truncada em 0 (atraso não é negativo).
    """
    ruido = rng.normal(0, 5, N_MESES)
    trajetoria = nivel_base + tendencia_alvo * np.arange(N_MESES) + ruido
    return np.clip(trajetoria, 0, None).round(0)


def main() -> None:
    rng = np.random.default_rng(7)
    linhas = []

    for i in range(N_CONTRATOS):
        contrato = f"C{i:05d}"
        formato_safra = _FORMATOS_SAFRA[i % len(_FORMATOS_SAFRA)]

        # Metade dos contratos tem tendência de piora; distribuição de
        # nível-base independente da tendência -- o sinal de risco de
        # verdade (abaixo) só aparece quando os DOIS são altos ao mesmo
        # tempo, não isoladamente.
        tendencia_alvo = rng.choice([0.0, 3.5]) + rng.normal(0, 0.5)
        nivel_base = rng.uniform(0, 20)
        atraso = _trajetoria_atraso(rng, tendencia_alvo, nivel_base)

        for mes_idx in range(N_MESES):
            ano, mes = 2024 + (mes_idx // 12), (mes_idx % 12) + 1
            linhas.append(
                {
                    "contrato": contrato,
                    "safra": _formatar_safra(ano, mes, formato_safra),
                    "dias_atraso": atraso[mes_idx],
                }
            )

    painel = pd.DataFrame(linhas)
    painel["safra_norm"] = normalizar_safra(painel["safra"])
    painel = painel.sort_values(["contrato", "safra_norm"]).reset_index(drop=True)

    agregado = construir_agregados_janela(
        painel, chave="contrato", tempo="safra_norm", valor="dias_atraso", janelas=[3]
    )

    # Alvo sintético: evento fica provável só quando tendência E severidade
    # recente são altas ao mesmo tempo (interação, não soma) -- avaliado só
    # no último mês de cada contrato, ponto de observação típico de scoring.
    ultimo_mes = agregado.groupby("contrato", sort=False).tail(1).copy()
    tendencia_alta = ultimo_mes["dias_atraso_tendencia_3m"] > 1.5
    severidade_alta = ultimo_mes["dias_atraso_maximo_3m"] > 25
    logit_p = -2.5 + 4.0 * (tendencia_alta & severidade_alta).astype(float)
    p = 1 / (1 + np.exp(-logit_p))
    ultimo_mes["y"] = rng.binomial(1, p)

    SAIDA.mkdir(parents=True, exist_ok=True)
    painel.to_csv(SAIDA / "painel.csv", index=False)
    ultimo_mes.to_csv(SAIDA / "agregado.csv", index=False)

    print(f"Escrito {SAIDA / 'painel.csv'} ({len(painel)} linhas, {N_CONTRATOS} contratos)")
    print(f"Escrito {SAIDA / 'agregado.csv'} ({len(ultimo_mes)} linhas, 1 por contrato)")
    print(f"Taxa de evento: {ultimo_mes['y'].mean():.1%}")
    print(f"Formatos de safra usados: {_FORMATOS_SAFRA}")


if __name__ == "__main__":
    main()
