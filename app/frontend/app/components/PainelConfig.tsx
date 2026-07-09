"use client";

import type { ConfigPipeline } from "../lib/api";

interface Props {
  datasets: string[];
  config: ConfigPipeline;
  aoMudar: (config: ConfigPipeline) => void;
  rodando: boolean;
  aoRodar: () => void;
}

export default function PainelConfig({ datasets, config, aoMudar, rodando, aoRodar }: Props) {
  function atualizar<K extends keyof ConfigPipeline>(campo: K, valor: ConfigPipeline[K]) {
    aoMudar({ ...config, [campo]: valor });
  }

  return (
    <aside className="w-80 shrink-0 border-r border-slate-800 bg-slate-900/50 p-5 flex flex-col gap-6 overflow-y-auto">
      <div>
        <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">Dataset</h2>
        <select
          className="w-full rounded-md bg-slate-800 border border-slate-700 px-3 py-2 text-sm text-slate-100 focus:outline-none focus:ring-2 focus:ring-emerald-500"
          value={config.dataset}
          onChange={(e) => atualizar("dataset", e.target.value)}
          disabled={rodando}
        >
          {datasets.map((d) => (
            <option key={d} value={d}>
              {d}
            </option>
          ))}
        </select>
      </div>

      <div>
        <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">Pipeline</h2>
        <label className="flex items-center gap-2 text-sm text-slate-200 cursor-pointer">
          <input
            type="checkbox"
            checked={config.usar_pipeline_completo}
            onChange={(e) => atualizar("usar_pipeline_completo", e.target.checked)}
            disabled={rodando}
            className="h-4 w-4 rounded border-slate-600 bg-slate-800 text-emerald-500 focus:ring-emerald-500"
          />
          Construção → categorização → WOE
        </label>
        <p className="mt-1 text-xs text-slate-500">
          Desligado: Pedro_Wise direto nas variáveis originais (baseline).
        </p>
      </div>

      <div>
        <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
          Critério de parada
        </h2>
        <div className="flex flex-col gap-1.5">
          {(["teste", "dev", "min"] as const).map((opcao) => (
            <label key={opcao} className="flex items-center gap-2 text-sm text-slate-200 cursor-pointer">
              <input
                type="radio"
                name="criterio"
                checked={config.criterio === opcao}
                onChange={() => atualizar("criterio", opcao)}
                disabled={rodando}
                className="h-4 w-4 border-slate-600 bg-slate-800 text-emerald-500 focus:ring-emerald-500"
              />
              {opcao === "min" ? "min (KS mínimo dev/teste)" : opcao}
            </label>
          ))}
        </div>
      </div>

      <div>
        <label className="flex items-center gap-2 text-sm text-slate-200 cursor-pointer">
          <input
            type="checkbox"
            checked={config.shadow_probing}
            onChange={(e) => atualizar("shadow_probing", e.target.checked)}
            disabled={rodando}
            className="h-4 w-4 rounded border-slate-600 bg-slate-800 text-emerald-500 focus:ring-emerald-500"
          />
          Shadow probing
        </label>
        <p className="mt-1 text-xs text-slate-500">Para o forward quando uma variável permutada venceria.</p>
      </div>

      <div>
        <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">Nível 2</h2>
        <div className="grid grid-cols-3 gap-2">
          {(
            [
              ["n_best_duplo", "duplo"],
              ["n_best_triplo_1", "trip. 1"],
              ["n_best_triplo_2", "trip. 2"],
            ] as const
          ).map(([campo, rotulo]) => (
            <div key={campo}>
              <label className="block text-[11px] text-slate-500 mb-1">{rotulo}</label>
              <input
                type="number"
                min={1}
                max={20}
                value={config[campo]}
                onChange={(e) => atualizar(campo, Number(e.target.value))}
                disabled={rodando}
                className="w-full rounded-md bg-slate-800 border border-slate-700 px-2 py-1.5 text-sm text-slate-100 focus:outline-none focus:ring-2 focus:ring-emerald-500"
              />
            </div>
          ))}
        </div>
      </div>

      <button
        onClick={aoRodar}
        disabled={rodando || !config.dataset}
        className="mt-auto w-full rounded-md bg-emerald-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-emerald-500 disabled:cursor-not-allowed disabled:bg-slate-700 disabled:text-slate-400"
      >
        {rodando ? "Rodando…" : "Rodar seleção"}
      </button>
    </aside>
  );
}
