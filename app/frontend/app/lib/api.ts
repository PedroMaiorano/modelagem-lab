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
  gerar_transformacoes_potencia: boolean;
  gerar_bin_ordinal: boolean;
  // Pré-seleção (módulo 3) — opt-in
  usar_pre_selecao: boolean;
  limiar_variancia: number | null;
  limiar_iv: number | null;
  limiar_correlacao: number | null;
  // Restrição de significância — null desliga
  p_valor_maximo: number | null;
  // Só relevante quando p_valor_maximo está ativo: roda a busca de novo sem
  // o filtro, pra comparação (dobra o tempo de treinamento).
  comparar_sem_p_valor: boolean;
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

export interface ParConstrucao {
  numerador: string;
  denominador: string;
  nome?: string;
  operacao: "razao" | "diferenca";
}

export async function rodarConstrucao(
  dataset: string,
  paresCustomizados: ParConstrucao[] = [],
): Promise<ResultadoConstrucao> {
  const resp = await fetch(`${URL_API}/api/modulo/construcao`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ dataset, pares_customizados: paresCustomizados }),
  });
  if (!resp.ok) throw new Error(`Falha ao rodar construção (${resp.status})`);
  return resp.json();
}

export async function rodarCategorizacaoTransformacao(
  dataset: string,
  usarConstrucao: boolean,
  paresCustomizados: ParConstrucao[] = [],
  gerarTransformacoesPotencia: boolean = true,
  gerarBinOrdinal: boolean = true,
): Promise<ResultadoCategorizacaoTransformacao> {
  const resp = await fetch(`${URL_API}/api/modulo/categorizacao-transformacao`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      dataset,
      usar_construcao: usarConstrucao,
      pares_customizados: paresCustomizados,
      gerar_transformacoes_potencia: gerarTransformacoesPotencia,
      gerar_bin_ordinal: gerarBinOrdinal,
    }),
  });
  if (!resp.ok) throw new Error(`Falha ao rodar categorização + transformação (${resp.status})`);
  return resp.json();
}

export interface ConfigPreSelecao {
  dataset: string;
  usar_construcao: boolean;
  pares_customizados: ParConstrucao[];
  gerar_transformacoes_potencia: boolean;
  gerar_bin_ordinal: boolean;
  limiar_variancia: number | null;
  limiar_iv: number | null;
  limiar_correlacao: number | null;
}

export interface ParCorrelacionado {
  mantida: string;
  descartada: string;
  correlacao: number;
}

export interface ResultadoPreSelecao {
  n_inicial: number;
  n_apos_variancia: number;
  n_apos_iv: number;
  n_final: number;
  colunas_mantidas: string[];
  pares_correlacionados_descartados: ParCorrelacionado[];
}

export async function rodarPreSelecao(config: ConfigPreSelecao): Promise<ResultadoPreSelecao> {
  const resp = await fetch(`${URL_API}/api/modulo/pre-selecao`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(config),
  });
  if (!resp.ok) throw new Error(`Falha ao rodar pré-seleção (${resp.status})`);
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

export interface FaixaDecil {
  faixa: number;
  n: number;
  taxa_evento: number;
  pct_eventos_capturados: number;
  pct_nao_eventos_capturados: number;
  ks_acumulado: number;
}

export interface Coeficiente {
  variavel: string;
  coeficiente: number;
  erro_padrao: number;
  p_valor: number;
}

export interface ResultadoSemFiltroPValor {
  variaveis: string[];
  ks_teste: number;
  auc: number;
}

export interface EventoResultado {
  tipo: "resultado";
  variaveis: string[];
  ks_dev: number;
  ks_teste: number;
  auc: number;
  gini: number;
  taxa_evento_dev: number;
  taxa_evento_teste: number;
  n_eventos: number;
  top_iv: ItemIV[];
  tabela_decis: FaixaDecil[];
  intercepto: number;
  intercepto_erro_padrao: number;
  intercepto_p_valor: number;
  coeficientes: Coeficiente[];
  resultado_sem_filtro_pvalor: ResultadoSemFiltroPValor | null;
  tempo_segundos: number;
}

