"use client";

import { useEffect, useRef, useState } from "react";
import type { EstagioTeste } from "../lib/progresso";

interface Props {
  estagiosTeste: EstagioTeste[];
  rodando: boolean;
}

const MS_POR_CANDIDATO = 70;
const MS_PAUSA_VENCEDOR = 350;
const MS_ESPERA_PROXIMO = 150;
const MAX_CANDIDATOS_EXIBIDOS = 12;
const MAX_HISTORICO = 4;

interface PosicaoAnimacao {
  indiceEstagio: number;
  indiceCandidato: number;
  concluido: boolean;
}

/** Anima a "árvore de busca" de forma DESACOPLADA da velocidade real do
 * backend — o Pedro_Wise avalia candidatas em paralelo e pode terminar uma
 * rodada em milissegundos, rápido demais pra acompanhar visualmente. Em vez
 * de reagir direto a cada eventos chegando, isto roda seu próprio timer
 * (~220ms por candidata) consumindo `estagiosTeste` no ritmo dele, sempre
 * lendo a versão mais recente via ref (nunca reinicia o timer quando um
 * novo estágio chega — só o `avancar()` já agendado passa a ver mais dado).
 */
function useAnimacaoArvore(estagiosTeste: EstagioTeste[]): PosicaoAnimacao {
  // `estagiosRef` só é lido/escrito dentro de efeitos (nunca durante o
  // render, que é o que a regra react-hooks/refs proíbe) — serve só pra o
  // laço de timers abaixo sempre enxergar a versão mais recente sem
  // precisar reiniciar o efeito (que roda uma vez só, `[]`) a cada linha
  // nova de log.
  const estagiosRef = useRef(estagiosTeste);
  useEffect(() => {
    estagiosRef.current = estagiosTeste;
  }, [estagiosTeste]);

  // O que é exibido vem de useState (nunca de ref.current durante o
  // render). A posição "atual" de verdade é uma variável comum dentro do
  // closure do efeito — não é ref nem state, só uma variável JS mutada
  // livremente pelo laço de ticks; a cada passo ela empurra uma cópia pro
  // useState só pra disparar o re-render.
  const [posicao, setPosicao] = useState<PosicaoAnimacao>({
    indiceEstagio: 0,
    indiceCandidato: 0,
    concluido: false,
  });

  useEffect(() => {
    let cancelado = false;
    let timeoutId: ReturnType<typeof setTimeout>;
    let atual: PosicaoAnimacao = { indiceEstagio: 0, indiceCandidato: 0, concluido: false };

    function avancar() {
      if (cancelado) return;
      const estagioAtual = estagiosRef.current[atual.indiceEstagio];

      if (!estagioAtual) {
        timeoutId = setTimeout(avancar, MS_ESPERA_PROXIMO);
        return;
      }

      const atraso = atual.concluido ? MS_PAUSA_VENCEDOR : MS_POR_CANDIDATO;
      timeoutId = setTimeout(() => {
        if (cancelado) return;
        if (atual.concluido) {
          atual = { indiceEstagio: atual.indiceEstagio + 1, indiceCandidato: 0, concluido: false };
        } else {
          const estagio = estagiosRef.current[atual.indiceEstagio];
          const proximo = atual.indiceCandidato + 1;
          const limite = estagio ? Math.min(estagio.candidatos.length, MAX_CANDIDATOS_EXIBIDOS) : 0;
          if (!estagio || proximo >= limite) {
            atual = { ...atual, concluido: true };
          } else {
            atual = { ...atual, indiceCandidato: proximo };
          }
        }
        setPosicao(atual);
        avancar();
      }, atraso);
    }

    avancar();
    return () => {
      cancelado = true;
      clearTimeout(timeoutId);
    };
  }, []);

  return posicao;
}

