"use client";

import type { ReactNode } from "react";

interface Props {
  datasets: string[];
  dataset: string;
  aoMudarDataset: (dataset: string) => void;
  rodando: boolean;
  aoRodar: () => void;
  aoLimpar: () => void;
  temResultado: boolean;
  painelUpload: ReactNode;
}

export default function SidebarDataset({
  datasets,
  dataset,
  aoMudarDataset,
  rodando,
  aoRodar,
  aoLimpar,
  temResultado,
  painelUpload,
}: Props) {
  return (
    <aside className="w-64 shrink-0 border-r border-slate-800/60 bg-slate-900/30 p-5 flex flex-col gap-5 overflow-y-auto">
      {painelUpload}

      <div>
        <h2 className="text-xs font-medium uppercase tracking-wider text-slate-500 mb-2">Dataset</h2>
        <select
          className="w-full rounded-lg bg-slate-800/70 border border-slate-700/60 px-3 py-2 text-sm text-slate-100 focus:outline-none focus:ring-2 focus:ring-emerald-500"
          value={dataset}
          onChange={(e) => aoMudarDataset(e.target.value)}
          disabled={rodando}
        >
          {datasets.map((d) => (
            <option key={d} value={d}>
              {d}
            </option>
          ))}
        </select>
      </div>

      <div className="flex flex-col gap-2">
        <button
          onClick={aoRodar}
          disabled={rodando || !dataset}
          className="flex w-full items-center justify-center gap-2 rounded-lg bg-gradient-to-r from-emerald-600 to-emerald-500 px-4 py-2.5 text-sm font-semibold text-white shadow-sm shadow-emerald-950/50 transition hover:from-emerald-500 hover:to-emerald-400 disabled:cursor-not-allowed disabled:from-slate-700 disabled:to-slate-700 disabled:text-slate-400 disabled:shadow-none"
        >
          {rodando && (
            <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-white/40 border-t-white" />
          )}
          {rodando ? "Rodando…" : "Rodar seleção"}
        </button>
        {(temResultado || rodando) && (
          <button
            onClick={aoLimpar}
            disabled={rodando}
            className="w-full rounded-lg border border-slate-700/60 px-4 py-2 text-xs font-medium text-slate-400 transition hover:border-slate-600 hover:text-slate-200 disabled:cursor-not-allowed disabled:opacity-40"
          >
            Limpar resultado
          </button>
        )}
      </div>
    </aside>
  );
}
