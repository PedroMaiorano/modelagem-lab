"use client";

import { useEffect, useState } from "react";
import PainelConfig from "./components/PainelConfig";
import PainelModulos from "./components/PainelModulos";
import PainelUpload from "./components/PainelUpload";
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
  forward_simples: true,
  transformacao_simples_nivel1: true,
  backward_simples_nivel1: true,
  min_vars_para_backward: 5,
  forward_duplo: true,
  forward_triplo: true,
  transformacao_simples_nivel2: true,
  backward_simples_nivel2: true,
  n_best_duplo: 5,
  n_best_triplo_1: 3,
  n_best_triplo_2: 3,
  nivel3_ativado: false,
  n_best_backward: 2,
  profundidade_maxima_nivel3: 2,
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

  async function aoPrepararNovoDataset(nomeDataset: string) {
    const lista = await buscarDatasets();
    setDatasets(lista);
    setConfig((c) => ({ ...c, dataset: nomeDataset }));
  }

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
      <PainelConfig
        datasets={datasets}
        config={config}
        aoMudar={setConfig}
        rodando={rodando}
        aoRodar={aoRodar}
        painelUpload={<PainelUpload aoPreparar={aoPrepararNovoDataset} />}
      />
      <main className="flex-1 overflow-y-auto p-6">
        <header className="mb-6 flex items-center justify-between border-b border-slate-800 pb-4">
          <div>
            <h1 className="text-lg font-semibold text-slate-100">Pedro_Wise — dashboard</h1>
            <p className="text-sm text-slate-500">
              Construção → categorização → transformação → treinamento, em tempo real.
            </p>
          </div>
          <div className="flex items-center gap-1.5 rounded-full border border-slate-800 bg-slate-900/50 px-2.5 py-1 text-[11px] text-slate-500">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
            backend conectado
          </div>
        </header>

        <div className="flex flex-col gap-6">
          {config.dataset && <PainelModulos dataset={config.dataset} />}
          <ProgressoAoVivo linhas={linhas} rodando={rodando} />
          {resultado && <PainelResultado resultado={resultado} />}
        </div>
      </main>
    </div>
  );
}
