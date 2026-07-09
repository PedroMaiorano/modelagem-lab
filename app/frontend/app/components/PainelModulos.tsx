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

function BarraIVMini({
  variavel,
  iv,
  classificacao,
  maximo,
}: {
  variavel: string;
  iv: number;
  classificacao: string;
  maximo: number;
}) {
  const largura = maximo > 0 ? Math.max(4, (iv / maximo) * 100) : 0;
  return (
    <div className="flex items-center gap-3 text-xs">
      <div className="w-28 shrink-0 truncate text-slate-400" title={variavel}>
        {variavel}
      </div>
      <div className="h-3 flex-1 overflow-hidden rounded-full bg-slate-800/50">
        <div className="h-full rounded-full bg-sky-600" style={{ width: `${largura}%` }} />
      </div>
      <div className="w-14 shrink-0 text-right tabular-nums text-slate-400">{iv.toFixed(3)}</div>
      <div className="w-32 shrink-0 truncate text-[11px] text-slate-500">{classificacao}</div>
    </div>
  );
}

function Modulo({
  numero,
  titulo,
  descricao,
  acoes,
  children,
}: {
  numero: number;
  titulo: string;
  descricao: string;
  acoes: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-4 rounded-xl border border-slate-800/50 bg-slate-900/30 p-5">
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="flex h-5 w-5 items-center justify-center rounded-full bg-slate-800 text-[11px] font-semibold text-slate-400">
              {numero}
            </span>
            <h3 className="text-sm font-semibold text-slate-100">{titulo}</h3>
          </div>
          <p className="mt-1 text-xs text-slate-500">{descricao}</p>
        </div>
        {acoes}
      </div>
      {children}
    </div>
  );
}

export default function PainelModulos({ dataset }: Props) {
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

  const botao = (rodando: boolean, aoClicar: () => void, rotulo: string) => (
    <button
      onClick={aoClicar}
      disabled={rodando}
      className="shrink-0 rounded-lg bg-slate-800/70 border border-slate-700/50 px-3 py-1.5 text-xs font-medium text-slate-200 transition hover:border-emerald-700 hover:text-emerald-400 disabled:opacity-50"
    >
      {rodando ? "Rodando…" : rotulo}
    </button>
  );

  return (
    <div className="flex flex-col gap-4">
      <p className="text-sm text-slate-500">Rode e inspecione cada etapa isoladamente antes do treinamento.</p>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <Modulo
          numero={1}
          titulo="Construção"
          descricao="Razões/diferenças de negócio, quando aplicáveis ao dataset."
          acoes={botao(rodandoConstrucao, () => void aoRodarConstrucao(), "Rodar")}
        >
          {erroConstrucao && <p className="text-xs text-red-400">{erroConstrucao}</p>}
          {!resultadoConstrucao && !erroConstrucao && (
            <p className="text-xs text-slate-600">Ainda não rodado.</p>
          )}
          {resultadoConstrucao &&
            (resultadoConstrucao.colunas_novas.length === 0 ? (
              <p className="text-xs text-slate-500">
                Nenhuma razão de negócio aplicável a este dataset (colunas necessárias ausentes).
              </p>
            ) : (
              <div className="text-xs text-slate-400">
                <p className="mb-2">
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
              </div>
            ))}
        </Modulo>

        <Modulo
          numero={2}
          titulo="Categorização + Transformação"
          descricao="Binning monotônico + WOE, com Information Value por variável."
          acoes={botao(rodandoCategorizacao, () => void aoRodarCategorizacao(), "Rodar")}
        >
          <label className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer">
            <input
              type="checkbox"
              checked={usarConstrucao}
              onChange={(e) => setUsarConstrucao(e.target.checked)}
              className="h-3.5 w-3.5 rounded border-slate-600 bg-slate-800 text-emerald-500"
            />
            incluir variáveis construídas (etapa 1)
          </label>
          {erroCategorizacao && <p className="text-xs text-red-400">{erroCategorizacao}</p>}
          {!resultadoCategorizacao && !erroCategorizacao && (
            <p className="text-xs text-slate-600">Ainda não rodado.</p>
          )}
          {resultadoCategorizacao && (
            <div className="flex flex-col gap-2">
              <p className="text-xs text-slate-500">{resultadoCategorizacao.n_variaveis} variáveis transformadas</p>
              <div className="flex flex-col gap-1.5 max-h-72 overflow-y-auto pr-1">
                {resultadoCategorizacao.iv.map((item) => (
                  <BarraIVMini key={item.variavel} maximo={maximoIV} {...item} />
                ))}
              </div>
            </div>
          )}
        </Modulo>
      </div>

      <p className="text-xs text-slate-600">
        3. Treinamento (Pedro_Wise) — configure na aba &ldquo;Treinamento&rdquo; e rode em &ldquo;Rodar
        seleção&rdquo; na barra lateral.
      </p>
    </div>
  );
}
