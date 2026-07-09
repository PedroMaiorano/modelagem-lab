"use client";

import { useEffect, useState } from "react";
import PainelConfig from "./components/PainelConfig";
import PainelModulos from "./components/PainelModulos";
import PainelUpload from "./components/PainelUpload";
import SidebarDataset from "./components/SidebarDataset";
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

const ABAS = [
  { id: "dataset", rotulo: "Dataset" },
  { id: "modulos", rotulo: "Módulos" },
  { id: "treinamento", rotulo: "Treinamento" },
] as const;

type Aba = (typeof ABAS)[number]["id"];

export default function Pagina() {
  const [datasets, setDatasets] = useState<string[]>([]);
  const [config, setConfig] = useState<ConfigPipeline>(CONFIG_INICIAL);
  const [aba, setAba] = useState<Aba>("dataset");
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

  function limparResultado() {
    setLinhas([]);
    setResultado(null);
  }

  function aoMudarDataset(dataset: string) {
    setConfig((c) => ({ ...c, dataset }));
    limparResultado();
  }

  async function aoPrepararNovoDataset(nomeDataset: string) {
    const lista = await buscarDatasets();
    setDatasets(lista);
    aoMudarDataset(nomeDataset);
    setAba("modulos");
  }

  async function aoRodar() {
    setAba("treinamento");
    setRodando(true);
    limparResultado();
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
      <SidebarDataset
        datasets={datasets}
        dataset={config.dataset}
        aoMudarDataset={aoMudarDataset}
        rodando={rodando}
        aoRodar={aoRodar}
        aoLimpar={limparResultado}
        temResultado={linhas.length > 0 || resultado !== null}
        painelUpload={<PainelUpload aoPreparar={aoPrepararNovoDataset} />}
      />
      <main className="flex-1 overflow-y-auto p-6">
        <header className="mb-6 flex items-center justify-between">
          <div>
            <h1 className="text-lg font-semibold text-slate-100">Pedro_Wise — dashboard</h1>
            <p className="text-sm text-slate-500">
              Construção → categorização → transformação → treinamento, em tempo real.
            </p>
          </div>
          <div className="flex items-center gap-1.5 rounded-full border border-slate-800/60 px-2.5 py-1 text-[11px] text-slate-500">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
            backend conectado
          </div>
        </header>

        <nav className="mb-6 flex gap-1 border-b border-slate-800/60">
          {ABAS.map((a) => (
            <button
              key={a.id}
              onClick={() => setAba(a.id)}
              className={`px-4 py-2 text-sm font-medium transition border-b-2 -mb-px ${
                aba === a.id
                  ? "border-emerald-500 text-slate-100"
                  : "border-transparent text-slate-500 hover:text-slate-300"
              }`}
            >
              {a.rotulo}
            </button>
          ))}
        </nav>

        {aba === "dataset" && (
          <div className="max-w-lg">
            <p className="text-sm text-slate-500">
              Dataset ativo: <span className="text-slate-200">{config.dataset || "nenhum selecionado"}</span>
            </p>
            <p className="mt-1 text-xs text-slate-600">
              Use &ldquo;+ Novo dataset&rdquo; na barra lateral pra enviar um CSV novo, ou escolha um já
              preparado no seletor. Depois vá pra aba &ldquo;Módulos&rdquo; pra inspecionar construção e
              categorização, ou direto pra &ldquo;Treinamento&rdquo;.
            </p>
          </div>
        )}

        {aba === "modulos" &&
          (config.dataset ? (
            <PainelModulos key={config.dataset} dataset={config.dataset} />
          ) : (
            <p className="text-sm text-slate-600">Selecione um dataset primeiro.</p>
          ))}

        {aba === "treinamento" && (
          <div className="flex flex-col gap-8">
            <PainelConfig config={config} aoMudar={setConfig} rodando={rodando} />
            <div className="flex flex-col gap-6">
              <ProgressoAoVivo linhas={linhas} rodando={rodando} />
              {resultado && <PainelResultado resultado={resultado} />}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