export default function ArvoreBuscaAoVivo({ estagiosTeste, rodando }: Props) {
  const pos = useAnimacaoArvore(estagiosTeste);

  if (estagiosTeste.length === 0) {
    return (
      <div className="flex min-h-[11rem] items-center justify-center text-xs text-slate-600">
        {rodando ? "Aguardando primeira rodada…" : "Nenhuma busca ainda."}
      </div>
    );
  }

  // A animação pode "vencer a corrida" do backend: o backend às vezes leva
  // vários segundos reais entre uma declaração "testando N candidatas" e a
  // próxima (nível 3, muitas trocas, etc.), então o índice animado alcança
  // o fim do array disponível bem antes de haver mais dado. Antes disso
  // ficava tela em branco esperando — em vez disso, trava exibindo o
  // último estágio já resolvido (com o vencedor destacado, parado) até o
  // próximo chegar, então sempre tem algo na tela.
  const indiceEstagio = Math.min(pos.indiceEstagio, estagiosTeste.length - 1);
  const aguardandoProximo = pos.indiceEstagio >= estagiosTeste.length;
  const estagio = estagiosTeste[indiceEstagio];
  const concluidoExibicao = pos.concluido || aguardandoProximo;
  const historico = estagiosTeste.slice(Math.max(0, indiceEstagio - MAX_HISTORICO), indiceEstagio);

  const candidatosExibidos = estagio.candidatos.slice(0, MAX_CANDIDATOS_EXIBIDOS);
  const restantes = estagio.candidatos.length - candidatosExibidos.length;

  return (
    <div className="flex min-h-[11rem] flex-col justify-center gap-4">
      {historico.length > 0 && (
        <div className="flex flex-wrap items-center gap-1.5 text-[10px] text-slate-600">
          {historico.map((h, i) => (
            <span key={i} className="flex items-center gap-1.5">
              <span className={h.vencedor ? "text-emerald-500" : "text-slate-600"}>
                {h.vencedor ?? "nenhuma melhorou"}
              </span>
              <span>→</span>
            </span>
          ))}
        </div>
      )}

      <div className="text-center text-xs font-medium text-slate-400">{estagio.rotulo}</div>

      <div className="relative flex flex-wrap items-start justify-center gap-3">
        <svg className="pointer-events-none absolute -top-5 left-0 h-5 w-full" preserveAspectRatio="none">
          {candidatosExibidos.map((_, i) => {
            const n = candidatosExibidos.length;
            const xPct = ((i + 0.5) / n) * 100;
            const vencedorAtivo = concluidoExibicao && candidatosExibidos[i] === estagio.vencedor;
            return (
              <line
                key={i}
                x1="50%"
                y1="0"
                x2={`${xPct}%`}
                y2="20"
                stroke={vencedorAtivo ? "rgb(16 185 129)" : "rgb(51 65 85)"}
                strokeWidth={vencedorAtivo ? 2 : 1}
              />
            );
          })}
        </svg>

        {candidatosExibidos.map((c, i) => {
          const sendoTestado = !concluidoExibicao && i === pos.indiceCandidato;
          const jaTestado = !concluidoExibicao && i < pos.indiceCandidato;
          const eVencedor = concluidoExibicao && c === estagio.vencedor;
          const perdeu = concluidoExibicao && c !== estagio.vencedor;

          return (
            <div
              key={c}
              className={`rounded-lg border px-2.5 py-1.5 text-[11px] font-mono transition-all duration-300 ${
                sendoTestado
                  ? "scale-110 border-sky-400 bg-sky-950/60 text-sky-200 shadow-md shadow-sky-900/60 animate-pulse"
                  : eVencedor
                    ? "scale-105 border-emerald-500 bg-emerald-950/60 text-emerald-300 shadow-md shadow-emerald-900/60"
                    : perdeu
                      ? "border-slate-800 bg-slate-900/40 text-slate-600 opacity-40"
                      : jaTestado
                        ? "border-slate-700 bg-slate-800/40 text-slate-500"
                        : "border-slate-800 bg-slate-900/40 text-slate-500"
              }`}
            >
              {c}
            </div>
          );
        })}
        {restantes > 0 && (
          <div className="rounded-lg border border-slate-800 bg-slate-900/40 px-2.5 py-1.5 text-[11px] text-slate-600">
            +{restantes} mais
          </div>
        )}
      </div>

      {concluidoExibicao && (
        <p className="text-center text-[11px] text-slate-500">
          {estagio.vencedor ? (
            <>
              vencedora: <span className="text-emerald-400">{estagio.vencedor}</span>
            </>
          ) : (
            "nenhuma candidata melhorou o score"
          )}
        </p>
      )}
    </div>
  );
}
