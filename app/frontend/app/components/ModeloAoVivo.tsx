"use client";

import { useEffect, useRef, useState } from "react";
import type { EstadoAoVivo } from "../lib/progresso";

interface Props {
  estado: EstadoAoVivo;
  rodando: boolean;
}

function useCronometro(rodando: boolean): number {
  // `segundos` só é lido/escrito via state (nunca lendo ref.current nem
  // chamando Date.now() durante o render — as regras mais novas do
  // react-hooks/eslint proíbem os dois, "refs"/"purity"). O ref só guarda o
  // timestamp de início (escrita em efeito é permitida, leitura não é
  // durante render); o setState roda dentro do callback do setInterval,
  // nunca direto no corpo síncrono do efeito (react-hooks/set-state-in-effect).
  const [segundos, setSegundos] = useState(0);
  const inicioRef = useRef<number | null>(null);

  useEffect(() => {
    if (!rodando) {
      inicioRef.current = null;
      return;
    }
    inicioRef.current = Date.now();
    const id = setInterval(() => {
      setSegundos(inicioRef.current ? Math.floor((Date.now() - inicioRef.current) / 1000) : 0);
    }, 1000);
    return () => clearInterval(id);
  }, [rodando]);

  return segundos;
}

export default function ModeloAoVivo({ estado, rodando }: Props) {
  const segundos = useCronometro(rodando);
  const { variaveisAtuais, scoreAtual, estagioAtual, nEventosAceitos } = estado;

  return (
    <div className="rounded-xl border border-slate-700 bg-slate-900/70 p-4">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400">Modelo atual</h3>
        {rodando && (
          <span className="flex items-center gap-1.5 text-[11px] text-slate-500">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
            {segundos}s · {nEventosAceitos} atualizações aceitas
          </span>
        )}
      </div>

      <div className="mb-3 flex items-baseline gap-2">
        <span className="text-2xl font-semibold tabular-nums text-slate-100">
          {scoreAtual !== null ? scoreAtual.toFixed(4) : "—"}
        </span>
        <span className="text-xs text-slate-500">score</span>
      </div>

      {estagioAtual && (
        <p className="mb-3 text-xs text-slate-400">
          <span className="text-slate-600">estágio: </span>
          {estagioAtual}
        </p>
      )}

      {variaveisAtuais.length > 0 ? (
        <div className="flex flex-wrap gap-1.5">
          {variaveisAtuais.map((v) => (
            <span
              key={v}
              className="rounded-full border border-emerald-800 bg-emerald-950/50 px-2.5 py-1 text-xs text-emerald-300"
            >
              {v}
            </span>
          ))}
        </div>
      ) : (
        <p className="text-xs text-slate-600">Nenhuma variável aceita ainda.</p>
      )}
    </div>
  );
}
