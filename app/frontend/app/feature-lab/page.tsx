"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  buscarInfoPainel,
  buscarPreviewDataset,
  descobrirEmTabela,
  listarBasesFeatureLab,
  rodarAgregacao,
  rodarDireto,
  uploadPainel,
  type BaseFeatureLab,
  type InfoPainel,
  type RegraFeatureLab,
  type ResultadoAgregacao,
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

type CampoOrdenacao = "iv_teste" | "iv_dev" | "suporte_teste" | "n_condicoes" | "n_variaveis";

const CAMPOS_ORDENACAO: { campo: CampoOrdenacao; rotulo: string }[] = [
  { campo: "iv_teste", rotulo: "IV teste" },
  { campo: "iv_dev", rotulo: "IV dev" },
  { campo: "suporte_teste", rotulo: "suporte teste" },
  { campo: "n_condicoes", rotulo: "nº condições" },
  { campo: "n_variaveis", rotulo: "nº variáveis" },
];

export default function FeatureLabPagina() {
  // --- etapa 1: base ---
  const [bases, setBases] = useState<BaseFeatureLab[]>([]);
  const [base, setBase] = useState<BaseFeatureLab | null>(null);

  // --- etapa 2: esfera 1 (só aparece se base.tipo === "painel") ---
  const [info, setInfo] = useState<InfoPainel | null>(null);
  const [chave, setChave] = useState("");
  const [colunaTempo, setColunaTempo] = useState("");
  const [colunasValor, setColunasValor] = useState<Set<string>>(new Set());
  const [janelasTexto, setJanelasTexto] = useState("3");
  const [arquivoUpload, setArquivoUpload] = useState<File | null>(null);
  const [nomeUpload, setNomeUpload] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [rodandoEsfera1, setRodandoEsfera1] = useState(false);
  const [resultadoEsfera1, setResultadoEsfera1] = useState<ResultadoAgregacao | null>(null);

  // --- etapa 3: esfera 2 ---
  const [colunasDisponiveisDireto, setColunasDisponiveisDireto] = useState<string[]>([]);
  const [colunasX, setColunasX] = useState<Set<string>>(new Set());
  const [profundidadeMaxima, setProfundidadeMaxima] = useState(2);
  const [nArvores, setNArvores] = useState(60);
  const [minSuporte, setMinSuporte] = useState(0.02);
  const [maxSuporte, setMaxSuporte] = useState(0.5);
  const [maxRegras, setMaxRegras] = useState(20);
  const [permitirCruzamento, setPermitirCruzamento] = useState(true);
  const [rodandoEsfera2, setRodandoEsfera2] = useState(false);
  const [resultado, setResultado] = useState<ResultadoFeatureLab | null>(null);

  const [erro, setErro] = useState<string | null>(null);

  // --- tabela final: ordenação/filtro ---
  const [ordenarPor, setOrdenarPor] = useState<CampoOrdenacao>("iv_teste");
  const [ordemAsc, setOrdemAsc] = useState(false);
  const [ivMinimo, setIvMinimo] = useState(0);
  const [nVariaveisFiltro, setNVariaveisFiltro] = useState<"todas" | "1" | "2+">("todas");

  useEffect(() => {
    listarBasesFeatureLab()
      .then((lista) => {
        setBases(lista);
        if (lista.length > 0) setBase(lista[0]);
      })
      .catch((e) => setErro(String(e)));
  }, []);

  // Troca de base: reseta tudo que veio de uma base anterior. Ajuste de
  // estado durante o render (padrão documentado pelo React pra "resetar
  // estado quando uma prop muda") em vez de useEffect -- evita a cascata
  // de re-renders de chamar setState direto no corpo de um efeito.
  const [baseAnterior, setBaseAnterior] = useState<BaseFeatureLab | null>(null);
  if (base !== baseAnterior) {
    setBaseAnterior(base);
    setInfo(null);
    setResultadoEsfera1(null);
    setResultado(null);
    setColunasDisponiveisDireto([]);
  }

  useEffect(() => {
    if (!base) return;

    if (base.tipo === "painel") {
      buscarInfoPainel(base.nome)
        .then((i) => {
          setInfo(i);
          setChave(i.chave_sugerida);
          setColunaTempo(i.tempo_sugerido);
          setColunasValor(new Set(i.colunas_valor_disponiveis));
        })
        .catch((e) => setErro(String(e)));
    } else {
      buscarPreviewDataset(base.nome)
        .then((p) => {
          setColunasDisponiveisDireto(p.colunas_numericas);
          setColunasX(new Set(p.colunas_numericas));
        })
        .catch((e) => setErro(String(e)));
    }
  }, [base]);

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
      const infoNova = await uploadPainel(arquivoUpload, nomeUpload.trim());
      const lista = await listarBasesFeatureLab();
      setBases(lista);
      setBase({ nome: infoNova.nome, tipo: "painel" });
      setArquivoUpload(null);
      setNomeUpload("");
    } catch (e) {
      setErro(String(e));
    } finally {
      setEnviando(false);
    }
  }

  async function aoRodarEsfera1() {
    if (!base) return;
    const janelas = janelasTexto
      .split(",")
      .map((s) => Number(s.trim()))
      .filter((n) => Number.isFinite(n) && n > 0);
    if (colunasValor.size === 0) {
      setErro("Selecione ao menos uma coluna de valor.");
      return;
    }
    if (janelas.length === 0) {
      setErro("Informe ao menos uma janela válida (ex.: 3,6).");
      return;
    }

    setRodandoEsfera1(true);
    setErro(null);
    setResultado(null);
    try {
      const r = await rodarAgregacao({
        painel: base.nome,
        chave,
        coluna_tempo: colunaTempo,
        colunas_valor: [...colunasValor],
        janelas,
      });
      setResultadoEsfera1(r);
      setColunasX(new Set(r.colunas_geradas));
    } catch (e) {
      setErro(String(e));
    } finally {
      setRodandoEsfera1(false);
    }
  }

  async function aoRodarEsfera2() {
    if (!base) return;
    if (colunasX.size === 0) {
      setErro("Selecione ao menos uma coluna candidata.");
      return;
    }

    setRodandoEsfera2(true);
    setErro(null);
    setResultado(null);
    const parametros = {
      profundidade_maxima: profundidadeMaxima,
      n_arvores: nArvores,
      min_suporte: minSuporte,
      max_suporte: maxSuporte,
      max_regras: maxRegras,
      permitir_cruzamento_entre_bases: permitirCruzamento,
    };
    try {
      const r =
        base.tipo === "painel" && resultadoEsfera1
          ? await descobrirEmTabela({ tabela: resultadoEsfera1.tabela, colunas_x: [...colunasX], ...parametros })
          : await rodarDireto({ dataset: base.nome, colunas_x: [...colunasX], ...parametros });
      setResultado(r);
    } catch (e) {
      setErro(String(e));
    } finally {
      setRodandoEsfera2(false);
    }
  }

  function alternarOrdenacao(campo: CampoOrdenacao) {
    if (campo === ordenarPor) setOrdemAsc(!ordemAsc);
    else {
      setOrdenarPor(campo);
      setOrdemAsc(false);
    }
  }

  const precisaEsfera1 = base?.tipo === "painel";
  const esfera2Liberada = precisaEsfera1 ? resultadoEsfera1 !== null : colunasDisponiveisDireto.length > 0;
  const colunasParaEsfera2 = precisaEsfera1 ? (resultadoEsfera1?.colunas_geradas ?? []) : colunasDisponiveisDireto;

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
            Base → agregação (esfera 1, se aplicável) → descoberta de interação (esfera 2).
          </p>
        </div>
        <Link href="/" className="text-xs text-slate-500 hover:text-emerald-400">
          ← voltar pro Pedro_Wise
        </Link>
      </header>

      {/* Etapa 1: base ------------------------------------------------- */}
      <Secao titulo="1. Base">
        <div className="flex flex-wrap items-end gap-4">
          <div>
            <label className="mb-1 block text-[11px] text-slate-500">dataset</label>
            <select
              value={base ? `${base.tipo}:${base.nome}` : ""}
              onChange={(e) => {
                const [tipo, nome] = e.target.value.split(":");
                setBase({ tipo: tipo as BaseFeatureLab["tipo"], nome });
              }}
              className="rounded-lg bg-slate-800 border border-slate-600 px-2 py-1.5 text-sm text-slate-100"
            >
              {bases.map((b) => (
                <option key={`${b.tipo}:${b.nome}`} value={`${b.tipo}:${b.nome}`}>
                  {b.nome} ({b.tipo === "painel" ? "painel" : "flat"})
                </option>
              ))}
            </select>
          </div>
          {info && (
            <p className="text-xs text-slate-500">
              {info.n_linhas.toLocaleString("pt-BR")} linhas, {info.n_chaves.toLocaleString("pt-BR")} chaves —
              tem granularidade de painel, a esfera 1 abaixo é aplicável.
            </p>
          )}
          {base?.tipo === "flat" && (
            <p className="text-xs text-slate-500">
              Base já flat — sem granularidade de painel, pula direto pra esfera 2.
            </p>
          )}
        </div>

        <div className="mt-4 flex flex-wrap items-end gap-2 border-t border-slate-800 pt-4">
          <div>
            <label className="mb-1 block text-[11px] text-slate-500">enviar novo painel (CSV)</label>
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

      {/* Etapa 2: esfera 1 (só se painel) --------------------------------- */}
      {precisaEsfera1 && info && (
        <Secao titulo="2. Esfera 1 — agregação temporal">
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
          <button
            onClick={aoRodarEsfera1}
            disabled={rodandoEsfera1}
            className="mt-4 rounded-lg bg-slate-700 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-600 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {rodandoEsfera1 ? "Rodando…" : "Rodar esfera 1"}
          </button>

          {resultadoEsfera1 && (
            <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4 border-t border-slate-800 pt-4">
              <Metrica rotulo="linhas do painel" valor={resultadoEsfera1.n_linhas_painel.toLocaleString("pt-BR")} />
              <Metrica rotulo="chaves" valor={resultadoEsfera1.n_chaves.toLocaleString("pt-BR")} />
              <Metrica rotulo="colunas geradas" valor={String(resultadoEsfera1.colunas_geradas.length)} />
              <Metrica rotulo="linhas resultantes" valor={resultadoEsfera1.tabela.length.toLocaleString("pt-BR")} />
            </div>
          )}
        </Secao>
      )}

      {/* Etapa 3: esfera 2 -------------------------------------------------- */}
      {esfera2Liberada && (
        <Secao titulo={`${precisaEsfera1 ? "3" : "2"}. Esfera 2 — descoberta de interação`}>
          <div className="mb-4">
            <p className="mb-1.5 text-[11px] text-slate-500">colunas candidatas</p>
            <div className="flex max-h-40 flex-wrap gap-2 overflow-y-auto">
              {colunasParaEsfera2.map((c) => (
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

          <button
            onClick={aoRodarEsfera2}
            disabled={rodandoEsfera2}
            className="mt-4 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {rodandoEsfera2 ? "Rodando…" : "Rodar esfera 2"}
          </button>
        </Secao>
      )}

      {erro && <p className="text-sm text-red-400">{erro}</p>}

      {/* Resultado -------------------------------------------------------- */}
      {resultado && (
        <Secao titulo="Resultado">
          <div className="mb-4 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
            <Metrica rotulo="colunas candidatas" valor={String(resultado.colunas_x.length)} />
            <Metrica rotulo="dev / teste" valor={`${resultado.n_dev} / ${resultado.n_teste}`} />
            <Metrica rotulo="taxa evento dev" valor={`${(resultado.taxa_evento_dev * 100).toFixed(1)}%`} />
            <Metrica rotulo="taxa evento teste" valor={`${(resultado.taxa_evento_teste * 100).toFixed(1)}%`} />
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
