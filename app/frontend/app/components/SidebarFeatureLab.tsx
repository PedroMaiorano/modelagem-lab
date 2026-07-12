"use client";

import { useState } from "react";
import type { BaseFeatureLab } from "../lib/api";

interface Props {
  bases: BaseFeatureLab[];
  base: BaseFeatureLab | null;
  aoMudarBase: (base: BaseFeatureLab) => void;
  aoEnviarPainel: (arquivo: File, nome: string) => Promise<void>;
  colunasBase: string[];
  colunaY: string;
  aoMudarColunaY: (coluna: string) => void;
  aoLimparTudo: () => void;
}

export default function SidebarFeatureLab({
  bases,
  base,
  aoMudarBase,
  aoEnviarPainel,
  colunasBase,
  colunaY,
  aoMudarColunaY,
  aoLimparTudo,
}: Props) {
  const [arquivo, setArquivo] = useState<File | null>(null);
  const [nome, setNome] = useState("");
  const [enviando, setEnviando] = useState(false);

  async function aoClicarEnviar() {
    if (!arquivo || !nome.trim()) return;
    setEnviando(true);
    try {
      await aoEnviarPainel(arquivo, nome.trim());
      setArquivo(null);
      setNome("");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <aside className="w-64 shrink-0 border-r border-slate-700 bg-slate-900/70 p-5 flex flex-col gap-5 overflow-y-auto">
      <div className="flex flex-col gap-2">
        <h2 className="text-xs font-medium uppercase tracking-wider text-slate-500">Nova base (CSV)</h2>
        <input
          type="file"
          accept=".csv"
          onChange={(e) => setArquivo(e.target.files?.[0] ?? null)}
          className="block text-xs text-slate-400 file:mr-2 file:rounded file:border-0 file:bg-slate-700 file:px-2 file:py-1 file:text-xs file:text-slate-200"
        />
        <input
          type="text"
          value={nome}
          onChange={(e) => setNome(e.target.value)}
          placeholder="nome da base"
          className="w-full rounded-lg bg-slate-800 border border-slate-600 px-2 py-1.5 text-sm text-slate-100"
        />
        <button
          onClick={aoClicarEnviar}
          disabled={enviando || !arquivo || !nome.trim()}
          className="w-full rounded-lg border border-slate-600 px-3 py-1.5 text-xs font-medium text-slate-300 transition hover:border-emerald-700 hover:text-emerald-400 disabled:cursor-not-allowed disabled:opacity-40"
        >
          {enviando ? "Enviando…" : "Enviar"}
        </button>
      </div>

      <div className="border-t border-slate-800 pt-4">
        <h2 className="text-xs font-medium uppercase tracking-wider text-slate-500 mb-2">Base</h2>
        <select
          className="w-full rounded-lg bg-slate-800 border border-slate-600 px-3 py-2 text-sm text-slate-100 focus:outline-none focus:ring-2 focus:ring-emerald-500"
          value={base ? `${base.tipo}:${base.nome}` : ""}
          onChange={(e) => {
            const [tipo, nomeBase] = e.target.value.split(":");
            aoMudarBase({ tipo: tipo as BaseFeatureLab["tipo"], nome: nomeBase });
          }}
        >
          {bases.map((b) => (
            <option key={`${b.tipo}:${b.nome}`} value={`${b.tipo}:${b.nome}`}>
              {b.nome}
            </option>
          ))}
        </select>
      </div>

      <div>
        <h2 className="text-xs font-medium uppercase tracking-wider text-slate-500 mb-2">Coluna resposta</h2>
        {colunasBase.length > 0 ? (
          <select
            value={colunaY}
            onChange={(e) => aoMudarColunaY(e.target.value)}
            className="w-full rounded-lg bg-slate-800 border border-slate-600 px-3 py-2 text-sm text-slate-100 focus:outline-none focus:ring-2 focus:ring-emerald-500"
          >
            {!colunasBase.includes(colunaY) && <option value={colunaY}>{colunaY}</option>}
            {colunasBase.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        ) : (
          <p className="text-[11px] text-slate-500">escolha uma base primeiro</p>
        )}
        <p className="mt-1 text-[11px] text-slate-500">Coluna alvo na base — padrão &ldquo;y&rdquo;.</p>
      </div>

      <button
        onClick={aoLimparTudo}
        className="mt-auto rounded-lg border border-slate-700 px-3 py-1.5 text-xs font-medium text-slate-500 transition hover:border-red-800 hover:text-red-400"
      >
        Limpar tudo
      </button>
    </aside>
  );
}
