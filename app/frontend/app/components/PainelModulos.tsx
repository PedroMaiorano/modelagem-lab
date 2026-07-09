"use client";

import { useState } from "react";
import {
  rodarCategorizacaoTransformacao,
  rodarConstrucao,
  type ResultadoCategorizacaoTransformacao,
  type ResultadoConstrucao,
} from "../lib/api";

interface Props {
  dataset: string;
}

function BarraIVMini({ variavel, iv, classificacao, maximo }: { variavel: string; iv: number; classificacao: string; maximo: number }) {
  const largura = maximo > 0 ? Math.max(4, (iv / maximo) * 100) : 0;
  return (
    <div className="flex items-center gap-3 text-xs">
      <div className="w-36 shrink-0 truncate text-slate-400" title={variavel}>
        {variavel}
      </div>
      <div className="h-3 flex-1 overflow-hidden rounded-full bg-slate-800/50">
        <div className="h-full rounded bg-sky-600" style={{ width: `${largura}%` }} />
      </div>
      <div className="w-16 shrink-0 text-right tabular-nums text-slate-400">{iv.toFixed(3)}</div>
      <div className="w-40 shrink-0 truncate text-[11px] text-slate-500">{classificacao}</div>
    </div>
  );
}

function Etapa({
  titulo,
  descricao,
  aberta,
  aoAlternar,
  children,
}: {
  titulo: string;
  descricao: string;
  aberta: boolean;
  aoAlternar: () => void;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-xl border border-slate-800/50 bg-slate-900/30">
      <button
        onClick={aoAlternar}
        className="flex w-full items-center justify-between px-5 py-4 text-left"
      >
        <div>
          <h3 className="text-sm font-semibold text-slate-100">{titulo}</h3>
          <p className="text-xs text-slate-500">{descricao}</p>
        </div>
        <span className="text-slate-500 text-xs">{aberta ? "▾" : "▸"}</span>
      </button>
      {aberta && <div className="border-t border-slate-800/50 p-5">{children}</div>}
    </div>
  );
}

export default function PainelModulos({ dataset }: Props) {
  const [abertaConstrucao, setAbertaConstrucao] = useState(false);
  const [abertaCategorizacao, setAbertaCategorizacao] = useState(false);

  const [rodandoConstrucao, setRodandoConstrucao] = useState(false);
  const [resultadoConstrucao, setResultadoConstrucao] = useState<ResultadoConstrucao | null>(null);
  const [erroConstrucao, setErroConstrucao] = useState<string | null>(null);

  const [usarConstrucao, setUsarConstrucao] = useState(true);
  const [rodandoCategorizacao, setRodandoCategorizacao] = useState(false);
  const [resultadoCategorizacao, setResultadoCategorizacao] = useState<ResultadoCategorizacaoTransformacao | null>(
    null,
  );
  const [erroCategorizacao, setErroCategorizacao] = useState<string | null>(null);

  async function aoRodarConstrucao() {
    setRodandoConstrucao(true);
    setErroConstrucao(null);
    try {
      setResultadoConstrucao(await rodarConstrucao(dataset));
    } catch (e) {
      setErroConstrucao(String(e));
    } finally {
      setRodandoConstrucao(false);
    }
  }

  async function aoRodarCategorizacao() {
    setRodandoCategorizacao(true);
    setErroCategorizacao(null);
    try {
      setResultadoCategorizacao(await rodarCategorizacaoTransformacao(dataset, usarConstrucao));
    } catch (e) {
      setErroCategorizacao(String(e));
    } finally {
      setRodandoCategorizacao(false);
    }
  }

  const maximoIV = Math.max(0, ...(resultadoCategorizacao?.iv.map((i) => i.iv) ?? []));

  return (
    <div className="flex flex-col gap-4 max-w-3xl">
      <p className="text-sm text-slate-500">
        Rode e inspecione cada etapa isoladamente antes do treinamento.
      </p>

      <Etapa
        titulo="1. Construção"
        descricao="Razões/diferenças de negócio, quando aplicáveis ao dataset."
        aberta={abertaConstrucao}
        aoAlternar={() => setAbertaConstrucao((v) => !v)}
      >
        <button
          onClick={() => void aoRodarConstrucao()}
          disabled={rodandoConstrucao}
          className="rounded-lg bg-slate-800/60 border border-slate-700/50 px-3 py-1.5 text-xs font-medium text-slate-200 hover:border-emerald-700 hover:text-emerald-400 disabled:opacity-50"
        >
          {rodandoConstrucao ? "Rodando…" : "Rodar construção"}
        </button>
        {erroConstrucao && <p className="mt-2 text-xs text-red-400">{erroConstrucao}</p>}
        {resultadoConstrucao && (
          <div className="mt-3 text-xs text-slate-400">
            {resultadoConstrucao.colunas_novas.length === 0 ? (
              <p>Nenhuma razão de negócio aplicável a este dataset (colunas necessárias ausentes).</p>
            ) : (
              <>
                <p className="mb-1.5">
                  {resultadoConstrucao.colunas_novas.length} colunas novas de{" "}
                  {resultadoConstrucao.n_colunas_total} candidatas totais:
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {resultadoConstrucao.colunas_novas.map((c) => (
                    <span
                      key={c}
                      className="rounded-full border border-sky-800 bg-sky-950/50 px-2 py-0.5 text-[11px] text-sky-300"
                    >
                      {c}
                    </span>
                  ))}
                </div>
              </>
            )}
          </div>
        )}
      </Etapa>

      <Etapa
        titulo="2. Categorização + Transformação"
        descricao="Binning monotônico + WOE, com Information Value por variável."
        aberta={abertaCategorizacao}
        aoAlternar={() => setAbertaCategorizacao((v) => !v)}
      >
        <label className="mb-3 flex items-center gap-2 text-xs text-slate-300 cursor-pointer">
          <input
            type="checkbox"
            checked={usarConstrucao}
            onChange={(e) => setUsarConstrucao(e.target.checked)}
            className="h-3.5 w-3.5 rounded border-slate-600 bg-slate-800 text-emerald-500"
          />
          incluir variáveis construídas (etapa 1)
        </label>
        <button
          onClick={() => void aoRodarCategorizacao()}
          disabled={rodandoCategorizacao}
          className="rounded-lg bg-slate-800/60 border border-slate-700/50 px-3 py-1.5 text-xs font-medium text-slate-200 hover:border-emerald-700 hover:text-emerald-400 disabled:opacity-50"
        >
          {rodandoCategorizacao ? "Rodando…" : "Rodar categorização + transformação"}
        </button>
        {erroCategorizacao && <p className="mt-2 text-xs text-red-400">{erroCategorizacao}</p>}
        {resultadoCategorizacao && (
          <div className="mt-3 flex flex-col gap-2">
            <p className="text-xs text-slate-500">{resultadoCategorizacao.n_variaveis} variáveis transformadas</p>
            <div className="flex flex-col gap-1.5 max-h-64 overflow-y-auto">
              {resultadoCategorizacao.iv.map((item) => (
                <BarraIVMini key={item.variavel} maximo={maximoIV} {...item} />
              ))}
            </div>
          </div>
        )}
      </Etapa>

      <p className="text-xs text-slate-600">
        3. Treinamento (Pedro_Wise) — configure na aba &ldquo;Treinamento&rdquo; e rode em &ldquo;Rodar
        seleção&rdquo; na barra lateral.
      </p>
    </div>
  );
}
