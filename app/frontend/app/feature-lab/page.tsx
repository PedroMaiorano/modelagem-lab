"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  buscarDatasets,
  buscarInfoPainel,
  buscarPreviewDataset,
  listarPaineis,
  rodarAgregacao,
  rodarDireto,
  uploadPainel,
  type InfoPainel,
  type RegraFeatureLab,
  type ResultadoFeatureLab,
} from "../lib/api";

function Secao({ titulo, children }: { titulo: string; children: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-slate-700 bg-slate-900/70 p-5">
      <h2 className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-400">{titulo}</h2>
      {children}
    </div>
  );
}

function Metrica({ rotulo, valor }: { rotulo: string; valor: string }) {
  return (
    <div className="rounded-lg border border-slate-700 bg-slate-800/60 px-3 py-2">
      <div className="text-[10px] uppercase tracking-wider text-slate-500">{rotulo}</div>
      <div className="mt-0.5 text-lg font-semibold text-slate-100 tabular-nums">{valor}</div>
    </div>
  );
}

type Modo = "agregacao" | "direto";
type CampoOrdenacao = "iv_teste" | "iv_dev" | "suporte_teste" | "n_condicoes" | "n_variaveis";

const CAMPOS_ORDENACAO: { campo: CampoOrdenacao; rotulo: string }[] = [
  { campo: "iv_teste", rotulo: "IV teste" },
  { campo: "iv_dev", rotulo: "IV dev" },
  { campo: "suporte_teste", rotulo: "suporte teste" },
  { campo: "n_condicoes", rotulo: "nº condições" },
  { campo: "n_variaveis", rotulo: "nº variáveis" },
];

