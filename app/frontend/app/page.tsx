"use client";

import { useEffect, useMemo, useState } from "react";
import GraficoScoreAoVivo from "./components/GraficoScoreAoVivo";
import ModeloAoVivo from "./components/ModeloAoVivo";
import PainelConfig from "./components/PainelConfig";
import PainelDatasetInfo from "./components/PainelDatasetInfo";
import PainelModulos from "./components/PainelModulos";
import PainelUpload from "./components/PainelUpload";
import SidebarDataset from "./components/SidebarDataset";
import ProgressoAoVivo, { type LinhaProgresso } from "./components/ProgressoAoVivo";
import PainelResultado from "./components/PainelResultado";
import { interpretarProgresso } from "./lib/progresso";
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
  gerar_transformacoes_potencia: true,
  gerar_bin_ordinal: true,
  usar_pre_selecao: false,
  limiar_variancia: 1e-6,
  limiar_iv: 0.02,
  limiar_correlacao: 0.9,
  p_valor_maximo: null,
};

const ABAS = [
  { id: "dataset", rotulo: "Dataset" },
  { id: "modulos", rotulo: "Módulos" },
  { id: "treinamento", rotulo: "Treinamento" },
  { id: "resultados", rotulo: "Resultados" },
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
  // Incrementado a cada "Limpar resultado" — entra na `key` do PainelModulos
  // pra forçar remontagem e limpar o estado local dele também (construção/
  // categorização rodadas), que não vive aqui em cima.
  const [resetKey, setResetKey] = useState(0);
  const estadoAoVivo = useMemo(() => interpretarProgresso(linhas), [linhas]);

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

  // Handler do botão "Limpar resultado" na sidebar: além de limpar o
  // treinamento, força o PainelModulos a remontar (via resetKey na key),
  // já que o estado de construção/categorização roda vive lá dentro, não
  // aqui em cima. `aoMudarDataset`/`aoRodar` não chamam isto — só o clique
  // explícito do usuário.
  function aoLimparTudo() {
    limparResultado();
    setResetKey((k) => k + 1);
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
          setAba("resultados");
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
    <div className="flex h-screen print:block print:h-auto">
      <SidebarDataset
        datasets={datasets}
        dataset={config.dataset}
        aoMudarDataset={aoMudarDataset}
        rodando={rodando}
        aoRodar={aoRodar}
        aoLimpar={aoLimparTudo}
        painelUpload={<PainelUpload aoPreparar={aoPrepararNovoDataset} />}
      />
      <main className="flex-1 overflow-y-auto p-6 print:overflow-visible print:p-0">
        <header className="mb-6 flex items-center justify-between print:hidden">
          <div>
            <h1 className="text-lg font-semibold text-slate-100">Pedro_Wise — dashboard</h1>
            <p className="text-sm text-slate-500">
              Construção → categorização → transformação → treinamento, em tempo real.
            </p>
          </div>
          <div className="flex items-center gap-1.5 rounded-full border border-slate-700 px-2.5 py-1 text-[11px] text-slate-500">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
            backend conectado
          </div>
        </header>

        <nav className="mb-6 flex gap-1 rounded-lg bg-slate-900/70 p-1 w-fit print:hidden">
          {ABAS.map((a) => (
            <button
              key={a.id}
              onClick={() => setAba(a.id)}
              className={`rounded-md px-4 py-1.5 text-sm font-medium transition ${
                aba === a.id
                  ? "bg-slate-700 text-white shadow-sm"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              {a.rotulo}
            </button>
          ))}
        </nav>

        {/* As 3 abas ficam sempre montadas (só escondidas via CSS) — desmontar
            e remontar a cada troca de aba resetava o estado local dos
            módulos (o que o usuário reportou como "abas limpando sozinhas"). */}
        <div className={aba === "dataset" ? "" : "hidden"}>
          {config.dataset ? (
            <PainelDatasetInfo key={config.dataset} dataset={config.dataset} />
          ) : (
            <p className="text-sm text-slate-600">Selecione um dataset primeiro.</p>
          )}
        </div>

        <div className={aba === "modulos" ? "" : "hidden"}>
          {config.dataset ? (
            <PainelModulos key={`${config.dataset}-${resetKey}`} dataset={config.dataset} />
          ) : (
            <p className="text-sm text-slate-600">Selecione um dataset primeiro.</p>
          )}
        </div>

        <div className={aba === "treinamento" ? "" : "hidden"}>
          <div className="flex flex-col gap-8">
            <PainelConfig config={config} aoMudar={setConfig} rodando={rodando} />
            <div className="grid grid-cols-1 gap-6 xl:grid-cols-[minmax(0,42rem)_1fr]">
              <ProgressoAoVivo linhas={linhas} rodando={rodando} />
              {(linhas.length > 0 || rodando) && (
                <div className="flex flex-col gap-6">
                  <ModeloAoVivo estado={estadoAoVivo} rodando={rodando} />
                  <div className="rounded-xl border border-slate-700 bg-slate-900/70 p-4">
                    <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-400">
                      Score ao longo da busca
                    </h3>
                    <GraficoScoreAoVivo historico={estadoAoVivo.historicoScore} />
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        <div className={aba === "resultados" ? "" : "hidden"}>
          {resultado ? (
            <div className="flex flex-col gap-6">
              {/* Só aparece na impressão/PDF — no navegador, dataset/hora já
                  estão implícitos no resto da UI, não precisa duplicar. */}
              <div className="hidden print:block">
                <h1 className="text-lg font-semibold text-slate-950">
                  Relatório Pedro_Wise — {config.dataset}
                </h1>
                <p className="text-sm text-slate-600">Gerado em {new Date().toLocaleString("pt-BR")}</p>
              </div>
              <div className="flex justify-end print:hidden">
                <button
                  onClick={() => window.print()}
                  className="rounded-lg border border-slate-600 bg-slate-800 px-3 py-1.5 text-xs font-medium text-slate-200 transition hover:border-emerald-700 hover:text-emerald-400"
                >
                  Exportar PDF
                </button>
              </div>
              <PainelResultado resultado={resultado} />
            </div>
          ) : (
            <p className="text-sm text-slate-600">
              Nenhum resultado ainda — configure na aba &ldquo;Treinamento&rdquo; e rode em &ldquo;Rodar
              seleção&rdquo; na barra lateral.
            </p>
          )}
        </div>
      </main>
    </div>
  );
}
