"use client";

import { useEffect, useState } from "react";
import {
  buscarPreviewDataset,
  ESFERA1_PADRAO,
  ESFERA2_PADRAO,
  rodarCategorizacaoTransformacao,
  rodarConstrucao,
  rodarEsfera1,
  rodarEsfera2,
  rodarPreSelecao,
  type ConfigEsfera1,
  type ConfigEsfera2,
  type ParConstrucao,
  type ParCorrelacionado,
  type ResultadoCategorizacaoTransformacao,
  type ResultadoConstrucao,
  type ResultadoEsfera1,
  type ResultadoEsfera2,
  type ResultadoPreSelecao,
} from "../lib/api";

interface Props {
  dataset: string;
}

/** Agrupa por "mantida" — o display anterior repetia a mesma sobrevivente
 * numa linha por par descartado (dezenas de linhas quase idênticas quando
 * uma variável de referência, tipo um índice de bin, correlaciona com
 * muitas razões derivadas dela). Uma linha por sobrevivente é bem mais
 * fácil de escanear. */
function agruparPorMantida(
  pares: ParCorrelacionado[],
): { mantida: string; descartadas: { nome: string; correlacao: number }[] }[] {
  const grupos = new Map<string, { nome: string; correlacao: number }[]>();
  for (const p of pares) {
    const lista = grupos.get(p.mantida) ?? [];
    lista.push({ nome: p.descartada, correlacao: p.correlacao });
    grupos.set(p.mantida, lista);
  }
  return [...grupos.entries()].map(([mantida, descartadas]) => ({ mantida, descartadas }));
}

function rotuloPar(p: ParConstrucao): string {
  const simbolo = p.operacao === "razao" ? "/" : "-";
  return p.nome || `${p.numerador} ${simbolo} ${p.denominador}`;
}

const AVISO_MUITAS_COLUNAS = 20;

/** Todas as razões possíveis entre pares de colunas NUMÉRICAS (nunca
 * categóricas/data, senão a divisão quebra) — cada par uma vez só (A/B, não
 * A/B e B/A). Sem limite — o volume de candidatas geradas pode ficar grande
 * (C(n,2) pares × ~7 transformações de potência cada), mas isso é
 * exatamente o que o módulo 3 (Pré-seleção) existe pra filtrar depois, em
 * vez de restringir aqui na origem.
 */
function gerarTodasCombinacoes(colunasNumericas: string[]): ParConstrucao[] {
  const pares: ParConstrucao[] = [];
  for (let i = 0; i < colunasNumericas.length; i++) {
    for (let j = i + 1; j < colunasNumericas.length; j++) {
      pares.push({ numerador: colunasNumericas[i], denominador: colunasNumericas[j], operacao: "razao" });
    }
  }
  return pares;
}