export type EventoProgresso = EventoEtapa | EventoLog | EventoErro | EventoResultado;

export async function buscarDatasets(): Promise<string[]> {
  const resp = await fetch(`${URL_API}/api/datasets`);
  if (!resp.ok) throw new Error(`Falha ao listar datasets (${resp.status})`);
  return resp.json();
}

export interface ResumoColunaNumerica {
  tipo: "numerico";
  pct_ausente: number;
  minimo: number;
  maximo: number;
  media: number;
  desvio_padrao: number;
}

export interface ResumoColunaCategorica {
  tipo: "categorico";
  pct_ausente: number;
  n_distintos: number;
  top_valores: { valor: string; contagem: number }[];
}

export type ResumoColuna = ResumoColunaNumerica | ResumoColunaCategorica;

export interface PreviewDataset {
  colunas: string[];
  colunas_numericas: string[];
  n_dev: number;
  n_teste: number;
  taxa_evento_dev: number | null;
  taxa_evento_teste: number | null;
  resumo_colunas: Record<string, ResumoColuna>;
  amostra: Record<string, unknown>[];
}

export async function buscarPreviewDataset(nome: string): Promise<PreviewDataset> {
  const resp = await fetch(`${URL_API}/api/datasets/${encodeURIComponent(nome)}/preview`);
  if (!resp.ok) throw new Error(`Falha ao carregar preview de '${nome}' (${resp.status})`);
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

// ---------------------------------------------------------------------------
// Feature-lab (esferas 1/2, experimental). Ver app/backend/feature_lab.py.
// ---------------------------------------------------------------------------

export interface InfoPainel {
  colunas: string[];
  chave_sugerida: string;
  tempo_sugerido: string;
  colunas_valor_disponiveis: string[];
  n_linhas: number;
  n_chaves: number;
}

export interface ConfigFeatureLab {
  painel: string;
  chave: string;
  coluna_tempo: string;
  colunas_valor: string[];
  janelas: number[];
  profundidade_maxima: number;
  n_arvores: number;
  min_suporte: number;
  max_suporte: number;
  max_regras: number;
  permitir_cruzamento_entre_bases: boolean;
}

export interface RegraFeatureLab {
  regra: string;
  suporte_dev: number;
  suporte_teste: number;
  iv_dev: number;
  iv_teste: number;
}

export interface ResultadoFeatureLab {
  n_linhas_painel: number;
  n_chaves: number;
  colunas_geradas: string[];
  n_dev: number;
  n_teste: number;
  taxa_evento_dev: number;
  taxa_evento_teste: number;
  regras: RegraFeatureLab[];
  melhor_regra: string | null;
  auc_sem_regra: number | null;
  auc_com_regra: number | null;
}

export async function listarPaineis(): Promise<string[]> {
  const resp = await fetch(`${URL_API}/api/feature-lab/paineis`);
  if (!resp.ok) throw new Error(`Falha ao listar painéis (${resp.status})`);
  return resp.json();
}

export async function buscarInfoPainel(nome: string): Promise<InfoPainel> {
  const resp = await fetch(`${URL_API}/api/feature-lab/paineis/${encodeURIComponent(nome)}/info`);
  if (!resp.ok) throw new Error(`Falha ao buscar info do painel (${resp.status})`);
  return resp.json();
}

export async function rodarFeatureLab(config: ConfigFeatureLab): Promise<ResultadoFeatureLab> {
  const resp = await fetch(`${URL_API}/api/feature-lab/rodar`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(config),
  });
  if (!resp.ok) {
    const corpo = await resp.json().catch(() => null);
    throw new Error(corpo?.detail ?? `Falha ao rodar feature-lab (${resp.status})`);
  }
  return resp.json();
}
