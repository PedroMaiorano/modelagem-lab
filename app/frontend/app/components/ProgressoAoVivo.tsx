"use client";

import { useEffect, useRef } from "react";

export interface LinhaProgresso {
  tipo: "etapa" | "log" | "erro";
  mensagem: string;
}

interface Props {
  linhas: LinhaProgresso[];
  rodando: boolean;
}

const CORES: Record<LinhaProgresso["tipo"], string> = {
  etapa: "text-emerald-400 font-semibold",
  log: "text-slate-400",
  erro: "text-red-400 font-semibold",
};

export default function ProgressoAoVivo({ linhas, rodando }: Props) {
  const fimRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fimRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [linhas]);

  if (linhas.length === 0 && !rodando) {
    return (
      <div className="flex h-40 items-center justify-center rounded-lg border border-dashed border-slate-800 text-sm text-slate-600">
        Configure na barra lateral e clique em &ldquo;Rodar seleção&rdquo;.
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-950">
      <div className="flex items-center gap-2 border-b border-slate-800 px-4 py-2">
        <span className={`h-2 w-2 rounded-full ${rodando ? "bg-emerald-500 animate-pulse" : "bg-slate-600"}`} />
        <span className="text-xs font-medium text-slate-400">
          {rodando ? "Rodando…" : "Concluído"}
        </span>
      </div>
      <div className="max-h-80 overflow-y-auto p-4 font-mono text-xs leading-relaxed">
        {linhas.map((linha, i) => (
          <div key={i} className={CORES[linha.tipo]}>
            {linha.tipo === "etapa" ? `▸ ${linha.mensagem}` : linha.mensagem}
          </div>
        ))}
        <div ref={fimRef} />
      </div>
    </div>
  );
}
