"use client";

import type { EventoResultado, FaixaDecil } from "../lib/api";

function Metrica({ rotulo, valor }: { rotulo: string; valor: string }) {
  return (
    <div className="rounded-xl border border-slate-700 bg-slate-900/70 px-4 py-3">
      <div className="text-[11px] uppercase tracking-wider text-slate-500">{rotulo}</div>
      <div className="mt-1 text-2xl font-semibold text-slate-100 tabular-nums">{valor}</div>
    </div>
  );
}

/** Barras de IV: uma única cor (magnitude, não categoria) — sem legenda
 * necessária para série única, ver referências/palette.md da skill dataviz. */
function BarraIV({ variavel, iv, maximo }: { variavel: string; iv: number; maximo: number }) {
  const largura = maximo > 0 ? Math.max(4, (iv / maximo) * 100) : 0;
  return (
    <div className="flex items-center gap-3 text-xs">
      <div className="w-32 shrink-0 truncate text-slate-400" title={variavel}>
        {variavel}
      </div>
      <div className="h-3.5 flex-1 overflow-hidden rounded-full bg-slate-800/50">
        <div className="h-full rounded-full bg-emerald-600" style={{ width: `${largura}%` }} />
      </div>
      <div className="w-14 shrink-0 text-right tabular-nums text-slate-400">{iv.toFixed(3)}</div>
    </div>
  );
}

const LARGURA = 560;
const ALTURA = 200;
const MARGEM = { topo: 10, base: 24, esquerda: 30, direita: 10 };

/** Curva KS: % acumulado de eventos vs. não-eventos por faixa de score,
 * com a maior distância entre as duas curvas marcada (é o próprio KS). Mais
 * informativo que só o número agregado — mostra ONDE o modelo separa bem. */
function GraficoKS({ tabela }: { tabela: FaixaDecil[] }) {
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
        <line
          key={frac}
          x1={MARGEM.esquerda}
          x2={LARGURA - MARGEM.direita}
          y1={y(frac)}
          y2={y(frac)}
          stroke="rgb(30 41 59 / 0.6)"
          strokeWidth={1}
        />
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
      <text x={MARGEM.esquerda} y={12} className="fill-slate-500" fontSize={10}>
        100%
      </text>
      <text x={MARGEM.esquerda} y={ALTURA - MARGEM.base + 4} className="fill-slate-500" fontSize={10}>
        0%
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

function GraficoTaxaEvento({ tabela }: { tabela: FaixaDecil[] }) {
  const larguraUtil = LARGURA - MARGEM.esquerda - MARGEM.direita;
  const alturaUtil = ALTURA - MARGEM.topo - MARGEM.base;
  const maximo = Math.max(...tabela.map((f) => f.taxa_evento), 0.01);
  const larguraBarra = (larguraUtil / tabela.length) * 0.7;

  return (
    <svg viewBox={`0 0 ${LARGURA} ${ALTURA}`} className="w-full" role="img" aria-label="Taxa de evento por faixa">
      {tabela.map((f, i) => {
        const alturaBarra = (f.taxa_evento / maximo) * alturaUtil;
        const xCentro = MARGEM.esquerda + ((i + 0.5) / tabela.length) * larguraUtil;
        return (
          <g key={f.faixa}>
            <rect
              x={xCentro - larguraBarra / 2}
              y={MARGEM.topo + alturaUtil - alturaBarra}
              width={larguraBarra}
              height={alturaBarra}
              rx={3}
              className="fill-sky-600"
            />
            <text
              x={xCentro}
              y={ALTURA - MARGEM.base + 14}
              textAnchor="middle"
              className="fill-slate-500"
              fontSize={10}
            >
              {f.faixa}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

export default function PainelResultado({ resultado }: { resultado: EventoResultado }) {
  const maximoIV = Math.max(0, ...resultado.top_iv.map((i) => i.iv));

  return (
    <div className="flex flex-col gap-5">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Metrica rotulo="KS (teste)" valor={resultado.ks_teste.toFixed(4)} />
        <Metrica rotulo="AUC" valor={resultado.auc.toFixed(3)} />
        <Metrica rotulo="Variáveis" valor={String(resultado.variaveis.length)} />
        <Metrica rotulo="Tempo" valor={`${resultado.tempo_segundos}s`} />
      </div>

      <div>
        <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-400">
          Variáveis selecionadas
        </h3>
        <div className="flex flex-wrap gap-1.5">
          {resultado.variaveis.map((v) => (
            <span
              key={v}
              className="rounded-full border border-emerald-800 bg-emerald-950/50 px-2.5 py-1 text-xs text-emerald-300"
            >
              {v}
            </span>
          ))}
        </div>
      </div>

      {resultado.tabela_decis.length > 1 && (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <div className="rounded-xl border border-slate-700 bg-slate-900/70 p-4">
            <h3 className="mb-1 text-xs font-semibold uppercase tracking-wider text-slate-400">
              Curva KS (teste)
            </h3>
            <p className="mb-2 text-[11px] text-slate-600">
              % acumulado de <span className="text-emerald-400">eventos</span> vs.{" "}
              <span className="text-slate-400">não-eventos</span> por faixa de score (maior risco → menor).
            </p>
            <GraficoKS tabela={resultado.tabela_decis} />
          </div>
          <div className="rounded-xl border border-slate-700 bg-slate-900/70 p-4">
            <h3 className="mb-1 text-xs font-semibold uppercase tracking-wider text-slate-400">
              Taxa de evento por faixa
            </h3>
            <p className="mb-2 text-[11px] text-slate-600">
              10 faixas de score (1 = maior risco). Faixas decrescentes indicam boa discriminação.
            </p>
            <GraficoTaxaEvento tabela={resultado.tabela_decis} />
          </div>
        </div>
      )}

      {resultado.top_iv.length > 0 && (
        <div>
          <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-400">
            Top Information Value
          </h3>
          <div className="flex flex-col gap-2 rounded-xl border border-slate-700 bg-slate-900/70 p-4">
            {resultado.top_iv.map((item) => (
              <BarraIV key={item.variavel} variavel={item.variavel} iv={item.iv} maximo={maximoIV} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
