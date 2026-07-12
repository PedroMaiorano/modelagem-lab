"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import SidebarFeatureLab from "../components/SidebarFeatureLab";
import {
  buscarInfoPainel,
  buscarPreviewDataset,
  carregarBaseBruta,
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

const ABAS = [
  { id: "esfera1", rotulo: "Esfera 1" },
  { id: "esfera2", rotulo: "Esfera 2" },
] as const;

type Aba = (typeof ABAS)[number]["id"];

//: heurística só pra sugerir default no seletor — usuário sempre pode trocar.
const CANDIDATOS_TEMPO = new Set(["safra", "data", "mes", "tempo", "competencia", "anomes", "day"]);

//: janelas mais comuns em painel mensal — atalho, não limita: dá pra
//: adicionar qualquer valor pelo campo "outra" ao lado.
const JANELAS_COMUNS = [2, 3, 6, 9, 12];

export default function FeatureLabPagina() {
  const [aba, setAba] = useState<Aba>("esfera1");

  const [bases, setBases] = useState<BaseFeatureLab[]>([]);
  const [base, setBase] = useState<BaseFeatureLab | null>(null);
  const [colunaY, setColunaY] = useState("y");
  const [colunasBase, setColunasBase] = useState<string[]>([]);
  const [colunasNumericasBase, setColunasNumericasBase] = useState<string[]>([]);
  const [info, setInfo] = useState<InfoPainel | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  // --- esfera 1 ---
  const [chave, setChave] = useState("");
  const [colunaTempo, setColunaTempo] = useState("");
  const [colunasValor, setColunasValor] = useState<Set<string>>(new Set());
  const [janelas, setJanelas] = useState<Set<number>>(new Set([3]));
  const [janelaCustom, setJanelaCustom] = useState("");
  const [rodandoEsfera1, setRodandoEsfera1] = useState(false);
  const [resultadoEsfera1, setResultadoEsfera1] = useState<ResultadoAgregacao | null>(null);

  // --- esfera 2 ---
  const [fonteEsfera2, setFonteEsfera2] = useState<"esfera1" | "bruta">("bruta");
  const [colunasX, setColunasX] = useState<Set<string>>(new Set());
  const [profundidadeMaxima, setProfundidadeMaxima] = useState(2);
  const [nArvores, setNArvores] = useState(60);
  const [minSuporte, setMinSuporte] = useState(0.02);
  const [maxSuporte, setMaxSuporte] = useState(0.5);
  const [maxRegras, setMaxRegras] = useState(20);
  const [permitirCruzamento, setPermitirCruzamento] = useState(true);
  const [proporcaoVariaveis, setProporcaoVariaveis] = useState<string>("");
  const [metodoSplit, setMetodoSplit] = useState<"aleatorio" | "coluna">("aleatorio");
  const [colunaSplit, setColunaSplit] = useState("");
  const [valoresDevTexto, setValoresDevTexto] = useState("");
  const [valoresTesteTexto, setValoresTesteTexto] = useState("");
  const [rodandoEsfera2, setRodandoEsfera2] = useState(false);
  const [resultado, setResultado] = useState<ResultadoFeatureLab | null>(null);

  // --- resultado: ordenação/filtro ---
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
  // estado quando uma prop muda") em vez de useEffect.
  const [baseAnterior, setBaseAnterior] = useState<BaseFeatureLab | null>(null);
  if (base !== baseAnterior) {
    setBaseAnterior(base);
    setInfo(null);
    setColunasBase([]);
    setColunasNumericasBase([]);
    setResultadoEsfera1(null);
    setResultado(null);
    setFonteEsfera2("bruta");
  }

  useEffect(() => {
    if (!base) return;

    if (base.tipo === "painel") {
      buscarInfoPainel(base.nome, colunaY)
        .then((i) => {
          setInfo(i);
          setColunasBase(i.colunas);
          setColunasNumericasBase(i.colunas_numericas);
          setChave(i.chave_sugerida);
          setColunaTempo(i.tempo_sugerido);
          setColunasValor(new Set(i.colunas_valor_disponiveis));
          setColunasX(new Set(i.colunas_numericas));
        })
        .catch((e) => setErro(String(e)));
    } else {
      buscarPreviewDataset(base.nome)
        .then((p) => {
          setColunasBase(p.colunas);
          setColunasNumericasBase(p.colunas_numericas);
          setColunasX(new Set(p.colunas_numericas));
          const chaveSugerida = p.colunas[0] ?? "";
          const tempoSugerido =
            p.colunas.find((c) => CANDIDATOS_TEMPO.has(c.toLowerCase())) ?? p.colunas[1] ?? "";
          setChave(chaveSugerida);
          setColunaTempo(tempoSugerido);
          setColunasValor(new Set(p.colunas_numericas));
        })
        .catch((e) => setErro(String(e)));
    }
  }, [base, colunaY]);

  function alternar<T>(conjunto: Set<T>, item: T, aoMudar: (s: Set<T>) => void) {
    const novo = new Set(conjunto);
    if (novo.has(item)) novo.delete(item);
    else novo.add(item);
    aoMudar(novo);
  }

  function adicionarJanelaCustom() {
    const n = Number(janelaCustom);
    if (Number.isFinite(n) && n > 0) {
      setJanelas((atual) => new Set(atual).add(n));
      setJanelaCustom("");
    }
  }

  async function aoEnviarPainel(arquivo: File, nome: string) {
    const infoNova = await uploadPainel(arquivo, nome);
    const lista = await listarBasesFeatureLab();
    setBases(lista);
    setBase({ nome: infoNova.nome, tipo: "painel" });
  }

  async function aoRodarEsfera1() {
    if (!base) return;
    if (colunasValor.size === 0) {
      setErro("Selecione ao menos uma coluna de valor.");
      return;
    }
    if (janelas.size === 0) {
      setErro("Selecione ao menos uma janela.");
      return;
    }

    setRodandoEsfera1(true);
    setErro(null);
    try {
      const r = await rodarAgregacao({
        base: base.nome,
        tipo: base.tipo,
        chave,
        coluna_tempo: colunaTempo,
        colunas_valor: [...colunasValor],
        janelas: [...janelas].sort((a, b) => a - b),
        coluna_y: colunaY,
      });
      setResultadoEsfera1(r);
      setColunasX(new Set(r.colunas_geradas));
      setFonteEsfera2("esfera1");
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
    const proporcao = proporcaoVariaveis.trim() === "" ? null : Number(proporcaoVariaveis);
    const parametros = {
      profundidade_maxima: profundidadeMaxima,
      n_arvores: nArvores,
      min_suporte: minSuporte,
      max_suporte: maxSuporte,
      max_regras: maxRegras,
      permitir_cruzamento_entre_bases: permitirCruzamento,
      coluna_y: colunaY,
      proporcao_variaveis_por_split: proporcao,
    };
    const usaRodarDireto = fonteEsfera2 === "bruta" && base.tipo === "flat";
    const paramsSplit =
      !usaRodarDireto && metodoSplit === "coluna"
        ? {
            metodo_split: "coluna" as const,
            coluna_split: colunaSplit,
            valores_dev: valoresDevTexto.split(",").map((s) => s.trim()).filter(Boolean),
            valores_teste: valoresTesteTexto.split(",").map((s) => s.trim()).filter(Boolean),
          }
        : {};
    try {
      let r: ResultadoFeatureLab;
      if (fonteEsfera2 === "esfera1") {
        if (!resultadoEsfera1) throw new Error("Rode a esfera 1 primeiro, ou troque a fonte pra 'colunas cruas'.");
        r = await descobrirEmTabela({
          tabela: resultadoEsfera1.tabela,
          colunas_x: [...colunasX],
          ...parametros,
          ...paramsSplit,
        });
      } else if (usaRodarDireto) {
        r = await rodarDireto({ dataset: base.nome, colunas_x: [...colunasX], ...parametros });
      } else {
        const bruta = await carregarBaseBruta(base.nome, base.tipo, colunaY);
        r = await descobrirEmTabela({ tabela: bruta.tabela, colunas_x: [...colunasX], ...parametros, ...paramsSplit });
      }
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

  function aoLimparEsfera1() {
    setResultadoEsfera1(null);
    setFonteEsfera2("bruta");
  }

  function aoLimparTudo() {
    setBase(null);
    setColunaY("y");
    setResultadoEsfera1(null);
    setResultado(null);
    setFonteEsfera2("bruta");
    setColunasX(new Set());
    setProporcaoVariaveis("");
    setMetodoSplit("aleatorio");
    setColunaSplit("");
    setValoresDevTexto("");
    setValoresTesteTexto("");
    setErro(null);
    setAba("esfera1");
  }

  // Qual variável bruta originou uma coluna gerada -- o nome já entrega
  // isso (`dias_atraso_tendencia_3m` -> `dias_atraso`), mas pedido
  // explícito: uma marcação visual além do nome. Reconhece pelo prefixo
  // contra a lista real de colunas originais (mais confiável que regex
  // solto, já que a convenção de sufixo vive só no backend).
  function origemDe(colunaGerada: string, colunasOriginais: string[]): string {
    return colunasOriginais.find((o) => colunaGerada.startsWith(`${o}_`)) ?? "?";
  }

  const CORES_ORIGEM: Record<string, string> = {};
  const PALETA_ORIGEM = ["text-sky-400", "text-violet-400", "text-amber-400", "text-rose-400", "text-cyan-400"];
  (resultadoEsfera1?.colunas_originais ?? []).forEach((o, i) => {
    CORES_ORIGEM[o] = PALETA_ORIGEM[i % PALETA_ORIGEM.length];
  });

  const colunasGeradasComIv = [...(resultadoEsfera1?.colunas_geradas ?? [])].sort(
    (a, b) => (resultadoEsfera1?.ivs[b] ?? 0) - (resultadoEsfera1?.ivs[a] ?? 0),
  );
  const colunasOriginaisComIv = [...(resultadoEsfera1?.colunas_originais ?? [])].sort(
    (a, b) => (resultadoEsfera1?.ivs_originais[b] ?? 0) - (resultadoEsfera1?.ivs_originais[a] ?? 0),
  );
  const colunasParaEsfera2 = fonteEsfera2 === "esfera1" ? (resultadoEsfera1?.colunas_geradas ?? []) : colunasNumericasBase;
  // rodarDireto já usa o dev.csv/teste.csv que o usuário preparou na aba
  // Dataset do Pedro_Wise -- não faz sentido oferecer split de novo aqui.
  const usaRodarDireto = fonteEsfera2 === "bruta" && base?.tipo === "flat";

  const regrasFiltradas: RegraFeatureLab[] = (resultado?.regras ?? [])
    .filter((r) => r.iv_teste >= ivMinimo)
    .filter((r) => {
      if (nVariaveisFiltro === "todas") return true;
      if (nVariaveisFiltro === "1") return r.n_variaveis === 1;
      return r.n_variaveis >= 2;
    })
    .sort((a, b) => (ordemAsc ? 1 : -1) * (a[ordenarPor] - b[ordenarPor]));

  return (
    <div className="flex h-screen">
      <SidebarFeatureLab
        bases={bases}
        base={base}
        aoMudarBase={setBase}
        aoEnviarPainel={aoEnviarPainel}
        colunasBase={colunasBase}
        colunaY={colunaY}
        aoMudarColunaY={setColunaY}
        aoLimparTudo={aoLimparTudo}
      />

      <main className="flex-1 overflow-y-auto p-6">
        <header className="mb-6 flex items-center justify-between">
          <div>
            <h1 className="text-lg font-semibold text-slate-100">Feature-lab</h1>
            <p className="text-sm text-slate-500">
              {base ? `Base: ${base.nome}` : "Escolha uma base na barra lateral"}
              {info && ` — ${info.n_linhas.toLocaleString("pt-BR")} linhas, ${info.n_chaves.toLocaleString("pt-BR")} chaves`}
            </p>
          </div>
          <Link href="/" className="text-xs text-slate-500 hover:text-emerald-400">
            ← voltar pro Pedro_Wise
          </Link>
        </header>

        <nav className="mb-6 flex gap-1 rounded-lg bg-slate-900/70 p-1 w-fit">
          {ABAS.map((a) => (
            <button
              key={a.id}
              onClick={() => setAba(a.id)}
              className={`rounded-md px-4 py-1.5 text-sm font-medium transition ${
                aba === a.id ? "bg-slate-700 text-white shadow-sm" : "text-slate-400 hover:text-slate-200"
              }`}
            >
              {a.rotulo}
            </button>
          ))}
        </nav>

        {erro && <p className="mb-4 text-sm text-red-400">{erro}</p>}

        {!base ? (
          <p className="text-sm text-slate-600">Escolha uma base na barra lateral primeiro.</p>
        ) : (
          <>
            <div className={aba === "esfera1" ? "" : "hidden"}>
              <div className="rounded-xl border border-slate-700 bg-slate-900/70 p-5">
                <h2 className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-400">
                  Agregação temporal
                </h2>
                <p className="mb-4 text-xs text-slate-500">
                  Opcional — gera máximo/média/mínimo/desvio/tendência sobre janela móvel, agrupado por
                  chave. Pule esta aba se sua base não tem granularidade de painel.
                </p>
                <div className="flex flex-col gap-3">
                  <div className="flex flex-wrap gap-4">
                    <div>
                      <label className="mb-1 block text-[11px] text-slate-500">chave</label>
                      <select
                        value={chave}
                        onChange={(e) => setChave(e.target.value)}
                        className="rounded-lg bg-slate-800 border border-slate-600 px-2 py-1.5 text-sm text-slate-100"
                      >
                        {colunasBase.map((c) => (
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
                        {colunasBase.map((c) => (
                          <option key={c} value={c}>
                            {c}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>
                  <div>
                    <p className="mb-1.5 text-[11px] text-slate-500">
                      colunas brutas a agregar (máximo/média/mínimo/desvio/tendência por janela)
                    </p>
                    <div className="flex flex-wrap gap-2">
                      {colunasBase
                        .filter((c) => c !== chave && c !== colunaTempo && c !== "y")
                        .map((c) => (
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
                    <p className="mb-1.5 text-[11px] text-slate-500">janelas (períodos)</p>
                    <div className="flex flex-wrap items-center gap-2">
                      {JANELAS_COMUNS.map((n) => (
                        <label
                          key={n}
                          className="flex cursor-pointer items-center gap-1.5 rounded-full border border-slate-700 bg-slate-800/60 px-2.5 py-1 text-xs text-slate-300"
                        >
                          <input
                            type="checkbox"
                            checked={janelas.has(n)}
                            onChange={() => alternar(janelas, n, setJanelas)}
                            className="h-3.5 w-3.5 rounded border-slate-600 bg-slate-800 text-emerald-500 focus:ring-emerald-500"
                          />
                          M{n}
                        </label>
                      ))}
                      {[...janelas]
                        .filter((n) => !JANELAS_COMUNS.includes(n))
                        .sort((a, b) => a - b)
                        .map((n) => (
                          <button
                            key={n}
                            onClick={() => alternar(janelas, n, setJanelas)}
                            className="rounded-full border border-emerald-700 bg-emerald-950/40 px-2.5 py-1 text-xs text-emerald-300"
                          >
                            M{n} ×
                          </button>
                        ))}
                      <input
                        type="number"
                        min={1}
                        value={janelaCustom}
                        onChange={(e) => setJanelaCustom(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === "Enter") {
                            e.preventDefault();
                            adicionarJanelaCustom();
                          }
                        }}
                        placeholder="outra"
                        className="w-20 rounded-lg bg-slate-800 border border-slate-600 px-2 py-1 text-xs text-slate-100"
                      />
                      <button
                        onClick={adicionarJanelaCustom}
                        className="rounded-lg border border-slate-600 px-2 py-1 text-xs text-slate-300 hover:border-emerald-700 hover:text-emerald-400"
                      >
                        + adicionar
                      </button>
                    </div>
                  </div>
                </div>
                <button
                  onClick={aoRodarEsfera1}
                  disabled={rodandoEsfera1}
                  className="mt-4 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {rodandoEsfera1 ? "Rodando…" : "Rodar esfera 1"}
                </button>

                {resultadoEsfera1 && (
                  <div className="mt-4 border-t border-slate-800 pt-4">
                    <div className="mb-3 flex items-center justify-between">
                      <div className="grid grow grid-cols-2 gap-3 sm:grid-cols-4">
                        <Metrica
                          rotulo="linhas do painel"
                          valor={resultadoEsfera1.n_linhas_painel.toLocaleString("pt-BR")}
                        />
                        <Metrica rotulo="chaves" valor={resultadoEsfera1.n_chaves.toLocaleString("pt-BR")} />
                        <Metrica rotulo="colunas geradas" valor={String(resultadoEsfera1.colunas_geradas.length)} />
                        <Metrica
                          rotulo="linhas resultantes"
                          valor={resultadoEsfera1.tabela.length.toLocaleString("pt-BR")}
                        />
                      </div>
                      <button
                        onClick={aoLimparEsfera1}
                        className="ml-3 shrink-0 rounded-lg border border-slate-600 px-3 py-1.5 text-xs font-medium text-slate-400 transition hover:border-slate-500 hover:text-slate-200"
                      >
                        Limpar
                      </button>
                    </div>

                    <p className="mb-4 text-xs text-slate-500">
                      Variável resposta: <span className="font-mono text-slate-300">{colunaY}</span> (configurável
                      na barra lateral).
                      {resultadoEsfera1.taxa_evento !== null &&
                        ` Taxa de evento: ${(resultadoEsfera1.taxa_evento * 100).toFixed(1)}%.`}
                    </p>

                    <div className="grid gap-4 md:grid-cols-2">
                      <div>
                        <p className="mb-1.5 text-[11px] text-slate-500">
                          variáveis originais (como estavam na base, no último período de cada chave)
                        </p>
                        <div className="max-h-96 overflow-y-auto rounded-lg border border-slate-700">
                          <table className="w-full text-xs">
                            <thead className="sticky top-0 bg-slate-800/90 text-slate-400">
                              <tr>
                                <th className="px-3 py-1.5 text-left font-medium">coluna</th>
                                <th className="px-3 py-1.5 text-right font-medium">IV</th>
                              </tr>
                            </thead>
                            <tbody>
                              {colunasOriginaisComIv.map((c, i) => (
                                <tr key={c} className={i % 2 === 0 ? "bg-slate-900/40" : "bg-slate-900/70"}>
                                  <td className={`px-3 py-1 font-mono ${CORES_ORIGEM[c] ?? "text-slate-300"}`}>
                                    {c}
                                  </td>
                                  <td className="px-3 py-1 text-right tabular-nums text-slate-300">
                                    {(resultadoEsfera1.ivs_originais[c] ?? 0).toFixed(3)}
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>

                      <div>
                        <p className="mb-1.5 text-[11px] text-slate-500">
                          variáveis construídas (por IV individual, antes de qualquer combinação)
                        </p>
                        <div className="max-h-96 overflow-y-auto rounded-lg border border-slate-700">
                          <table className="w-full text-xs">
                            <thead className="sticky top-0 bg-slate-800/90 text-slate-400">
                              <tr>
                                <th className="px-3 py-1.5 text-left font-medium">coluna</th>
                                <th className="px-3 py-1.5 text-left font-medium">origem</th>
                                <th className="px-3 py-1.5 text-right font-medium">IV</th>
                              </tr>
                            </thead>
                            <tbody>
                              {colunasGeradasComIv.map((c, i) => {
                                const origem = origemDe(c, resultadoEsfera1.colunas_originais);
                                return (
                                  <tr key={c} className={i % 2 === 0 ? "bg-slate-900/40" : "bg-slate-900/70"}>
                                    <td className="px-3 py-1 font-mono text-slate-300">{c}</td>
                                    <td className={`px-3 py-1 font-mono ${CORES_ORIGEM[origem] ?? "text-slate-500"}`}>
                                      {origem}
                                    </td>
                                    <td className="px-3 py-1 text-right tabular-nums text-emerald-400">
                                      {(resultadoEsfera1.ivs[c] ?? 0).toFixed(3)}
                                    </td>
                                  </tr>
                                );
                              })}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    </div>

                    <p className="mt-3 text-xs text-slate-500">
                      Pronto — vá pra aba <span className="text-slate-300">Esfera 2</span> pra descobrir
                      interações a partir dessas colunas.
                    </p>
                  </div>
                )}
              </div>
            </div>

            <div className={aba === "esfera2" ? "" : "hidden"}>
              <div className="rounded-xl border border-slate-700 bg-slate-900/70 p-5">
                <h2 className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-400">
                  Descoberta de interação
                </h2>

                <div className="mb-4">
                  <p className="mb-1.5 text-[11px] text-slate-500">fonte das colunas candidatas</p>
                  <div className="flex gap-2">
                    <button
                      onClick={() => setFonteEsfera2("bruta")}
                      className={`rounded-lg border px-3 py-1.5 text-xs font-medium transition ${
                        fonteEsfera2 === "bruta"
                          ? "border-emerald-600 bg-emerald-950/40 text-emerald-300"
                          : "border-slate-700 bg-slate-800/60 text-slate-400 hover:text-slate-200"
                      }`}
                    >
                      colunas da base (sem agregação)
                    </button>
                    <button
                      onClick={() => setFonteEsfera2("esfera1")}
                      disabled={!resultadoEsfera1}
                      className={`rounded-lg border px-3 py-1.5 text-xs font-medium transition disabled:cursor-not-allowed disabled:opacity-40 ${
                        fonteEsfera2 === "esfera1"
                          ? "border-emerald-600 bg-emerald-950/40 text-emerald-300"
                          : "border-slate-700 bg-slate-800/60 text-slate-400 hover:text-slate-200"
                      }`}
                    >
                      resultado da esfera 1{!resultadoEsfera1 && " (rode a esfera 1 primeiro)"}
                    </button>
                  </div>
                </div>

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
                  <div>
                    <label className="mb-1 block text-[11px] text-slate-500">variáveis por split</label>
                    <input
                      type="number"
                      step={0.1}
                      min={0}
                      max={1}
                      value={proporcaoVariaveis}
                      onChange={(e) => setProporcaoVariaveis(e.target.value)}
                      placeholder="todas"
                      className="w-full rounded-lg bg-slate-800 border border-slate-600 px-2 py-1.5 text-sm text-slate-100"
                    />
                  </div>
                </div>
                <p className="mt-2 text-xs text-slate-500">
                  <span className="text-slate-400">suporte mínimo/máximo</span>: fração de linhas que precisa
                  satisfazer a regra pra ela contar — muito raro (abaixo do mínimo) é ruído/overfit de poucos
                  casos, muito comum (acima do máximo) não discrimina nada.{" "}
                  <span className="text-slate-400">variáveis por split</span>: em branco, toda árvore considera
                  todas as colunas em cada split — se uma variável for bem mais forte que as outras, ela domina
                  toda árvore e combinações com variáveis mais fracas nunca chegam a ser testadas. Um valor tipo
                  0.5-0.7 limita cada split a uma amostra aleatória das colunas, dando chance às mais fracas.
                </p>
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

                {!usaRodarDireto && (
                  <div className="mt-4 border-t border-slate-800 pt-4">
                    <p className="mb-1.5 text-[11px] text-slate-500">split treino/teste</p>
                    <div className="flex gap-2">
                      <button
                        onClick={() => setMetodoSplit("aleatorio")}
                        className={`rounded-lg border px-3 py-1.5 text-xs font-medium transition ${
                          metodoSplit === "aleatorio"
                            ? "border-emerald-600 bg-emerald-950/40 text-emerald-300"
                            : "border-slate-700 bg-slate-800/60 text-slate-400 hover:text-slate-200"
                        }`}
                      >
                        aleatório (50/50)
                      </button>
                      <button
                        onClick={() => setMetodoSplit("coluna")}
                        className={`rounded-lg border px-3 py-1.5 text-xs font-medium transition ${
                          metodoSplit === "coluna"
                            ? "border-emerald-600 bg-emerald-950/40 text-emerald-300"
                            : "border-slate-700 bg-slate-800/60 text-slate-400 hover:text-slate-200"
                        }`}
                      >
                        coluna de amostra existente
                      </button>
                    </div>

                    {metodoSplit === "coluna" && (
                      <div className="mt-3 flex flex-wrap items-end gap-3">
                        <div>
                          <label className="mb-1 block text-[11px] text-slate-500">coluna</label>
                          <select
                            value={colunaSplit}
                            onChange={(e) => setColunaSplit(e.target.value)}
                            className="rounded-lg bg-slate-800 border border-slate-600 px-2 py-1.5 text-sm text-slate-100"
                          >
                            <option value="">selecione…</option>
                            {colunasBase.map((c) => (
                              <option key={c} value={c}>
                                {c}
                              </option>
                            ))}
                          </select>
                        </div>
                        <div>
                          <label className="mb-1 block text-[11px] text-slate-500">
                            valores = treino (separados por vírgula)
                          </label>
                          <input
                            type="text"
                            value={valoresDevTexto}
                            onChange={(e) => setValoresDevTexto(e.target.value)}
                            placeholder="dev,treino"
                            className="w-40 rounded-lg bg-slate-800 border border-slate-600 px-2 py-1.5 text-sm text-slate-100"
                          />
                        </div>
                        <div>
                          <label className="mb-1 block text-[11px] text-slate-500">
                            valores = teste (separados por vírgula)
                          </label>
                          <input
                            type="text"
                            value={valoresTesteTexto}
                            onChange={(e) => setValoresTesteTexto(e.target.value)}
                            placeholder="teste,oot"
                            className="w-40 rounded-lg bg-slate-800 border border-slate-600 px-2 py-1.5 text-sm text-slate-100"
                          />
                        </div>
                      </div>
                    )}
                  </div>
                )}

                <button
                  onClick={aoRodarEsfera2}
                  disabled={rodandoEsfera2}
                  className="mt-4 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {rodandoEsfera2 ? "Rodando…" : "Rodar esfera 2"}
                </button>
              </div>

              {resultado && (
                <div className="mt-6 rounded-xl border border-slate-700 bg-slate-900/70 p-5">
                  <h2 className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-400">Resultado</h2>
                  <div className="mb-4 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
                    <Metrica rotulo="colunas candidatas" valor={String(resultado.colunas_x.length)} />
                    <Metrica rotulo="dev / teste" valor={`${resultado.n_dev} / ${resultado.n_teste}`} />
                    <Metrica rotulo="taxa evento dev" valor={`${(resultado.taxa_evento_dev * 100).toFixed(1)}%`} />
                    <Metrica
                      rotulo="taxa evento teste"
                      valor={`${(resultado.taxa_evento_teste * 100).toFixed(1)}%`}
                    />
                    <Metrica rotulo="tempo de execução" valor={`${resultado.tempo_execucao_segundos.toFixed(2)}s`} />
                  </div>

                  {resultado.regras.length === 0 ? (
                    <p className="text-sm text-slate-500">
                      Nenhuma regra sobreviveu aos filtros de suporte — tente ajustar suporte
                      mínimo/máximo ou profundidade na aba Esfera 2.
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
                          {regrasFiltradas.length} de {resultado.regras.length} regras — clique nos
                          cabeçalhos pra ordenar
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
                                <td className="px-3 py-1.5 text-right tabular-nums text-slate-400">
                                  {r.iv_dev.toFixed(3)}
                                </td>
                                <td className="px-3 py-1.5 text-right tabular-nums text-slate-400">
                                  {r.suporte_teste.toFixed(3)}
                                </td>
                                <td className="px-3 py-1.5 text-right tabular-nums text-slate-400">
                                  {r.n_condicoes}
                                </td>
                                <td className="px-3 py-1.5 text-right tabular-nums text-slate-400">
                                  {r.n_variaveis}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </>
                  )}
                </div>
              )}
            </div>
          </>
        )}
      </main>
    </div>
  );
}
