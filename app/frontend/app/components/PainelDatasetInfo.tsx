"use client";

import { useEffect, useState } from "react";
import {
  buscarPreviewDataset,
  type PreviewDataset,
  type ResumoColunaCategorica,
  type ResumoColunaNumerica,
} from "../lib/api";

interface Props {
  dataset: string;
}

function Cartao({ rotulo, valor }: { rotulo: string; valor: string | number }) {
  return (
    <div className="rounded-xl border border-slate-700 bg-slate-900/70 px-4 py-3">
      <div className="text-[11px] uppercase tracking-wider text-slate-500">{rotulo}</div>
      <div className="mt-1 text-xl font-semibold text-slate-100 tabular-nums">{valor}</div>
    </div>
  );
}

/** Régua de IV comum em scorecards (Siddiqi): <0.02 sem poder preditivo,
 * 0.02-0.1 fraco, 0.1-0.3 médio, 0.3-0.5 forte, >0.5 suspeito (possível
 * vazamento) — mesma classificação do backend (`classificar_iv`), só pra
 * colorir aqui sem precisar de mais uma chamada de API. */
function corIV(iv: number): string {
  if (iv < 0.02) return "text-slate-500";
  if (iv < 0.1) return "text-slate-300";
  if (iv < 0.3) return "text-sky-400";
  if (iv < 0.5) return "text-emerald-400";
  return "text-amber-400";
}

function CelulaIV({ iv }: { iv: number | null }) {
  if (iv === null) return <td className="whitespace-nowrap px-3 py-1.5 text-right text-slate-600">—</td>;
  return (
    <td className={`whitespace-nowrap px-3 py-1.5 text-right tabular-nums font-medium ${corIV(iv)}`}>
      {iv.toFixed(3)}
    </td>
  );
}

function BarraAusente({ pct }: { pct: number }) {
  const cor = pct === 0 ? "bg-slate-700" : pct < 0.05 ? "bg-amber-600" : "bg-rose-600";
  return (
    <div className="flex items-center justify-end gap-2">
      <div className="h-1.5 w-12 overflow-hidden rounded-full bg-slate-800">
        <div className={`h-full ${cor}`} style={{ width: `${Math.min(100, pct * 100)}%` }} />
      </div>
      <span className={`tabular-nums ${pct === 0 ? "text-slate-500" : "text-amber-400"}`}>
        {(pct * 100).toFixed(1)}%
      </span>
    </div>
  );
}

