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

// As linhas "testando N candidatas: a,b,c,..." existem pro histórico
// alimentar a árvore de busca (ver lib/progresso.ts) — a lista completa é
// dado, não leitura. Mostrar ela inteira no log poluía muito (uma "rodada"
// virava 4-5 linhas de nomes separados por vírgula). Aqui só resume pra
// exibição; `linhas` (o dado real usado pelo parser) continua intacto.
const REGEX_TESTANDO = /^((?:forward_simples|transformacao_simples(?:\[nivel2\])?|backward_simples(?:\[nivel2\])?|forward_duplo|forward_triplo): testando \d+ \S+):.*$/;

function textoExibido(mensagem: string): string {
  const m = mensagem.match(REGEX_TESTANDO);
  return m ? `${m[1]}…` : mensagem;
}

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
      {/* min-h-0 é essencial aqui: sem ele, um filho flex nunca encolhe
          abaixo do tamanho do próprio conteúdo (comportamento default do
          flexbox), então o overflow-y-auto nunca entra em ação e a caixa
          cresce sem limite em vez de acompanhar a altura da coluna irmã —
          bug real visto na tela depois que as linhas "testando" (bem mais
          longas) começaram a aparecer. */}
      <div ref={scrollRef} className="min-h-0 flex-1 overflow-y-auto p-4 font-mono text-xs leading-relaxed">
        {linhas.map((linha, i) => (
          <div key={i} className={CORES[linha.tipo]}>
            {linha.tipo === "etapa" ? `▸ ${linha.mensagem}` : textoExibido(linha.mensagem)}
          </div>
        ))}
      </div>
    </div>
  );
}
