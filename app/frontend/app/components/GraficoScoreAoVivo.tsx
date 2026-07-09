"use client";

import type { PontoScore } from "../lib/progresso";

const LARGURA = 560;
const ALTURA = 180;
const MARGEM = { topo: 12, base: 24, esquerda: 44, direita: 12 };

/** Score aceito ao longo dos eventos da busca — não é "tempo" no eixo X,
 * é a sequência de atualizações aceitas (forward/troca/backward/nível 3).
 * Complementa o log: mostra de longe se a busca está subindo, platôs longos
 * (como você notou no run com nível 3), ou oscilando. */
export default function GraficoScoreAoVivo({ historico }: { historico: PontoScore[] }) {
  if (historico.length < 2) {
    return (
      <div className="flex h-32 items-center justify-center text-xs text-slate-600">
        Aguardando atualizações aceitas…
      </div>
    );
  }

  const larguraUtil = LARGURA - MARGEM.esquerda - MARGEM.direita;
  const alturaUtil = ALTURA - MARGEM.topo - MARGEM.base;
  const n = historico.length;
  const scores = historico.map((p) => p.score);
  const minimo = Math.min(...scores);
  const maximo = Math.max(...scores);
  const faixa = maximo - minimo || 1;

  const x = (i: number) => MARGEM.esquerda + (i / (n - 1)) * larguraUtil;
  const y = (score: number) => MARGEM.topo + (1 - (score - minimo) / faixa) * alturaUtil;

  const pontos = historico.map((p, i) => `${x(i)},${y(p.score)}`).join(" ");
  const ultimo = historico[historico.length - 1];

  return (
    <svg viewBox={`0 0 ${LARGURA} ${ALTURA}`} className="w-full" role="img" aria-label="Score ao longo da busca">
      {[0, 0.5, 1].map((frac) => (
        <g key={frac}>
          <line
            x1={MARGEM.esquerda}
            x2={LARGURA - MARGEM.direita}
            y1={MARGEM.topo + (1 - frac) * alturaUtil}
            y2={MARGEM.topo + (1 - frac) * alturaUtil}
            stroke="rgb(30 41 59 / 0.6)"
            strokeWidth={1}
          />
          <text
            x={MARGEM.esquerda - 6}
            y={MARGEM.topo + (1 - frac) * alturaUtil + 3}
            textAnchor="end"
            className="fill-slate-500"
            fontSize={10}
          >
            {(minimo + frac * faixa).toFixed(3)}
          </text>
        </g>
      ))}
      <polyline points={pontos} fill="none" stroke="rgb(16 185 129)" strokeWidth={2} />
      <circle cx={x(n - 1)} cy={y(ultimo.score)} r={3.5} className="fill-emerald-400" />
      <text
        x={(MARGEM.esquerda + LARGURA - MARGEM.direita) / 2}
        y={ALTURA - 6}
        textAnchor="middle"
        className="fill-slate-600"
        fontSize={10}
      >
        atualizações aceitas ({n})
      </text>
    </svg>
  );
}
