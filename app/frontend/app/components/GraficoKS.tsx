"use client";

import type { FaixaDecil } from "../lib/api";

const LARGURA = 560;
const ALTURA = 220;
const MARGEM = { topo: 12, base: 34, esquerda: 36, direita: 12 };

/** Curva KS: % acumulado de eventos vs. não-eventos por faixa de score,
 * com a maior distância entre as duas curvas marcada (é o próprio KS). Mais
 * informativo que só o número agregado — mostra ONDE o modelo separa bem.
 * Extraído de PainelResultado (Pedro_Wise) pra ser reaproveitado também no
 * Feature-lab (esfera 3) -- mesmo cálculo, mesmo desenho, sem duplicar. */
export default function GraficoKS({ tabela }: { tabela: FaixaDecil[] }) {
  const larguraUtil = LARGURA - MARGEM.esquerda - MARGEM.direita;
  const alturaUtil = ALTURA - MARGEM.topo - MARGEM.base;
  const n = tabela.length;
  const x = (i: number) => MARGEM.esquerda + (i / (n - 1)) * larguraUtil;
  const y = (pct: number) => MARGEM.topo + (1 - pct) * alturaUtil;

  const pontosEventos = tabela.map((f, i) => `${x(i)},${y(f.pct_eventos_capturados)}`).join(" ");
  const pontosNaoEventos = tabela.map((f, i) => `${x(i)},${y(f.pct_nao_eventos_capturados)}`).join(" ");

  const indiceMaxKS = tabela.reduce(
    (melhor, f, i) => (f.ks_acumulado > tabela[melhor].ks_acumulado ? i : melhor),
    0,
  );
  const faixaMaxKS = tabela[indiceMaxKS];

  return (
    <svg viewBox={`0 0 ${LARGURA} ${ALTURA}`} className="w-full" role="img" aria-label="Curva KS acumulada">
      {[0, 0.25, 0.5, 0.75, 1].map((frac) => (
        <g key={frac}>
          <line
            x1={MARGEM.esquerda}
            x2={LARGURA - MARGEM.direita}
            y1={y(frac)}
            y2={y(frac)}
            stroke="rgb(30 41 59 / 0.6)"
            strokeWidth={1}
          />
          <text x={MARGEM.esquerda - 6} y={y(frac) + 3} textAnchor="end" className="fill-slate-500" fontSize={10}>
            {Math.round(frac * 100)}%
          </text>
        </g>
      ))}
      <line
        x1={x(indiceMaxKS)}
        x2={x(indiceMaxKS)}
        y1={y(faixaMaxKS.pct_eventos_capturados)}
        y2={y(faixaMaxKS.pct_nao_eventos_capturados)}
        stroke="rgb(244 63 94)"
        strokeWidth={2}
        strokeDasharray="3 2"
      />
      <polyline points={pontosEventos} fill="none" stroke="rgb(16 185 129)" strokeWidth={2} />
      <polyline points={pontosNaoEventos} fill="none" stroke="rgb(100 116 139)" strokeWidth={2} />
      {tabela.map((f, i) => (
        <text
          key={f.faixa}
          x={x(i)}
          y={ALTURA - MARGEM.base + 16}
          textAnchor="middle"
          className="fill-slate-500"
          fontSize={10}
        >
          {f.faixa}
        </text>
      ))}
      <text
        x={(MARGEM.esquerda + LARGURA - MARGEM.direita) / 2}
        y={ALTURA - 6}
        textAnchor="middle"
        className="fill-slate-600"
        fontSize={10}
      >
        faixa de score (decil, 1 = maior risco)
      </text>
      <text
        x={x(indiceMaxKS) + 4}
        y={(y(faixaMaxKS.pct_eventos_capturados) + y(faixaMaxKS.pct_nao_eventos_capturados)) / 2}
        className="fill-rose-400"
        fontSize={10}
      >
        KS {faixaMaxKS.ks_acumulado.toFixed(3)}
      </text>
    </svg>
  );
}
