// Tipos e cliente da API do backend FastAPI. Ver app/backend/main.py.

export const URL_API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001";

export interface ConfigPipeline {
  dataset: string;
  usar_pipeline_completo: boolean;
  criterio: "teste" | "dev" | "min";
  shadow_probing: boolean;
  n_best_duplo: number;
  n_best_triplo_1: number;
  n_best_triplo_2: number;
}

export interface EventoEtapa {
  tipo: "etapa";
  mensagem: string;
}

export interface EventoLog {
  tipo: "log";
  mensagem: string;
}

export interface EventoErro {
  tipo: "erro";
  mensagem: string;
}

export interface ItemIV {
  variavel: string;
  iv: number;
}

export interface EventoResultado {
  tipo: "resultado";
  variaveis: string[];
  ks_dev: number | null;
  ks_teste: number;
  auc: number;
  n_eventos: number;
  top_iv: ItemIV[];
  tempo_segundos: number;
}

export type EventoProgresso = EventoEtapa | EventoLog | EventoErro | EventoResultado;

export async function buscarDatasets(): Promise<string[]> {
  const resp = await fetch(`${URL_API}/api/datasets`);
  if (!resp.ok) throw new Error(`Falha ao listar datasets (${resp.status})`);
  return resp.json();
}

/**
 * SSE via POST não é suportado pelo EventSource nativo do navegador (só GET) —
 * lê a resposta como stream via fetch e parseia os frames "data: {...}\n\n" à
 * mão. `onEvento` é chamado a cada frame assim que chega, dando o efeito de
 * progresso em tempo real que o dashboard antigo (Streamlit) não tinha.
 */
export async function rodarPipelineComProgresso(
  config: ConfigPipeline,
  onEvento: (evento: EventoProgresso) => void,
  sinal?: AbortSignal,
): Promise<void> {
  const resp = await fetch(`${URL_API}/api/pipeline/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(config),
    signal: sinal,
  });
  if (!resp.ok || !resp.body) {
    throw new Error(`Falha ao iniciar pipeline (${resp.status})`);
  }

  const leitor = resp.body.getReader();
  const decodificador = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await leitor.read();
    if (done) break;
    buffer += decodificador.decode(value, { stream: true });

    // sse-starlette/uvicorn terminam cada frame com "\r\n\r\n" (CRLF), não "\n\n" —
    // confirmado inspecionando os bytes reais da resposta (não documentado, só
    // observável rodando). Regex cobre os dois casos por robustez.
    const frames = buffer.split(/\r?\n\r?\n/);
    buffer = frames.pop() ?? ""; // último frame pode estar incompleto — guarda pro próximo chunk

    for (const frame of frames) {
      const linhaDados = frame.split(/\r?\n/).find((l) => l.startsWith("data: "));
      if (!linhaDados) continue; // frames de "ping" (keepalive) não têm "data:"
      const json = linhaDados.slice("data: ".length);
      onEvento(JSON.parse(json) as EventoProgresso);
    }
  }
}
