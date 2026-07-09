"use client";

import { useEffect, useState } from "react";
import { buscarPreviewDataset, type PreviewDataset } from "../lib/api";

interface Props {
  dataset: string;
}

function Cartao({ rotulo, valor }: { rotulo: string; valor: string | number }) {
  return (
    <div className="rounded-xl border border-slate-800/50 bg-slate-900/30 px-4 py-3">
      <div className="text-[11px] uppercase tracking-wider text-slate-500">{rotulo}</div>
      <div className="mt-1 text-xl font-semibold text-slate-100 tabular-nums">{valor}</div>
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

  return (
    <div className="flex flex-col gap-6">
      <div className="grid grid-cols-3 gap-3 max-w-xl">
        <Cartao rotulo="Linhas (dev)" valor={preview.n_dev} />
        <Cartao rotulo="Linhas (teste)" valor={preview.n_teste} />
        <Cartao rotulo="Colunas" valor={preview.colunas.length} />
      </div>

      <div>
        <h2 className="mb-2 text-xs font-medium uppercase tracking-wider text-slate-500">
          Amostra (5 primeiras linhas de dev)
        </h2>
        <div className="overflow-x-auto rounded-xl border border-slate-800/50 bg-slate-900/30">
          <table className="min-w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-800/50 text-slate-500">
                {preview.colunas.map((c) => (
                  <th key={c} className="whitespace-nowrap px-3 py-2 font-medium">
                    {c}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {preview.amostra.map((linha, i) => (
                <tr key={i} className="border-b border-slate-800/30 last:border-0">
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