export default function FeatureLabPagina() {
  const [modo, setModo] = useState<Modo>("agregacao");

  // --- modo agregação ---
  const [paineis, setPaineis] = useState<string[]>([]);
  const [painel, setPainel] = useState("");
  const [info, setInfo] = useState<InfoPainel | null>(null);
  const [chave, setChave] = useState("");
  const [colunaTempo, setColunaTempo] = useState("");
  const [colunasValor, setColunasValor] = useState<Set<string>>(new Set());
  const [janelasTexto, setJanelasTexto] = useState("3");
  const [arquivoUpload, setArquivoUpload] = useState<File | null>(null);
  const [nomeUpload, setNomeUpload] = useState("");
  const [enviando, setEnviando] = useState(false);

  // --- modo direto ---
  const [datasets, setDatasets] = useState<string[]>([]);
  const [dataset, setDataset] = useState("");
  const [colunasDisponiveis, setColunasDisponiveis] = useState<string[]>([]);
  const [colunasX, setColunasX] = useState<Set<string>>(new Set());

  // --- esfera 2 (comum aos dois modos) ---
  const [profundidadeMaxima, setProfundidadeMaxima] = useState(2);
  const [nArvores, setNArvores] = useState(60);
  const [minSuporte, setMinSuporte] = useState(0.02);
  const [maxSuporte, setMaxSuporte] = useState(0.5);
  const [maxRegras, setMaxRegras] = useState(20);
  const [permitirCruzamento, setPermitirCruzamento] = useState(true);

  const [rodando, setRodando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [resultado, setResultado] = useState<ResultadoFeatureLab | null>(null);

  // --- tabela: ordenação/filtro ---
  const [ordenarPor, setOrdenarPor] = useState<CampoOrdenacao>("iv_teste");
  const [ordemAsc, setOrdemAsc] = useState(false);
  const [ivMinimo, setIvMinimo] = useState(0);
  const [nVariaveisFiltro, setNVariaveisFiltro] = useState<"todas" | "1" | "2+">("todas");

  useEffect(() => {
    listarPaineis()
      .then((lista) => {
        setPaineis(lista);
        if (lista.length > 0) setPainel(lista[0]);
      })
      .catch((e) => setErro(String(e)));
    buscarDatasets()
      .then((lista) => {
        setDatasets(lista);
        if (lista.length > 0) setDataset(lista[0]);
      })
      .catch((e) => setErro(String(e)));
  }, []);

  useEffect(() => {
    if (!painel || modo !== "agregacao") return;
    buscarInfoPainel(painel)
      .then((i) => {
        setInfo(i);
        setChave(i.chave_sugerida);
        setColunaTempo(i.tempo_sugerido);
        setColunasValor(new Set(i.colunas_valor_disponiveis));
        setResultado(null);
      })
      .catch((e) => setErro(String(e)));
  }, [painel, modo]);

  useEffect(() => {
    if (!dataset || modo !== "direto") return;
    buscarPreviewDataset(dataset)
      .then((p) => {
        setColunasDisponiveis(p.colunas_numericas);
        setColunasX(new Set(p.colunas_numericas));
        setResultado(null);
      })
      .catch((e) => setErro(String(e)));
  }, [dataset, modo]);

  function alternar(conjunto: Set<string>, item: string, aoMudar: (s: Set<string>) => void) {
    const novo = new Set(conjunto);
    if (novo.has(item)) novo.delete(item);
    else novo.add(item);
    aoMudar(novo);
  }

  async function aoEnviarPainel() {
    if (!arquivoUpload || !nomeUpload.trim()) return;
    setEnviando(true);
    setErro(null);
    try {
      const info = await uploadPainel(arquivoUpload, nomeUpload.trim());
      const lista = await listarPaineis();
      setPaineis(lista);
      setPainel(info.nome);
      setArquivoUpload(null);
      setNomeUpload("");
    } catch (e) {
      setErro(String(e));
    } finally {
      setEnviando(false);
    }
  }

  async function aoRodar() {
    setRodando(true);
    setErro(null);
    setResultado(null);
    try {
      if (modo === "agregacao") {
        const janelas = janelasTexto
          .split(",")
          .map((s) => Number(s.trim()))
          .filter((n) => Number.isFinite(n) && n > 0);
        if (colunasValor.size === 0) throw new Error("Selecione ao menos uma coluna de valor.");
        if (janelas.length === 0) throw new Error("Informe ao menos uma janela válida (ex.: 3,6).");

        const r = await rodarAgregacao({
          painel,
          chave,
          coluna_tempo: colunaTempo,
          colunas_valor: [...colunasValor],
          janelas,
          profundidade_maxima: profundidadeMaxima,
          n_arvores: nArvores,
          min_suporte: minSuporte,
          max_suporte: maxSuporte,
          max_regras: maxRegras,
          permitir_cruzamento_entre_bases: permitirCruzamento,
        });
        setResultado(r);
      } else {
        if (colunasX.size === 0) throw new Error("Selecione ao menos uma coluna candidata.");
        const r = await rodarDireto({
          dataset,
          colunas_x: [...colunasX],
          profundidade_maxima: profundidadeMaxima,
          n_arvores: nArvores,
          min_suporte: minSuporte,
          max_suporte: maxSuporte,
          max_regras: maxRegras,
          permitir_cruzamento_entre_bases: permitirCruzamento,
        });
        setResultado(r);
      }
    } catch (e) {
      setErro(String(e));
    } finally {
      setRodando(false);
    }
  }

  function alternarOrdenacao(campo: CampoOrdenacao) {
    if (campo === ordenarPor) setOrdemAsc(!ordemAsc);
    else {
      setOrdenarPor(campo);
      setOrdemAsc(false);
    }
  }

  const regrasFiltradas: RegraFeatureLab[] = (resultado?.regras ?? [])
    .filter((r) => r.iv_teste >= ivMinimo)
    .filter((r) => {
      if (nVariaveisFiltro === "todas") return true;
      if (nVariaveisFiltro === "1") return r.n_variaveis === 1;
      return r.n_variaveis >= 2;
    })
    .sort((a, b) => (ordemAsc ? 1 : -1) * (a[ordenarPor] - b[ordenarPor]));

  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-6 p-6">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-slate-100">Feature-lab</h1>
          <p className="text-sm text-slate-500">
            Construção e descoberta de features — experimental, desacoplado do Pedro_Wise por enquanto.
          </p>
        </div>
        <Link href="/" className="text-xs text-slate-500 hover:text-emerald-400">
          ← voltar pro Pedro_Wise
        </Link>
      </header>

      <div className="flex gap-1 rounded-lg bg-slate-900/70 p-1 w-fit">
        {(["agregacao", "direto"] as Modo[]).map((m) => (
          <button
            key={m}
            onClick={() => {
              setModo(m);
              setResultado(null);
            }}
            className={`rounded-md px-4 py-1.5 text-sm font-medium transition ${
              modo === m ? "bg-slate-700 text-white shadow-sm" : "text-slate-400 hover:text-slate-200"
            }`}
          >
            {m === "agregacao" ? "Com agregação (painel)" : "Direto (dataset existente)"}
          </button>
        ))}
      </div>
      <p className="-mt-3 text-xs text-slate-500">
        {modo === "agregacao"
          ? "Painel mensal (chave + tempo + valores) — passa pela esfera 1 antes da descoberta de interação."
          : "Base já flat (uma linha por observação, sem granularidade de painel) — pula direto pra descoberta de interação."}
      </p>

      {modo === "agregacao" ? (
        <>
          <Secao titulo="Painel">
            <div className="flex flex-wrap items-end gap-4">
              <div>
                <label className="mb-1 block text-[11px] text-slate-500">dataset de painel</label>
                <select
                  value={painel}
                  onChange={(e) => setPainel(e.target.value)}
                  className="rounded-lg bg-slate-800 border border-slate-600 px-2 py-1.5 text-sm text-slate-100"
                >
                  {paineis.map((p) => (
                    <option key={p} value={p}>
                      {p}
                    </option>
                  ))}
                </select>
              </div>
              {info && (
                <>
                  <div>
                    <label className="mb-1 block text-[11px] text-slate-500">chave</label>
                    <select
                      value={chave}
                      onChange={(e) => setChave(e.target.value)}
                      className="rounded-lg bg-slate-800 border border-slate-600 px-2 py-1.5 text-sm text-slate-100"
                    >
                      {info.colunas.map((c) => (
                        <option key={c} value={c}>
                          {c}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="mb-1 block text-[11px] text-slate-500">coluna de tempo/safra</label>
                    <select
                      value={colunaTempo}
                      onChange={(e) => setColunaTempo(e.target.value)}
                      className="rounded-lg bg-slate-800 border border-slate-600 px-2 py-1.5 text-sm text-slate-100"
                    >
                      {info.colunas.map((c) => (
                        <option key={c} value={c}>
                          {c}
                        </option>
                      ))}
                    </select>
                  </div>
                  <p className="text-xs text-slate-500">
                    {info.n_linhas.toLocaleString("pt-BR")} linhas, {info.n_chaves.toLocaleString("pt-BR")} chaves
                  </p>
                </>
              )}
            </div>

            <div className="mt-4 flex flex-wrap items-end gap-2 border-t border-slate-800 pt-4">
              <div>
                <label className="mb-1 block text-[11px] text-slate-500">novo painel (CSV)</label>
                <input
                  type="file"
                  accept=".csv"
                  onChange={(e) => setArquivoUpload(e.target.files?.[0] ?? null)}
                  className="block text-xs text-slate-400 file:mr-2 file:rounded file:border-0 file:bg-slate-700 file:px-2 file:py-1 file:text-xs file:text-slate-200"
                />
              </div>
              <div>
                <label className="mb-1 block text-[11px] text-slate-500">nome</label>
                <input
                  type="text"
                  value={nomeUpload}
                  onChange={(e) => setNomeUpload(e.target.value)}
                  placeholder="meu-painel"
                  className="w-36 rounded-lg bg-slate-800 border border-slate-600 px-2 py-1.5 text-sm text-slate-100"
                />
              </div>
              <button
                onClick={aoEnviarPainel}
                disabled={enviando || !arquivoUpload || !nomeUpload.trim()}
                className="rounded-lg border border-slate-600 bg-slate-800 px-3 py-1.5 text-xs font-medium text-slate-200 transition hover:border-emerald-700 hover:text-emerald-400 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {enviando ? "Enviando…" : "Enviar painel"}
              </button>
            </div>
          </Secao>

          {info && (
            <Secao titulo="Esfera 1 — agregação temporal">
              <div className="flex flex-col gap-3">
                <div>
                  <p className="mb-1.5 text-[11px] text-slate-500">
                    colunas brutas a agregar (máximo/média/mínimo/desvio/tendência por janela)
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {info.colunas_valor_disponiveis.map((c) => (
                      <label
                        key={c}
                        className="flex cursor-pointer items-center gap-1.5 rounded-full border border-slate-700 bg-slate-800/60 px-2.5 py-1 text-xs text-slate-300"
                      >
                        <input
                          type="checkbox"
                          checked={colunasValor.has(c)}
                          onChange={() => alternar(colunasValor, c, setColunasValor)}
                          className="h-3.5 w-3.5 rounded border-slate-600 bg-slate-800 text-emerald-500 focus:ring-emerald-500"
                        />
                        {c}
                      </label>
                    ))}
                  </div>
                </div>
                <div>
                  <label className="mb-1 block text-[11px] text-slate-500">
                    janelas (períodos, separadas por vírgula)
                  </label>
                  <input
                    type="text"
                    value={janelasTexto}
                    onChange={(e) => setJanelasTexto(e.target.value)}
                    placeholder="3,6,12"
                    className="w-32 rounded-lg bg-slate-800 border border-slate-600 px-2 py-1.5 text-sm text-slate-100"
                  />
                </div>
              </div>
            </Secao>
          )}
        </>
      ) : (
        <Secao titulo="Dataset">
          <div className="flex flex-wrap items-end gap-4">
            <div>
              <label className="mb-1 block text-[11px] text-slate-500">dataset</label>
              <select
                value={dataset}
                onChange={(e) => setDataset(e.target.value)}
                className="rounded-lg bg-slate-800 border border-slate-600 px-2 py-1.5 text-sm text-slate-100"
              >
                {datasets.map((d) => (
                  <option key={d} value={d}>
                    {d}
                  </option>
                ))}
              </select>
            </div>
          </div>
          {colunasDisponiveis.length > 0 && (
            <div className="mt-4">
              <p className="mb-1.5 text-[11px] text-slate-500">colunas candidatas (esfera 2)</p>
              <div className="flex max-h-40 flex-wrap gap-2 overflow-y-auto">
                {colunasDisponiveis.map((c) => (
                  <label
                    key={c}
                    className="flex cursor-pointer items-center gap-1.5 rounded-full border border-slate-700 bg-slate-800/60 px-2.5 py-1 text-xs text-slate-300"
                  >
                    <input
                      type="checkbox"
                      checked={colunasX.has(c)}
                      onChange={() => alternar(colunasX, c, setColunasX)}
                      className="h-3.5 w-3.5 rounded border-slate-600 bg-slate-800 text-emerald-500 focus:ring-emerald-500"
                    />
                    {c}
                  </label>
                ))}
              </div>
            </div>
          )}
        </Secao>
      )}

      <Secao titulo="Esfera 2 — descoberta de interação">
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
          <div>
            <label className="mb-1 block text-[11px] text-slate-500">profundidade máxima</label>
            <input
              type="number"
              min={2}
              max={6}
              value={profundidadeMaxima}
              onChange={(e) => setProfundidadeMaxima(Number(e.target.value))}
              className="w-full rounded-lg bg-slate-800 border border-slate-600 px-2 py-1.5 text-sm text-slate-100"
            />
          </div>
          <div>
            <label className="mb-1 block text-[11px] text-slate-500">nº árvores</label>
            <input
              type="number"
              min={10}
              max={300}
              value={nArvores}
              onChange={(e) => setNArvores(Number(e.target.value))}
              className="w-full rounded-lg bg-slate-800 border border-slate-600 px-2 py-1.5 text-sm text-slate-100"
            />
          </div>
          <div>
            <label className="mb-1 block text-[11px] text-slate-500">suporte mínimo</label>
            <input
              type="number"
              step={0.01}
              min={0}
              max={1}
              value={minSuporte}
              onChange={(e) => setMinSuporte(Number(e.target.value))}
              className="w-full rounded-lg bg-slate-800 border border-slate-600 px-2 py-1.5 text-sm text-slate-100"
            />
          </div>
          <div>
            <label className="mb-1 block text-[11px] text-slate-500">suporte máximo</label>
            <input
              type="number"
              step={0.01}
              min={0}
              max={1}
              value={maxSuporte}
              onChange={(e) => setMaxSuporte(Number(e.target.value))}
              className="w-full rounded-lg bg-slate-800 border border-slate-600 px-2 py-1.5 text-sm text-slate-100"
            />
          </div>
          <div>
            <label className="mb-1 block text-[11px] text-slate-500">máx. regras exibidas</label>
            <input
              type="number"
              min={1}
              max={100}
              value={maxRegras}
              onChange={(e) => setMaxRegras(Number(e.target.value))}
              className="w-full rounded-lg bg-slate-800 border border-slate-600 px-2 py-1.5 text-sm text-slate-100"
            />
          </div>
        </div>
        <label className="mt-4 flex items-center gap-2 text-sm text-slate-200 cursor-pointer">
          <input
            type="checkbox"
            checked={permitirCruzamento}
            onChange={(e) => setPermitirCruzamento(e.target.checked)}
            className="h-4 w-4 rounded border-slate-600 bg-slate-800 text-emerald-500 focus:ring-emerald-500"
          />
          Permitir cruzar variáveis brutas diferentes numa mesma regra
        </label>
        <p className="mt-1 text-xs text-slate-500">
          Desmarcado: cada regra só combina primitivas da mesma variável bruta — útil se regra de
          negócio não quer misturar domínios diferentes numa condição só.
        </p>
      </Secao>

      <div className="flex items-center gap-3">
        <button
          onClick={aoRodar}
          disabled={rodando || (modo === "agregacao" ? !painel : !dataset)}
          className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {rodando ? "Rodando…" : "Rodar"}
        </button>
        {erro && <p className="text-sm text-red-400">{erro}</p>}
      </div>

      {resultado && (
        <Secao titulo="Resultado">
          <div className="mb-4 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
            {resultado.n_linhas_painel !== undefined && (
              <Metrica rotulo="linhas do painel" valor={resultado.n_linhas_painel.toLocaleString("pt-BR")} />
            )}
            {resultado.n_chaves !== undefined && (
              <Metrica rotulo="chaves" valor={resultado.n_chaves.toLocaleString("pt-BR")} />
            )}
            <Metrica rotulo="colunas candidatas" valor={String(resultado.colunas_x.length)} />
            <Metrica rotulo="dev / teste" valor={`${resultado.n_dev} / ${resultado.n_teste}`} />
            <Metrica rotulo="taxa evento dev" valor={`${(resultado.taxa_evento_dev * 100).toFixed(1)}%`} />
            <Metrica rotulo="tempo de execução" valor={`${resultado.tempo_execucao_segundos.toFixed(2)}s`} />
          </div>

          {resultado.regras.length === 0 ? (
            <p className="text-sm text-slate-500">
              Nenhuma regra sobreviveu aos filtros de suporte — tente ajustar suporte mínimo/máximo
              ou profundidade.
            </p>
          ) : (
            <>
              <div className="mb-3 flex flex-wrap items-end gap-4">
                <div>
                  <label className="mb-1 block text-[11px] text-slate-500">IV mínimo (teste)</label>
                  <input
                    type="number"
                    step={0.01}
                    min={0}
                    value={ivMinimo}
                    onChange={(e) => setIvMinimo(Number(e.target.value))}
                    className="w-24 rounded-lg bg-slate-800 border border-slate-600 px-2 py-1 text-sm text-slate-100"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-[11px] text-slate-500">nº variáveis</label>
                  <select
                    value={nVariaveisFiltro}
                    onChange={(e) => setNVariaveisFiltro(e.target.value as "todas" | "1" | "2+")}
                    className="rounded-lg bg-slate-800 border border-slate-600 px-2 py-1 text-sm text-slate-100"
                  >
                    <option value="todas">todas</option>
                    <option value="1">só 1 (mesma base)</option>
                    <option value="2+">2+ (cruzadas)</option>
                  </select>
                </div>
                <p className="text-xs text-slate-500">
                  {regrasFiltradas.length} de {resultado.regras.length} regras — clique nos cabeçalhos pra ordenar
                </p>
              </div>

              <div className="max-h-96 overflow-y-auto rounded-lg border border-slate-700">
                <table className="w-full text-xs">
                  <thead className="sticky top-0 bg-slate-800/90 text-slate-400">
                    <tr>
                      <th className="px-3 py-2 text-left font-medium">regra</th>
                      {CAMPOS_ORDENACAO.map(({ campo, rotulo }) => (
                        <th
                          key={campo}
                          onClick={() => alternarOrdenacao(campo)}
                          className="cursor-pointer select-none px-3 py-2 text-right font-medium hover:text-slate-200"
                        >
                          {rotulo}
                          {ordenarPor === campo && (ordemAsc ? " ↑" : " ↓")}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {regrasFiltradas.map((r, i) => (
                      <tr key={i} className={i % 2 === 0 ? "bg-slate-900/40" : "bg-slate-900/70"}>
                        <td className="px-3 py-1.5 font-mono text-slate-300">{r.regra}</td>
                        <td className="px-3 py-1.5 text-right tabular-nums text-emerald-400">
                          {r.iv_teste.toFixed(3)}
                        </td>
                        <td className="px-3 py-1.5 text-right tabular-nums text-slate-400">{r.iv_dev.toFixed(3)}</td>
                        <td className="px-3 py-1.5 text-right tabular-nums text-slate-400">
                          {r.suporte_teste.toFixed(3)}
                        </td>
                        <td className="px-3 py-1.5 text-right tabular-nums text-slate-400">{r.n_condicoes}</td>
                        <td className="px-3 py-1.5 text-right tabular-nums text-slate-400">{r.n_variaveis}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </Secao>
      )}
    </div>
  );
}
