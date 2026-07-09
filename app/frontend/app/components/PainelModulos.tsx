"use client";

import { useEffect, useState } from "react";
import {
  buscarPreviewDataset,
  rodarCategorizacaoTransformacao,
  rodarConstrucao,
  type ParConstrucao,
  type ResultadoCategorizacaoTransformacao,
  type ResultadoConstrucao,
} from "../lib/api";

interface Props {
  dataset: string;
}

function rotuloPar(p: ParConstrucao): string {
  const simbolo = p.operacao === "razao" ? "/" : "-";
  return p.nome || `${p.numerador} ${simbolo} ${p.denominador}`;
}

const MAXIMO_COLUNAS_PARA_AUTO_GERAR = 12;

/** Todas as razões possíveis entre pares de colunas NUMÉRICAS (nunca
 * categóricas/data, senão a divisão quebra) — cada par uma vez só (A/B, não
 * A/B e B/A). Capado em `MAXIMO_COLUNAS_PARA_AUTO_GERAR` colunas pra não
 * explodir o número de candidatas que o Pedro_Wise depois precisa avaliar.
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
  const [paresCustomizados, setParesCustomizados] = useState<ParConstrucao[]>([]);

  const [rodandoConstrucao, setRodandoConstrucao] = useState(false);
  const [resultadoConstrucao, setResultadoConstrucao] = useState<ResultadoConstrucao | null>(null);
  const [erroConstrucao, setErroConstrucao] = useState<string | null>(null);

  const [usarConstrucao, setUsarConstrucao] = useState(true);
  const [gerarTransformacoesPotencia, setGerarTransformacoesPotencia] = useState(true);
  const [rodandoCategorizacao, setRodandoCategorizacao] = useState(false);
  const [resultadoCategorizacao, setResultadoCategorizacao] = useState<ResultadoCategorizacaoTransformacao | null>(
    null,
  );
  const [erroCategorizacao, setErroCategorizacao] = useState<string | null>(null);

  useEffect(() => {
    buscarPreviewDataset(dataset)
      .then((p) => setColunasNumericas(p.colunas_numericas))
      .catch(() => setColunasNumericas([]));
  }, [dataset]);

  function removerPar(indice: number) {
    setParesCustomizados((atual) => atual.filter((_, i) => i !== indice));
  }

  function aoGerarAutomaticamente() {
    setParesCustomizados(gerarTodasCombinacoes(colunasNumericas));
  }

  async function aoRodarConstrucao() {
    setRodandoConstrucao(true);
    setErroConstrucao(null);
    try {
      setResultadoConstrucao(await rodarConstrucao(dataset, paresCustomizados));
    } catch (e) {
      setErroConstrucao(String(e));
    } finally {
      setRodandoConstrucao(false);
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
        ),
      );
    } catch (e) {
      setErroCategorizacao(String(e));
    } finally {
      setRodandoCategorizacao(false);
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
      <p className="text-sm text-slate-500">Rode e inspecione cada etapa isoladamente antes do treinamento.</p>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <Modulo
          numero={1}
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
              disabled={colunasNumericas.length < 2 || colunasNumericas.length > MAXIMO_COLUNAS_PARA_AUTO_GERAR}
              className="rounded-lg border border-slate-600 bg-slate-800 px-3 py-1.5 text-xs font-medium text-slate-200 transition hover:border-emerald-700 hover:text-emerald-400 disabled:cursor-not-allowed disabled:opacity-40"
            >
              Gerar automaticamente (todas as razões entre colunas numéricas)
            </button>
            {colunasNumericas.length > MAXIMO_COLUNAS_PARA_AUTO_GERAR && (
              <span className="text-[11px] text-slate-600">
                {colunasNumericas.length} colunas numéricas — acima do limite de{" "}
                {MAXIMO_COLUNAS_PARA_AUTO_GERAR} pra gerar tudo de uma vez, monte manualmente acima.
              </span>
            )}
          </div>
          {paresCustomizados.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {paresCustomizados.map((par, i) => (
                <span
                  key={i}
                  className="flex items-center gap-1.5 rounded-full border border-slate-600 bg-slate-800 px-2.5 py-1 text-[11px] text-slate-300"
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
                <div className="flex flex-wrap gap-1.5">
                  {resultadoConstrucao.colunas_novas.map((c) => (
                    <span
                      key={c}
                      className="rounded-full border border-sky-800 bg-sky-950/50 px-2 py-0.5 text-[11px] text-sky-300"
                    >
                      {c}
                    </span>
                  ))}
                </div>
              </div>
            ))}
        </Modulo>

        <Modulo
          numero={2}
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
            incluir variáveis construídas (etapa 1)
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
      </div>

      <p className="text-xs text-slate-600">
        3. Treinamento (Pedro_Wise) — configure na aba &ldquo;Treinamento&rdquo; e rode em &ldquo;Rodar
        seleção&rdquo; na barra lateral.
      </p>
    </div>
  );
}
