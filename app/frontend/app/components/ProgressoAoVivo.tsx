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
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Nunca usar scrollIntoView aqui: ele sobe a árvore de ancestrais
    // procurando QUALQUER contêiner com scroll pra alinhar o elemento —
    // inclusive o <main> da página inteira — e não dá pra restringir isso
    // a um só nível. Resultado real visto na tela: a página inteira
    // "pulava" pro topo a cada linha nova. Setar scrollTop direto no
    // contêiner do log mexe só nele, nada além.
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [linhas]);

  if (linhas.length === 0 && !rodando) {
    return (
      <div className="flex h-40 items-center justify-center rounded-xl border border-dashed border-slate-700 text-sm text-slate-600">
        Configure acima e clique em &ldquo;Rodar seleção&rdquo; na barra lateral.
      </div>
    );
  }

  return (
    <div className="flex h-full min-h-[20rem] flex-col rounded-xl border border-slate-700 bg-slate-900/70">
      <div className="flex shrink-0 items-center gap-2 border-b border-slate-700 px-4 py-2.5">
        <span className={`h-2 w-2 rounded-full ${rodando ? "bg-emerald-500 animate-pulse" : "bg-slate-600"}`} />
        <span className="text-xs font-medium text-slate-400">
          {rodando ? "Rodando…" : "Concluído"}
        </span>
      </div>
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 font-mono text-xs leading-relaxed">
        {linhas.map((linha, i) => (
          <div key={i} className={CORES[linha.tipo]}>
            {linha.tipo === "etapa" ? `▸ ${linha.mensagem}` : linha.mensagem}
          </div>
        ))}
      </div>
    </div>
  );
}
