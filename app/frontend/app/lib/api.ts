// Tipos e cliente da API do backend FastAPI. Ver app/backend/main.py.

export const URL_API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001";

export interface ConfigPipeline {
  dataset: string;
  usar_pipeline_completo: boolean;
  criterio: "teste" | "dev" | "min";
  shadow_probing: boolean;
  // Nível 1
  forward_simples: boolean;
  transformacao_simples_nivel1: boolean;
  backward_simples_nivel1: boolean;
  min_vars_para_backward: number;
  // Nível 2 / 2.5
  forward_duplo: boolean;
  forward_triplo: boolean;
  transformacao_simples_nivel2: boolean;
  backward_simples_nivel2: boolean;
  n_best_duplo: number;
  n_best_triplo_1: number;
  n_best_triplo_2: number;
  // Nível 3
  nivel3_ativado: boolean;
  n_best_backward: number;
  profundidade_maxima_nivel3: number;
}

// ---------------------------------------------------------------------------
// Ingestão: upload de CSV, detecção de colunas, split. Ver app/backend/ingestao.py.
// ---------------------------------------------------------------------------

export interface ColunaDetectada {
  nome: string;
  tipo: "numerico" | "data" | "categorico";
  formato_data: string | null;
  n_distintos: number;
  exemplos: string[];
}

export interface RespostaUpload {
  upload_id: string;
  n_linhas: number;
  colunas: ColunaDetectada[];
}

export interface ValorDistinto {
  valor: string;
  contagem: number;
}

export type ConfigSplit =
  | { modo: "amostra"; coluna: string; valores_dev: string[]; valores_teste: string[] }
  | { modo: "oot"; coluna: string; formato: string; corte: string }
  | { modo: "aleatorio"; proporcao_teste: number; semente: number };

export interface ConfigPreparar {
  upload_id: string;
  nome_dataset: string;
  coluna_resposta: string;
  split: ConfigSplit;
}

export async function uploadDataset(arquivo: File): Promise<RespostaUpload> {
  const form = new FormData();
  form.append("arquivo", arquivo);
  const resp = await fetch(`${URL_API}/api/dataset/upload`, { method: "POST", body: form });
  if (!resp.ok) throw new Error(`Falha ao enviar arquivo (${resp.status})`);
  return resp.json();
}

export async function buscarValoresDistintos(uploadId: string, coluna: string): Promise<ValorDistinto[]> {
  const resp = await fetch(
    `${URL_API}/api/dataset/${uploadId}/coluna/${encodeURIComponent(coluna)}/valores`,
  );
  if (!resp.ok) throw new Error(`Falha ao buscar valores de '${coluna}' (${resp.status})`);
  return resp.json();
}

export async function sugerirCorte(
  uploadId: string,
  coluna: string,
  formato: string,
  proporcaoTeste: number,
): Promise<string> {
  const params = new URLSearchParams({
    upload_id: uploadId,
    coluna,
    formato,
    proporcao_teste: String(proporcaoTeste),
  });
  const resp = await fetch(`${URL_API}/api/dataset/sugerir-corte?${params}`);
  if (!resp.ok) throw new Error(`Falha ao sugerir corte (${resp.status})`);
  const dados = await resp.json();
  return dados.corte;
}

// ---------------------------------------------------------------------------
// Módulos isolados (Fase 3): construção e categorização+transformação
// rodam e são inspecionados separadamente do treinamento (que continua em
// rodarPipelineComProgresso). Ver app/backend/main.py.
// ---------------------------------------------------------------------------

export interface ResultadoConstrucao {
  colunas_novas: string[];
  n_colunas_total: number;
  amostra: Record<string, unknown>[];
}

export interface ItemIVDetalhado extends ItemIV {
  classificacao: string;
}

export interface ResultadoCategorizacaoTransformacao {
  n_variaveis: number;
  iv: ItemIVDetalhado[];
}

export async function rodarConstrucao(dataset: string): Promise<ResultadoConstrucao> {
  const resp = await fetch(`${URL_API}/api/modulo/construcao?${new URLSearchParams({ dataset })}`, {
    method: "POST",
  });
  if (!resp.ok) throw new Error(`Falha ao rodar construção (${resp.status})`);
  return resp.json();
}

export async function rodarCategorizacaoTransformacao(
  dataset: string,
  usarConstrucao: boolean,
): Promise<ResultadoCategorizacaoTransformacao> {
  const params = new URLSearchParams({ dataset, usar_construcao: String(usarConstrucao) });
  const resp = await fetch(`${URL_API}/api/modulo/categorizacao-transformacao?${params}`, {
    method: "POST",
  });
  if (!resp.ok) throw new Error(`Falha ao rodar categorização + transformação (${resp.status})`);
  return resp.json();
}

export async function prepararDataset(
  config: ConfigPreparar,
): Promise<{ nome_dataset: string; n_dev: number; n_teste: number }> {
  const resp = await fetch(`${URL_API}/api/dataset/preparar`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(config),
  });
  if (!resp.ok) {
    const detalhe = await resp.json().catch(() => null);
    throw new Error(detalhe?.detail ?? `Falha ao preparar dataset (${resp.status})`);
  }
  return resp.json();
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