function FormularioParConstrucao({
  colunas,
  aoAdicionar,
}: {
  colunas: string[];
  aoAdicionar: (par: ParConstrucao) => void;
}) {
  const [numerador, setNumerador] = useState("");
  const [denominador, setDenominador] = useState("");
  const [operacao, setOperacao] = useState<ParConstrucao["operacao"]>("razao");
  const [nome, setNome] = useState("");

  function adicionar() {
    if (!numerador || !denominador || numerador === denominador) return;
    aoAdicionar({ numerador, denominador, operacao, nome: nome.trim() || undefined });
    setNome("");
  }

  return (
    <div className="flex flex-wrap items-end gap-2 rounded-lg border border-slate-700 bg-slate-800/60 p-3">
      <div>
        <label className="mb-1 block text-[11px] text-slate-500">numerador / A</label>
        <select
          value={numerador}
          onChange={(e) => setNumerador(e.target.value)}
          className="rounded-md bg-slate-800 border border-slate-600 px-2 py-1 text-xs text-slate-100"
        >
          <option value="">selecione…</option>
          {colunas.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
      </div>
      <span className="pb-1.5 text-xs text-slate-500">{operacao === "razao" ? "/" : "−"}</span>
      <div>
        <label className="mb-1 block text-[11px] text-slate-500">denominador / B</label>
        <select
          value={denominador}
          onChange={(e) => setDenominador(e.target.value)}
          className="rounded-md bg-slate-800 border border-slate-600 px-2 py-1 text-xs text-slate-100"
        >
          <option value="">selecione…</option>
          {colunas.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
      </div>
      <div>
        <label className="mb-1 block text-[11px] text-slate-500">operação</label>
        <select
          value={operacao}
          onChange={(e) => setOperacao(e.target.value as ParConstrucao["operacao"])}
          className="rounded-md bg-slate-800 border border-slate-600 px-2 py-1 text-xs text-slate-100"
        >
          <option value="razao">razão (A / B)</option>
          <option value="diferenca">diferença (A − B)</option>
        </select>
      </div>
      <div className="flex-1 min-w-[8rem]">
        <label className="mb-1 block text-[11px] text-slate-500">nome (opcional)</label>
        <input
          value={nome}
          onChange={(e) => setNome(e.target.value)}
          placeholder="gerado automaticamente"
          className="w-full rounded-md bg-slate-800 border border-slate-600 px-2 py-1 text-xs text-slate-100"
        />
      </div>
      <button
        onClick={adicionar}
        disabled={!numerador || !denominador || numerador === denominador}
        className="rounded-md bg-slate-700 px-3 py-1 text-xs font-medium text-slate-100 transition hover:bg-slate-600 disabled:cursor-not-allowed disabled:opacity-40"
      >
        + Adicionar
      </button>
    </div>
  );
}

/** Campo numérico opcional compacto: desmarcado = filtro desligado (`null`). */
function CampoLimiar({
  rotulo,
  valor,
  aoMudar,
  passo,
  padrao,
}: {
  rotulo: string;
  valor: number | null;
  aoMudar: (v: number | null) => void;
  passo: number;
  padrao: number;
}) {
  const ativo = valor !== null;
  return (
    <div>
      <label className="mb-1 flex items-center gap-1.5 text-[11px] text-slate-500 cursor-pointer">
        <input
          type="checkbox"
          checked={ativo}
          onChange={(e) => aoMudar(e.target.checked ? padrao : null)}
          className="h-3.5 w-3.5 rounded border-slate-600 bg-slate-800 text-emerald-500"
        />
        {rotulo}
      </label>
      <input
        type="number"
        step={passo}
        min={0}
        value={valor ?? ""}
        disabled={!ativo}
        onChange={(e) => aoMudar(Number(e.target.value))}
        className="w-full rounded-md bg-slate-800 border border-slate-600 px-2 py-1 text-xs text-slate-100 disabled:opacity-40"
      />
    </div>
  );
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
    <div className="flex flex-col gap-4 rounded-xl border border-slate-700 bg-slate-900/70 p-5">
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
  const [colunasNumericas, setColunasNumericas] = useState<string[]>([]);
  const [colunasTexto, setColunasTexto] = useState<string[]>([]);
  const [colunasTodas, setColunasTodas] = useState<string[]>([]);
  const [paresCustomizados, setParesCustomizados] = useState<ParConstrucao[]>([]);

  // --- esfera 1 (antes de tudo, agregação temporal) ---
  const [esfera1, setEsfera1] = useState<ConfigEsfera1>({ ...ESFERA1_PADRAO, ativo: true });
  const [rodandoEsfera1, setRodandoEsfera1] = useState(false);
  const [resultadoEsfera1, setResultadoEsfera1] = useState<ResultadoEsfera1 | null>(null);
  const [erroEsfera1, setErroEsfera1] = useState<string | null>(null);

  const [rodandoConstrucao, setRodandoConstrucao] = useState(false);
  const [resultadoConstrucao, setResultadoConstrucao] = useState<ResultadoConstrucao | null>(null);
  const [erroConstrucao, setErroConstrucao] = useState<string | null>(null);

  const [usarConstrucao, setUsarConstrucao] = useState(true);

  // --- esfera 2 (entre Construção e Categorização) ---
  const [esfera2, setEsfera2] = useState<ConfigEsfera2>({ ...ESFERA2_PADRAO, ativo: true });
  const [rodandoEsfera2, setRodandoEsfera2] = useState(false);
  const [resultadoEsfera2, setResultadoEsfera2] = useState<ResultadoEsfera2 | null>(null);
  const [erroEsfera2, setErroEsfera2] = useState<string | null>(null);

  const [gerarTransformacoesPotencia, setGerarTransformacoesPotencia] = useState(true);
  const [gerarBinOrdinal, setGerarBinOrdinal] = useState(true);
  const [rodandoCategorizacao, setRodandoCategorizacao] = useState(false);
  const [resultadoCategorizacao, setResultadoCategorizacao] = useState<ResultadoCategorizacaoTransformacao | null>(
    null,
  );
  const [erroCategorizacao, setErroCategorizacao] = useState<string | null>(null);

  const [limiarVariancia, setLimiarVariancia] = useState<number | null>(1e-6);
  const [limiarIV, setLimiarIV] = useState<number | null>(0.02);
  const [limiarCorrelacao, setLimiarCorrelacao] = useState<number | null>(0.7);
  const [rodandoPreSelecao, setRodandoPreSelecao] = useState(false);
  const [resultadoPreSelecao, setResultadoPreSelecao] = useState<ResultadoPreSelecao | null>(null);
  const [erroPreSelecao, setErroPreSelecao] = useState<string | null>(null);

  useEffect(() => {
    buscarPreviewDataset(dataset)
      .then((p) => {
        setColunasNumericas(p.colunas_numericas);
        setColunasTexto(p.colunas.filter((c) => !p.colunas_numericas.includes(c)));
        setColunasTodas(p.colunas.filter((c) => c !== "y"));
      })
      .catch(() => {
        setColunasNumericas([]);
        setColunasTexto([]);
        setColunasTodas([]);
      });
  }, [dataset]);

  function removerPar(indice: number) {
    setParesCustomizados((atual) => atual.filter((_, i) => i !== indice));
  }

  function aoGerarAutomaticamente() {
    setParesCustomizados(gerarTodasCombinacoes(colunasNumericas));
  }

  async function aoRodarEsfera1() {
    setRodandoEsfera1(true);
    setErroEsfera1(null);
    try {
      setResultadoEsfera1(await rodarEsfera1(dataset, esfera1));
    } catch (e) {
      setErroEsfera1(String(e));
    } finally {
      setRodandoEsfera1(false);
    }
  }

  async function aoRodarConstrucao() {
    setRodandoConstrucao(true);
    setErroConstrucao(null);
    try {
      setResultadoConstrucao(await rodarConstrucao(dataset, paresCustomizados, esfera1));
    } catch (e) {
      setErroConstrucao(String(e));
    } finally {
      setRodandoConstrucao(false);
    }
  }

  async function aoRodarEsfera2() {
    setRodandoEsfera2(true);
    setErroEsfera2(null);
    try {
      setResultadoEsfera2(await rodarEsfera2(dataset, usarConstrucao, paresCustomizados, esfera2, esfera1));
    } catch (e) {
      setErroEsfera2(String(e));
    } finally {
      setRodandoEsfera2(false);
    }
  }

  async function aoRodarCategorizacao() {
    setRodandoCategorizacao(true);
    setErroCategorizacao(null);
    try {
      setResultadoCategorizacao(
        await rodarCategorizacaoTransformacao(
          dataset,
          usarConstrucao,
          paresCustomizados,
          gerarTransformacoesPotencia,
          gerarBinOrdinal,
          esfera2,
          esfera1,
        ),
      );
    } catch (e) {
      setErroCategorizacao(String(e));
    } finally {
      setRodandoCategorizacao(false);
    }
  }

  async function aoRodarPreSelecao() {
    setRodandoPreSelecao(true);
    setErroPreSelecao(null);
    try {
      setResultadoPreSelecao(
        await rodarPreSelecao({
          dataset,
          usar_construcao: usarConstrucao,
          pares_customizados: paresCustomizados,
          gerar_transformacoes_potencia: gerarTransformacoesPotencia,
          gerar_bin_ordinal: gerarBinOrdinal,
          limiar_variancia: limiarVariancia,
          limiar_iv: limiarIV,
          limiar_correlacao: limiarCorrelacao,
          esfera2,
          esfera1,
        }),
      );
    } catch (e) {
      setErroPreSelecao(String(e));
    } finally {
      setRodandoPreSelecao(false);
    }
  }

  const maximoIV = Math.max(0, ...(resultadoCategorizacao?.iv.map((i) => i.iv) ?? []));

  const botao = (rodando: boolean, aoClicar: () => void, rotulo: string) => (
    <button
      onClick={aoClicar}
      disabled={rodando}
      className="shrink-0 rounded-lg bg-slate-800 border border-slate-600 px-3 py-1.5 text-xs font-medium text-slate-200 transition hover:border-emerald-700 hover:text-emerald-400 disabled:opacity-50"
    >
      {rodando ? "Rodando…" : rotulo}
    </button>
  );

  return (
    <div className="flex flex-col gap-4">
      <div className="rounded-lg border border-amber-800/40 bg-amber-950/10 px-3 py-2 text-xs text-amber-200/80">
        Playground de teste — rode aqui pra entender o que cada etapa faz e explorar limiares antes de
        decidir. Nada rodado nesta aba é usado no treinamento: a aba &ldquo;Treinamento&rdquo; sempre
        recomputa tudo do zero com as opções configuradas lá.
      </div>

      <Modulo
        numero={1}
        titulo="Esfera 1 (agregação temporal)"
        descricao='Reduz um dataset com várias linhas por chave a uma linha por chave (máximo/média/mínimo/desvio/tendência por janela) -- roda antes de tudo o resto. Dev e teste são agregados separadamente: preserva o split que você já escolheu no upload.'
        acoes={
          <div className="flex shrink-0 items-center gap-3">
            <label className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer">
              <input
                type="checkbox"
                checked={esfera1.ativo}
                onChange={(e) => setEsfera1((c) => ({ ...c, ativo: e.target.checked }))}
                className="h-3.5 w-3.5 rounded border-slate-600 bg-slate-800 text-emerald-500"
              />
              ativa
            </label>
            {botao(rodandoEsfera1, () => void aoRodarEsfera1(), "Rodar")}
          </div>
        }
      >
        <div className={`grid grid-cols-2 gap-3 sm:grid-cols-4 ${esfera1.ativo ? "" : "opacity-40"}`}>
          <div>
            <label className="mb-1 block text-[11px] text-slate-500">chave</label>
            <select
              value={esfera1.chave}
              disabled={!esfera1.ativo}
              onChange={(e) => setEsfera1((c) => ({ ...c, chave: e.target.value }))}
              className="w-full rounded-md bg-slate-800 border border-slate-600 px-2 py-1 text-xs text-slate-100"
            >
              <option value="">selecione…</option>
              {colunasTodas.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1 block text-[11px] text-slate-500">coluna tempo</label>
            <select
              value={esfera1.coluna_tempo}
              disabled={!esfera1.ativo}
              onChange={(e) => setEsfera1((c) => ({ ...c, coluna_tempo: e.target.value }))}
              className="w-full rounded-md bg-slate-800 border border-slate-600 px-2 py-1 text-xs text-slate-100"
            >
              <option value="">selecione…</option>
              {colunasTodas.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </div>
          <div className="col-span-2">
            <label className="mb-1 block text-[11px] text-slate-500">janelas</label>
            <div className="flex flex-wrap items-center gap-1">
              {[2, 3, 6, 9, 12].map((j) => {
                const marcada = (esfera1.janelas ?? []).includes(j);
                return (
                  <button
                    key={j}
                    disabled={!esfera1.ativo}
                    onClick={() =>
                      setEsfera1((cfg) => {
                        const atual = new Set(cfg.janelas ?? []);
                        if (atual.has(j)) atual.delete(j);
                        else atual.add(j);
                        return { ...cfg, janelas: [...atual].sort((a, b) => a - b) };
                      })
                    }
                    className={`rounded-full border px-2 py-0.5 text-[11px] transition disabled:cursor-not-allowed ${
                      marcada
                        ? "border-emerald-600 bg-emerald-950/40 text-emerald-300"
                        : "border-slate-700 bg-slate-800/60 text-slate-400"
                    }`}
                  >
                    {j}m
                  </button>
                );
              })}
            </div>
          </div>
        </div>
        <div>
          <p className="mb-1.5 text-[11px] text-slate-500">colunas de valor</p>
          <div className={`flex max-h-28 flex-wrap gap-1.5 overflow-y-auto ${esfera1.ativo ? "" : "opacity-40"}`}>
            {colunasTodas
              .filter((c) => c !== esfera1.chave && c !== esfera1.coluna_tempo)
              .map((c) => {
                const marcada = (esfera1.colunas_valor ?? []).includes(c);
                return (
                  <button
                    key={c}
                    disabled={!esfera1.ativo}
                    onClick={() =>
                      setEsfera1((cfg) => {
                        const atual = new Set(cfg.colunas_valor ?? []);
                        if (atual.has(c)) atual.delete(c);
                        else atual.add(c);
                        return { ...cfg, colunas_valor: [...atual] };
                      })
                    }
                    className={`rounded-full border px-2 py-0.5 text-[11px] transition disabled:cursor-not-allowed ${
                      marcada
                        ? "border-sky-700 bg-sky-950/40 text-sky-300"
                        : "border-slate-700 bg-slate-800/60 text-slate-400"
                    }`}
                  >
                    {c}
                  </button>
                );
              })}
          </div>
        </div>
        {erroEsfera1 && <p className="text-xs text-red-400">{erroEsfera1}</p>}
        {!resultadoEsfera1 && !erroEsfera1 && <p className="text-xs text-slate-600">Ainda não rodado.</p>}
        {resultadoEsfera1 && (
          <div className="text-xs text-slate-400">
            <p className="mb-2">
              dev {resultadoEsfera1.n_dev_antes} → {resultadoEsfera1.n_dev_depois} · teste{" "}
              {resultadoEsfera1.n_teste_antes} → {resultadoEsfera1.n_teste_depois} linhas
            </p>
            {resultadoEsfera1.colunas_novas.length > 0 && (
              <div className="flex max-h-40 flex-wrap gap-1.5 overflow-y-auto rounded-lg border border-slate-800 p-2">
                {resultadoEsfera1.colunas_novas.map((c) => (
                  <span
                    key={c}
                    className="h-fit rounded-full border border-sky-800 bg-sky-950/50 px-2 py-0.5 text-[11px] text-sky-300"
                  >
                    {c}
                  </span>
                ))}
              </div>
            )}
          </div>
        )}
      </Modulo>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <Modulo
          numero={2}
          titulo="Construção"
          descricao="Razões/diferenças entre colunas — automáticas (se aplicável ao dataset) ou definidas por você abaixo."
          acoes={botao(rodandoConstrucao, () => void aoRodarConstrucao(), "Rodar")}
        >
          <FormularioParConstrucao
            colunas={colunasNumericas}
            aoAdicionar={(par) => setParesCustomizados((atual) => [...atual, par])}
          />
          <div className="flex items-center gap-2">
            <button
              onClick={aoGerarAutomaticamente}
              disabled={colunasNumericas.length < 2}
              className="rounded-lg border border-slate-600 bg-slate-800 px-3 py-1.5 text-xs font-medium text-slate-200 transition hover:border-emerald-700 hover:text-emerald-400 disabled:cursor-not-allowed disabled:opacity-40"
            >
              Gerar automaticamente (todas as razões entre colunas numéricas)
            </button>
            {colunasNumericas.length > AVISO_MUITAS_COLUNAS && (
              <span className="text-[11px] text-amber-500">
                {colunasNumericas.length} colunas numéricas → até{" "}
                {(colunasNumericas.length * (colunasNumericas.length - 1)) / 2} razões. Use a Pré-seleção
                (módulo 3) depois pra filtrar antes do treinamento.
              </span>
            )}
          </div>
          {paresCustomizados.length > 0 && (
            <div>
              <div className="mb-1.5 flex items-center justify-between">
                <span className="text-[11px] text-slate-500">{paresCustomizados.length} pares selecionados</span>
                <button
                  onClick={() => setParesCustomizados([])}
                  className="text-[11px] text-slate-500 hover:text-red-400"
                >
                  limpar todos
                </button>
              </div>
              <div className="flex max-h-40 flex-wrap gap-1.5 overflow-y-auto rounded-lg border border-slate-800 p-2">
                {paresCustomizados.map((par, i) => (
                  <span
                    key={i}
                    className="flex h-fit items-center gap-1.5 rounded-full border border-slate-600 bg-slate-800 px-2.5 py-1 text-[11px] text-slate-300"
                  >
                    {rotuloPar(par)}
                    <button
                      onClick={() => removerPar(i)}
                      className="text-slate-500 hover:text-red-400"
                      aria-label={`Remover ${rotuloPar(par)}`}
                    >
                      ×
                    </button>
                  </span>
                ))}
              </div>
            </div>
          )}
          {erroConstrucao && <p className="text-xs text-red-400">{erroConstrucao}</p>}
          {!resultadoConstrucao && !erroConstrucao && (
            <p className="text-xs text-slate-600">Ainda não rodado.</p>
          )}
          {resultadoConstrucao &&
            (resultadoConstrucao.colunas_novas.length === 0 ? (
              <p className="text-xs text-slate-500">
                Nenhuma variável construída — nem sugestão automática aplicável a este dataset, nem par
                customizado adicionado acima.
              </p>
            ) : (
              <div className="text-xs text-slate-400">
                <p className="mb-2">
                  {resultadoConstrucao.colunas_novas.length} colunas novas de{" "}
                  {resultadoConstrucao.n_colunas_total} candidatas totais:
                </p>
                <div className="flex max-h-40 flex-wrap gap-1.5 overflow-y-auto rounded-lg border border-slate-800 p-2">
                  {resultadoConstrucao.colunas_novas.map((c) => (
                    <span
                      key={c}
                      className="h-fit rounded-full border border-sky-800 bg-sky-950/50 px-2 py-0.5 text-[11px] text-sky-300"
                    >
                      {c}
                    </span>
                  ))}
                </div>
              </div>
            ))}
        </Modulo>

        <Modulo
          numero={3}
          titulo="Esfera 2 (interação)"
          descricao='Descobre regras de interação ("A > x E B > y") entre Construção e Categorização — treina um ensemble raso, materializa as regras estáveis como coluna 0/1, candidatas junto com o resto.'
          acoes={
            <div className="flex shrink-0 items-center gap-3">
              <label className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer">
                <input
                  type="checkbox"
                  checked={esfera2.ativo}
                  onChange={(e) => setEsfera2((c) => ({ ...c, ativo: e.target.checked }))}
                  className="h-3.5 w-3.5 rounded border-slate-600 bg-slate-800 text-emerald-500"
                />
                ativa
              </label>
              {botao(rodandoEsfera2, () => void aoRodarEsfera2(), "Rodar")}
            </div>
          }
        >
          <div className={`grid grid-cols-2 gap-3 ${esfera2.ativo ? "" : "opacity-40"}`}>
            <div>
              <label className="mb-1 block text-[11px] text-slate-500">nº árvores</label>
              <input
                type="number"
                min={10}
                max={300}
                value={esfera2.n_arvores}
                disabled={!esfera2.ativo}
                onChange={(e) => setEsfera2((c) => ({ ...c, n_arvores: Number(e.target.value) }))}
                className="w-full rounded-md bg-slate-800 border border-slate-600 px-2 py-1 text-xs text-slate-100"
              />
            </div>
            <div>
              <label className="mb-1 block text-[11px] text-slate-500">profundidade máx.</label>
              <input
                type="number"
                min={2}
                max={6}
                value={esfera2.profundidade_maxima}
                disabled={!esfera2.ativo}
                onChange={(e) => setEsfera2((c) => ({ ...c, profundidade_maxima: Number(e.target.value) }))}
                className="w-full rounded-md bg-slate-800 border border-slate-600 px-2 py-1 text-xs text-slate-100"
              />
            </div>
            <div>
              <label className="mb-1 block text-[11px] text-slate-500">máx. regras</label>
              <input
                type="number"
                min={1}
                max={50}
                value={esfera2.max_regras}
                disabled={!esfera2.ativo}
                onChange={(e) => setEsfera2((c) => ({ ...c, max_regras: Number(e.target.value) }))}
                className="w-full rounded-md bg-slate-800 border border-slate-600 px-2 py-1 text-xs text-slate-100"
              />
            </div>
            <div>
              <label className="mb-1 block text-[11px] text-slate-500">IV mín. (estabilidade)</label>
              <input
                type="number"
                min={0}
                step={0.01}
                value={esfera2.iv_minimo}
                disabled={!esfera2.ativo}
                onChange={(e) => setEsfera2((c) => ({ ...c, iv_minimo: Number(e.target.value) }))}
                className="w-full rounded-md bg-slate-800 border border-slate-600 px-2 py-1 text-xs text-slate-100"
              />
            </div>
          </div>

          {(colunasNumericas.length > 0 || colunasTexto.length > 0) && (
            <div>
              <p className="mb-1.5 text-[11px] text-slate-500">
                tratar como categórica (WOE) — texto entra automaticamente
                {colunasTexto.length > 0 && (
                  <span className="text-amber-500"> ({colunasTexto.join(", ")} já é texto)</span>
                )}
              </p>
              <div className="flex max-h-28 flex-wrap gap-1.5 overflow-y-auto">
                {colunasNumericas.map((c) => {
                  const marcada = (esfera2.colunas_categoricas ?? []).includes(c);
                  return (
                    <button
                      key={c}
                      disabled={!esfera2.ativo}
                      onClick={() =>
                        setEsfera2((cfg) => {
                          const atual = new Set(cfg.colunas_categoricas ?? []);
                          if (atual.has(c)) atual.delete(c);
                          else atual.add(c);
                          return { ...cfg, colunas_categoricas: [...atual] };
                        })
                      }
                      className={`rounded-full border px-2 py-0.5 text-[11px] transition disabled:cursor-not-allowed ${
                        marcada
                          ? "border-amber-700 bg-amber-950/40 text-amber-200"
                          : "border-slate-700 bg-slate-800/60 text-slate-400"
                      }`}
                    >
                      {c}
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          <label className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer">
            <input
              type="checkbox"
              checked={esfera2.permitir_cruzamento_entre_bases}
              disabled={!esfera2.ativo}
              onChange={(e) => setEsfera2((c) => ({ ...c, permitir_cruzamento_entre_bases: e.target.checked }))}
              className="h-3.5 w-3.5 rounded border-slate-600 bg-slate-800 text-emerald-500"
            />
            permitir cruzar variáveis diferentes numa mesma regra
          </label>

          {erroEsfera2 && <p className="text-xs text-red-400">{erroEsfera2}</p>}
          {!resultadoEsfera2 && !erroEsfera2 && <p className="text-xs text-slate-600">Ainda não rodado.</p>}
          {resultadoEsfera2 &&
            (resultadoEsfera2.colunas_novas.length === 0 ? (
              <p className="text-xs text-slate-500">
                Nenhuma regra estável encontrada (IV teste abaixo do mínimo, ou nenhuma regra achada).
              </p>
            ) : (
              <div className="text-xs text-slate-400">
                <p className="mb-2">{resultadoEsfera2.n_regras_estaveis} regra(s) estável(is):</p>
                <div className="flex max-h-40 flex-wrap gap-1.5 overflow-y-auto rounded-lg border border-slate-800 p-2">
                  {resultadoEsfera2.colunas_novas.map((c) => (
                    <span
                      key={c}
                      className="h-fit rounded-full border border-violet-800 bg-violet-950/40 px-2 py-0.5 text-[11px] text-violet-300"
                    >
                      {c}
                    </span>
                  ))}
                </div>
              </div>
            ))}
        </Modulo>
      </div>

      <Modulo
        numero={4}
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
          incluir variáveis construídas (etapa 2)
        </label>
        <label className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer">
          <input
            type="checkbox"
            checked={gerarTransformacoesPotencia}
            onChange={(e) => setGerarTransformacoesPotencia(e.target.checked)}
            className="h-3.5 w-3.5 rounded border-slate-600 bg-slate-800 text-emerald-500"
          />
          gerar log/raiz/quadrática/cúbica/inversas por variável numérica
        </label>
        <label className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer">
          <input
            type="checkbox"
            checked={gerarBinOrdinal}
            onChange={(e) => setGerarBinOrdinal(e.target.checked)}
            className="h-3.5 w-3.5 rounded border-slate-600 bg-slate-800 text-emerald-500"
          />
          gerar índice do bin (faixa) como candidata
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

      <Modulo
        numero={5}
        titulo="Pré-seleção"
        descricao="Reduz o volume de candidatas antes do treinamento: variância, IV (por variável-base) e correlação entre bases diferentes."
        acoes={botao(rodandoPreSelecao, () => void aoRodarPreSelecao(), "Rodar")}
      >
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          <CampoLimiar
            rotulo="variância mín."
            valor={limiarVariancia}
            aoMudar={setLimiarVariancia}
            passo={0.000001}
            padrao={1e-6}
          />
          <CampoLimiar rotulo="IV mín." valor={limiarIV} aoMudar={setLimiarIV} passo={0.01} padrao={0.02} />
          <CampoLimiar
            rotulo="correlação máx."
            valor={limiarCorrelacao}
            aoMudar={setLimiarCorrelacao}
            passo={0.05}
            padrao={0.7}
          />
        </div>
        {erroPreSelecao && <p className="text-xs text-red-400">{erroPreSelecao}</p>}
        {!resultadoPreSelecao && !erroPreSelecao && <p className="text-xs text-slate-600">Ainda não rodado.</p>}
        {resultadoPreSelecao && (
          <div className="flex flex-col gap-3">
            <div className="flex flex-wrap items-center gap-2 text-xs text-slate-400">
              <span className="tabular-nums">{resultadoPreSelecao.n_inicial}</span>
              <span>→ variância →</span>
              <span className="tabular-nums">{resultadoPreSelecao.n_apos_variancia}</span>
              <span>→ IV →</span>
              <span className="tabular-nums">{resultadoPreSelecao.n_apos_iv}</span>
              <span>→ correlação →</span>
              <span className="font-semibold text-emerald-400 tabular-nums">{resultadoPreSelecao.n_final}</span>
            </div>
            {resultadoPreSelecao.pares_correlacionados_descartados.length > 0 && (
              <div>
                <p className="mb-1.5 text-[11px] text-slate-500">
                  {resultadoPreSelecao.pares_correlacionados_descartados.length} pares correlacionados —
                  manteve a de maior IV, agrupado por sobrevivente:
                </p>
                <div className="max-h-48 overflow-y-auto rounded-lg border border-slate-800">
                  <table className="w-full text-left text-[11px]">
                    <thead className="sticky top-0 bg-slate-900">
                      <tr className="border-b border-slate-800 text-slate-500">
                        <th className="px-2 py-1.5 font-medium">manteve</th>
                        <th className="px-2 py-1.5 font-medium">descartou</th>
                      </tr>
                    </thead>
                    <tbody>
                      {agruparPorMantida(resultadoPreSelecao.pares_correlacionados_descartados).map((g) => (
                        <tr key={g.mantida} className="border-b border-slate-800/60 last:border-0">
                          <td className="px-2 py-1.5 align-top text-emerald-400">{g.mantida}</td>
                          <td className="px-2 py-1.5 text-slate-400">
                            {g.descartadas.map((d) => (
                              <span key={d.nome} className="mr-2 inline-block">
                                {d.nome}{" "}
                                <span className="text-slate-600">(r={d.correlacao.toFixed(2)})</span>
                              </span>
                            ))}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
            <div className="flex flex-wrap gap-1.5 max-h-40 overflow-y-auto pr-1">
              {resultadoPreSelecao.colunas_mantidas.map((c) => (
                <span
                  key={c}
                  className="rounded-full border border-emerald-800 bg-emerald-950/40 px-2 py-0.5 text-[11px] text-emerald-300"
                >
                  {c}
                </span>
              ))}
            </div>
          </div>
        )}
      </Modulo>

      <p className="text-xs text-slate-600">
        6. Treinamento (Pedro_Wise) — configure na aba &ldquo;Treinamento&rdquo; e rode em &ldquo;Rodar
        seleção&rdquo; na barra lateral. Lá você também pode ativar a pré-seleção pra ela entrar
        automaticamente antes do treinamento, sem precisar rodar aqui primeiro.
      </p>
    </div>
  );
}
