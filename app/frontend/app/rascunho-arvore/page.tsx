"use client";

import { useEffect, useState } from "react";

// RASCUNHO — não é dado real, é só uma simulação fixa pra avaliar o
// conceito visual (pedido do usuário: "quero ver como se fosse uma árvore
// ou rede neural de possibilidade e ir piscando no que está sendo
// testado"). Se aprovado, a versão de verdade precisaria de eventos
// estruturados vindos do backend (hoje só manda texto de log) — ver
// conversa. Rota isolada, não faz parte do fluxo principal do app.

interface Estagio {
  rotulo: string;
  candidatos: string[];
  vencedor: number;
}

const ROTEIRO: Estagio[] = [
  {
    rotulo: "Nível 1 — forward simples",
    candidatos: ["cloud_woe", "humidity_inv", "temparature_log", "day_raiz", "windspeed_cubo", "sunshine_quad"],
    vencedor: 2,
  },
  {
    rotulo: "Nível 1 — transformação simples",
    candidatos: ["temparature_log", "temparature_inv", "temparature_woe", "temparature_quad"],
    vencedor: 1,
  },
  {
    rotulo: "Nível 2 — forward duplo",
    candidatos: ["+humidity_inv +day_raiz", "+cloud_quad +windspeed_woe", "+sunshine_cubo +pressure_woe"],
    vencedor: 0,
  },
];

const MS_POR_CANDIDATO = 550;
const MS_PAUSA_VENCEDOR = 1400;

type Fase = { estagioIdx: number; candidatoIdx: number; concluido: boolean };

export default function RascunhoArvore() {
  const [fase, setFase] = useState<Fase>({ estagioIdx: 0, candidatoIdx: 0, concluido: false });
  const [scoreAtual, setScoreAtual] = useState(0.62);

  useEffect(() => {
    const estagio = ROTEIRO[fase.estagioIdx];
    const duracao = fase.concluido ? MS_PAUSA_VENCEDOR : MS_POR_CANDIDATO;

    const id = setTimeout(() => {
      if (fase.concluido) {
        // avança pro próximo estágio (ou reinicia o roteiro)
        const proximo = (fase.estagioIdx + 1) % ROTEIRO.length;
        if (proximo === 0) setScoreAtual(0.62);
        else setScoreAtual((s) => s + 0.02 + Math.random() * 0.015);
        setFase({ estagioIdx: proximo, candidatoIdx: 0, concluido: false });
        return;
      }
      const proximoCandidato = fase.candidatoIdx + 1;
      if (proximoCandidato >= estagio.candidatos.length) {
        setFase((f) => ({ ...f, concluido: true }));
      } else {
        setFase((f) => ({ ...f, candidatoIdx: proximoCandidato }));
      }
    }, duracao);

    return () => clearTimeout(id);
  }, [fase]);

  const estagio = ROTEIRO[fase.estagioIdx];

  return (
    <div className="min-h-screen bg-slate-900 p-10 text-slate-100">
      <div className="mx-auto max-w-3xl">
        <h1 className="mb-1 text-lg font-semibold">Rascunho — árvore de busca ao vivo</h1>
        <p className="mb-8 text-sm text-slate-500">
          Simulação fixa, não conectada ao backend — só pra avaliar o conceito visual.
        </p>

        <div className="flex flex-col items-center gap-8">
          {/* nó raiz */}
          <div className="rounded-xl border border-emerald-700 bg-emerald-950/40 px-5 py-3 text-center shadow-lg shadow-emerald-950/50">
            <div className="text-[11px] uppercase tracking-wider text-emerald-500">modelo atual</div>
            <div className="text-2xl font-semibold tabular-nums">{scoreAtual.toFixed(4)}</div>
          </div>

          {/* linha conectora */}
          <div className="h-8 w-px bg-slate-700" />

          <div className="text-xs font-medium text-slate-400">{estagio.rotulo}</div>

          {/* candidatos sendo testados */}
          <div className="relative flex flex-wrap items-start justify-center gap-4">
            {/* linhas SVG conectando cada candidato ao centro (acima) */}
            <svg className="pointer-events-none absolute -top-6 left-0 h-6 w-full" preserveAspectRatio="none">
              {estagio.candidatos.map((_, i) => {
                const n = estagio.candidatos.length;
                const xPct = ((i + 0.5) / n) * 100;
                const vencedorAtivo = fase.concluido && i === estagio.vencedor;
                return (
                  <line
                    key={i}
                    x1="50%"
                    y1="0"
                    x2={`${xPct}%`}
                    y2="24"
                    stroke={vencedorAtivo ? "rgb(16 185 129)" : "rgb(51 65 85)"}
                    strokeWidth={vencedorAtivo ? 2 : 1}
                  />
                );
              })}
            </svg>

            {estagio.candidatos.map((c, i) => {
              const sendoTestado = !fase.concluido && i === fase.candidatoIdx;
              const jaTestado = !fase.concluido && i < fase.candidatoIdx;
              const eVencedor = fase.concluido && i === estagio.vencedor;
              const perdeu = fase.concluido && i !== estagio.vencedor;

              return (
                <div
                  key={c}
                  className={`rounded-lg border px-3 py-2 text-xs font-mono transition-all duration-300 ${
                    sendoTestado
                      ? "scale-110 border-sky-400 bg-sky-950/60 text-sky-200 shadow-lg shadow-sky-900/60 animate-pulse"
                      : eVencedor
                        ? "scale-105 border-emerald-500 bg-emerald-950/60 text-emerald-300 shadow-lg shadow-emerald-900/60"
                        : perdeu
                          ? "border-slate-800 bg-slate-900/40 text-slate-600 opacity-40"
                          : jaTestado
                            ? "border-slate-700 bg-slate-800/40 text-slate-500"
                            : "border-slate-800 bg-slate-900/40 text-slate-500"
                  }`}
                >
                  {c}
                  {sendoTestado && <div className="mt-0.5 text-[10px] text-sky-400">testando…</div>}
                  {eVencedor && <div className="mt-0.5 text-[10px] text-emerald-400">venceu ✓</div>}
                </div>
              );
            })}
          </div>
        </div>

        <div className="mt-10 rounded-lg border border-slate-800 bg-slate-900/50 p-4 text-xs text-slate-500">
          <p className="mb-1 font-medium text-slate-400">Como funcionaria de verdade:</p>
          <p>
            Hoje o backend só manda texto de log formatado (não estruturado por candidata) — pra essa
            animação refletir a busca real, o núcleo do Pedro_Wise precisaria logar CADA candidata testada
            (não só a vencedora de cada rodada), o que é uma mudança real no código já testado do algoritmo,
            não só na interface.
          </p>
        </div>
      </div>
    </div>
  );
}
