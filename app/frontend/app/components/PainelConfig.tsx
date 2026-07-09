"use client";

import type { ReactNode } from "react";
import type { ConfigPipeline } from "../lib/api";

interface Props {
  datasets: string[];
  config: ConfigPipeline;
  aoMudar: (config: ConfigPipeline) => void;
  rodando: boolean;
  aoRodar: () => void;
  painelUpload?: ReactNode;
}

export default function PainelConfig({ datasets, config, aoMudar, rodando, aoRodar, painelUpload }: Props) {
  function atualizar<K extends keyof ConfigPipeline>(campo: K, valor: ConfigPipeline[K]) {
    aoMudar({ ...config, [campo]: valor });
  }

  return (
    <aside className="w-80 shrink-0 border-r border-slate-800 bg-slate-900/50 p-5 flex flex-col gap-6 overflow-y-auto">
      {painelUpload}
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
        <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">Nível 1</h2>
        <div className="flex flex-col gap-1.5">
          {(
            [
              ["forward_simples", "forward simples"],
              ["transformacao_simples_nivel1", "transformação simples"],
              ["backward_simples_nivel1", "backward simples"],
            ] as const
          ).map(([campo, rotulo]) => (
            <label key={campo} className="flex items-center gap-2 text-sm text-slate-200 cursor-pointer">
              <input
                type="checkbox"
                checked={config[campo]}
                onChange={(e) => atualizar(campo, e.target.checked)}
                disabled={rodando}
                className="h-4 w-4 rounded border-slate-600 bg-slate-800 text-emerald-500 focus:ring-emerald-500"
              />
              {rotulo}
            </label>
          ))}
          <div>
            <label className="block text-[11px] text-slate-500 mb-1">mín. vars p/ backward</label>
            <input
              type="number"
              min={1}
              max={20}
              value={config.min_vars_para_backward}
              onChange={(e) => atualizar("min_vars_para_backward", Number(e.target.value))}
              disabled={rodando}
              className="w-24 rounded-md bg-slate-800 border border-slate-700 px-2 py-1.5 text-sm text-slate-100 focus:outline-none focus:ring-2 focus:ring-emerald-500"
            />
          </div>
        </div>
      </div>

      <div>
        <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">Nível 2 / 2.5</h2>
        <div className="flex flex-col gap-1.5 mb-2">
          {(
            [
              ["forward_duplo", "forward duplo"],
              ["forward_triplo", "forward triplo (2.5)"],
              ["transformacao_simples_nivel2", "transformação simples"],
              ["backward_simples_nivel2", "backward simples"],
            ] as const
          ).map(([campo, rotulo]) => (
            <label key={campo} className="flex items-center gap-2 text-sm text-slate-200 cursor-pointer">
              <input
                type="checkbox"
                checked={config[campo]}
                onChange={(e) => atualizar(campo, e.target.checked)}
                disabled={rodando}
                className="h-4 w-4 rounded border-slate-600 bg-slate-800 text-emerald-500 focus:ring-emerald-500"
              />
              {rotulo}
            </label>
          ))}
        </div>
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

      <div>
        <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">Nível 3</h2>
        <label className="flex items-center gap-2 text-sm text-slate-200 cursor-pointer">
          <input
            type="checkbox"
            checked={config.nivel3_ativado}
            onChange={(e) => atualizar("nivel3_ativado", e.target.checked)}
            disabled={rodando}
            className="h-4 w-4 rounded border-slate-600 bg-slate-800 text-emerald-500 focus:ring-emerald-500"
          />
          Backward complexo (recursivo)
        </label>
        <p className="mt-1 text-xs text-slate-500">Mais caro — explora remoções/trocas recursivas.</p>
        {config.nivel3_ativado && (
          <div className="mt-2 grid grid-cols-2 gap-2">
            <div>
              <label className="block text-[11px] text-slate-500 mb-1">n_best_backward</label>
              <input
                type="number"
                min={1}
                max={10}
                value={config.n_best_backward}
                onChange={(e) => atualizar("n_best_backward", Number(e.target.value))}
                disabled={rodando}
                className="w-full rounded-md bg-slate-800 border border-slate-700 px-2 py-1.5 text-sm text-slate-100 focus:outline-none focus:ring-2 focus:ring-emerald-500"
              />
            </div>
            <div>
              <label className="block text-[11px] text-slate-500 mb-1">profundidade máx.</label>
              <input
                type="number"
                min={1}
                max={5}
                value={config.profundidade_maxima_nivel3}
                onChange={(e) => atualizar("profundidade_maxima_nivel3", Number(e.target.value))}
                disabled={rodando}
                className="w-full rounded-md bg-slate-800 border border-slate-700 px-2 py-1.5 text-sm text-slate-100 focus:outline-none focus:ring-2 focus:ring-emerald-500"
              />
            </div>
          </div>
        )}
      </div>

      <button
        onClick={aoRodar}
        disabled={rodando || !config.dataset}
        className="mt-auto flex w-full items-center justify-center gap-2 rounded-lg bg-gradient-to-r from-emerald-600 to-emerald-500 px-4 py-2.5 text-sm font-semibold text-white shadow-sm shadow-emerald-950 transition hover:from-emerald-500 hover:to-emerald-400 disabled:cursor-not-allowed disabled:from-slate-700 disabled:to-slate-700 disabled:text-slate-400 disabled:shadow-none"
      >
        {rodando && (
          <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-white/40 border-t-white" />
        )}
        {rodando ? "Rodando…" : "Rodar seleção"}
      </button>
    </aside>
  );
}