export default function PainelDatasetInfo({ dataset }: Props) {
  const [preview, setPreview] = useState<PreviewDataset | null>(null);
  const [datasetDoPreview, setDatasetDoPreview] = useState<string | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    let cancelado = false;
    buscarPreviewDataset(dataset)
      .then((p) => {
        if (cancelado) return;
        setPreview(p);
        setDatasetDoPreview(dataset);
        setErro(null);
      })
      .catch((e) => {
        if (cancelado) return;
        setErro(String(e));
        setDatasetDoPreview(dataset);
      });
    return () => {
      cancelado = true;
    };
  }, [dataset]);

  const carregando = datasetDoPreview !== dataset;

  if (carregando) return <p className="text-sm text-slate-600">Carregando…</p>;
  if (erro) return <p className="text-sm text-red-400">{erro}</p>;
  if (!preview) return null;

  const porIvDesc = (a: string, b: string) =>
    (preview.resumo_colunas[b]?.iv ?? -1) - (preview.resumo_colunas[a]?.iv ?? -1);

  const colunasVisiveis = preview.colunas.filter((c) => c !== "y");
  const numericas = colunasVisiveis
    .filter((c) => preview.resumo_colunas[c]?.tipo === "numerico")
    .sort(porIvDesc) as string[];
  const categoricas = colunasVisiveis
    .filter((c) => preview.resumo_colunas[c]?.tipo === "categorico")
    .sort(porIvDesc);

  return (
    <div className="flex flex-col gap-6">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 max-w-2xl">
        <Cartao rotulo="Linhas (dev)" valor={preview.n_dev} />
        <Cartao rotulo="Linhas (teste)" valor={preview.n_teste} />
        <Cartao rotulo="Colunas" valor={preview.colunas.length} />
        <Cartao
          rotulo="Taxa de mau (dev)"
          valor={preview.taxa_evento_dev !== null ? `${(preview.taxa_evento_dev * 100).toFixed(1)}%` : "—"}
        />
      </div>

      {numericas.length > 0 && (
        <div>
          <h2 className="mb-2 text-xs font-medium uppercase tracking-wider text-slate-500">
            Colunas numéricas
          </h2>
          <div className="overflow-x-auto rounded-xl border border-slate-700 bg-slate-900/70">
            <table className="min-w-full text-left text-xs">
              <thead>
                <tr className="border-b border-slate-700 text-slate-500">
                  <th className="whitespace-nowrap px-3 py-2 font-medium">coluna</th>
                  <th className="whitespace-nowrap px-3 py-2 text-right font-medium">% ausente</th>
                  <th className="whitespace-nowrap px-3 py-2 text-right font-medium">mínimo</th>
                  <th className="whitespace-nowrap px-3 py-2 text-right font-medium">máximo</th>
                  <th className="whitespace-nowrap px-3 py-2 text-right font-medium">média</th>
                  <th className="whitespace-nowrap px-3 py-2 text-right font-medium">desvio</th>
                  <th className="whitespace-nowrap px-3 py-2 text-right font-medium">IV</th>
                </tr>
              </thead>
              <tbody>
                {numericas.map((c, i) => {
                  const r = preview.resumo_colunas[c] as ResumoColunaNumerica;
                  return (
                    <tr
                      key={c}
                      className={`border-b border-slate-800 last:border-0 ${i % 2 === 1 ? "bg-slate-800/20" : ""}`}
                    >
                      <td className="whitespace-nowrap px-3 py-1.5 font-mono text-sky-300">{c}</td>
                      <td className="whitespace-nowrap px-3 py-1.5 text-right">
                        <BarraAusente pct={r.pct_ausente} />
                      </td>
                      <td className="whitespace-nowrap px-3 py-1.5 text-right tabular-nums text-slate-300">
                        {r.minimo.toFixed(2)}
                      </td>
                      <td className="whitespace-nowrap px-3 py-1.5 text-right tabular-nums text-slate-300">
                        {r.maximo.toFixed(2)}
                      </td>
                      <td className="whitespace-nowrap px-3 py-1.5 text-right tabular-nums text-slate-300">
                        {r.media.toFixed(2)}
                      </td>
                      <td className="whitespace-nowrap px-3 py-1.5 text-right tabular-nums text-slate-400">
                        {r.desvio_padrao.toFixed(2)}
                      </td>
                      <CelulaIV iv={r.iv} />
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {categoricas.length > 0 && (
        <div>
          <h2 className="mb-2 text-xs font-medium uppercase tracking-wider text-slate-500">
            Colunas categóricas
          </h2>
          <div className="overflow-x-auto rounded-xl border border-slate-700 bg-slate-900/70">
            <table className="min-w-full text-left text-xs">
              <thead>
                <tr className="border-b border-slate-700 text-slate-500">
                  <th className="whitespace-nowrap px-3 py-2 font-medium">coluna</th>
                  <th className="whitespace-nowrap px-3 py-2 text-right font-medium">% ausente</th>
                  <th className="whitespace-nowrap px-3 py-2 text-right font-medium">distintos</th>
                  <th className="whitespace-nowrap px-3 py-2 font-medium">top valores</th>
                  <th className="whitespace-nowrap px-3 py-2 text-right font-medium">IV</th>
                </tr>
              </thead>
              <tbody>
                {categoricas.map((c, i) => {
                  const r = preview.resumo_colunas[c] as ResumoColunaCategorica;
                  return (
                    <tr
                      key={c}
                      className={`border-b border-slate-800 last:border-0 ${i % 2 === 1 ? "bg-slate-800/20" : ""}`}
                    >
                      <td className="whitespace-nowrap px-3 py-1.5 font-mono text-violet-300">{c}</td>
                      <td className="whitespace-nowrap px-3 py-1.5 text-right">
                        <BarraAusente pct={r.pct_ausente} />
                      </td>
                      <td className="whitespace-nowrap px-3 py-1.5 text-right tabular-nums text-slate-300">
                        {r.n_distintos}
                      </td>
                      <td className="px-3 py-1.5 text-slate-400">
                        {r.top_valores
                          .slice(0, 3)
                          .map((v) => `${v.valor} (${v.contagem})`)
                          .join(", ")}
                      </td>
                      <CelulaIV iv={r.iv} />
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <div>
        <h2 className="mb-2 text-xs font-medium uppercase tracking-wider text-slate-500">
          Amostra (5 primeiras linhas de dev)
        </h2>
        <div className="overflow-x-auto rounded-xl border border-slate-700 bg-slate-900/70">
          <table className="min-w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-700 text-slate-500">
                {preview.colunas.map((c) => (
                  <th key={c} className="whitespace-nowrap px-3 py-2 font-medium">
                    {c}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {preview.amostra.map((linha, i) => (
                <tr
                  key={i}
                  className={`border-b border-slate-800 last:border-0 ${i % 2 === 1 ? "bg-slate-800/20" : ""}`}
                >
                  {preview.colunas.map((c) => (
                    <td key={c} className="whitespace-nowrap px-3 py-1.5 text-slate-300">
                      {String(linha[c])}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
