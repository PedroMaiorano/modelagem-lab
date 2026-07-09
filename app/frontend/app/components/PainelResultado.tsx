"use client";

import type { EventoResultado } from "../lib/api";

function Metrica({ rotulo, valor }: { rotulo: string; valor: string }) {
  return (
    <div className="rounded-xl border border-slate-800/50 bg-slate-900/30 px-4 py-3">
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
      <div className="h-4 flex-1 overflow-hidden rounded bg-slate-800">
        <div className="h-full rounded bg-emerald-600" style={{ width: `${largura}%` }} />
      </div>
      <div className="w-14 shrink-0 text-right tabular-nums text-slate-400">{iv.toFixed(3)}</div>
    </div>
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

      {resultado.top_iv.length > 0 && (
        <div>
          <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-400">
            Top Information Value
          </h3>
          <div className="flex flex-col gap-2 rounded-xl border border-slate-800/50 bg-slate-900/30 p-4">
            {resultado.top_iv.map((item) => (
              <BarraIV key={item.variavel} variavel={item.variavel} iv={item.iv} maximo={maximoIV} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
