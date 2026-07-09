"use client";

import { useEffect, useState } from "react";
import PainelConfig from "./components/PainelConfig";
import ProgressoAoVivo, { type LinhaProgresso } from "./components/ProgressoAoVivo";
import PainelResultado from "./components/PainelResultado";
import {
  buscarDatasets,
  rodarPipelineComProgresso,
  type ConfigPipeline,
  type EventoResultado,
} from "./lib/api";

const CONFIG_INICIAL: ConfigPipeline = {
  dataset: "",
  usar_pipeline_completo: true,
  criterio: "teste",
  shadow_probing: false,
  n_best_duplo: 5,
  n_best_triplo_1: 3,
  n_best_triplo_2: 3,
};

export default function Pagina() {
  const [datasets, setDatasets] = useState<string[]>([]);
  const [config, setConfig] = useState<ConfigPipeline>(CONFIG_INICIAL);
  const [rodando, setRodando] = useState(false);
  const [linhas, setLinhas] = useState<LinhaProgresso[]>([]);
  const [resultado, setResultado] = useState<EventoResultado | null>(null);
  const [erroCarregamento, setErroCarregamento] = useState<string | null>(null);

  useEffect(() => {
    buscarDatasets()
      .then((lista) => {
        setDatasets(lista);
        if (lista.length > 0) setConfig((c) => ({ ...c, dataset: lista[0] }));
      })
      .catch((e) => setErroCarregamento(String(e)));
  }, []);

  async function aoRodar() {
    setRodando(true);
    setLinhas([]);
    setResultado(null);
    try {
      await rodarPipelineComProgresso(config, (evento) => {
        if (evento.tipo === "resultado") {
          setResultado(evento);
        } else {
          setLinhas((atual) => [...atual, evento]);
        }
      });
    } catch (e) {
      setLinhas((atual) => [...atual, { tipo: "erro", mensagem: String(e) }]);
    } finally {
      setRodando(false);
    }
  }

  if (erroCarregamento) {
    return (
      <div className="flex h-screen items-center justify-center p-8 text-center">
        <div className="max-w-md">
          <p className="font-semibold text-red-400">Não foi possível conectar ao backend.</p>
          <p className="mt-2 text-sm text-slate-500">{erroCarregamento}</p>
          <p className="mt-4 text-xs text-slate-600">
            Suba o backend:{" "}
            <code className="rounded bg-slate-900 px-1.5 py-0.5">
              python -m uvicorn main:app --port 8001 --app-dir app/backend
            </code>
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen">
      <PainelConfig datasets={datasets} config={config} aoMudar={setConfig} rodando={rodando} aoRodar={aoRodar} />
      <main className="flex-1 overflow-y-auto p-6">
        <header className="mb-6">
          <h1 className="text-lg font-semibold text-slate-100">Pedro_Wise — dashboard</h1>
          <p className="text-sm text-slate-500">
            Construção → categorização → transformação → treinamento, em tempo real.
          </p>
        </header>

        <div className="flex flex-col gap-6">
          <ProgressoAoVivo linhas={linhas} rodando={rodando} />
          {resultado && <PainelResultado resultado={resultado} />}
        </div>
      </main>
    </div>
  );
}
