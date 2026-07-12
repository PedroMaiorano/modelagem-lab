"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import GraficoKS from "../components/GraficoKS";
import SidebarFeatureLab from "../components/SidebarFeatureLab";
import {
  buscarInfoPainel,
  buscarPreviewDataset,
  carregarBaseBruta,
  compararComPedroWise,
  descobrirEmTabela,
  listarBasesFeatureLab,
  rodarAgregacao,
  rodarDireto,
  rodarRegressaoManual,
  uploadPainel,
  type BaseFeatureLab,
  type InfoPainel,
  type RegraFeatureLab,
  type ResultadoAgregacao,
  type ResultadoComparacaoPedroWise,
  type ResultadoFeatureLab,
  type ResultadoRegressaoManual,
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
  { id: "esfera3", rotulo: "Esfera 3" },
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
  // variáveis numéricas que o usuário marcou pra WOE-codificar antes da
  // esfera 2 -- pra código categórico sem ordem real (ex.: Thallium no
  // Heart Disease: 3/6/7 não é uma escala). Colunas de texto não precisam
  // estar aqui, entram nesse tratamento automaticamente no backend.
  const [colunasCategoricasMarcadas, setColunasCategoricasMarcadas] = useState<Set<string>>(new Set());
  const [rodandoEsfera2, setRodandoEsfera2] = useState(false);
  const [resultado, setResultado] = useState<ResultadoFeatureLab | null>(null);

  // --- split treino/teste (compartilhado entre esferas 2 e 3, mora na sidebar) ---
  const [metodoSplit, setMetodoSplit] = useState<"aleatorio" | "coluna">("aleatorio");
  const [colunaSplit, setColunaSplit] = useState("");
  const [valoresDevSplit, setValoresDevSplit] = useState<Set<string>>(new Set());
  const [valoresTesteSplit, setValoresTesteSplit] = useState<Set<string>>(new Set());

  // --- esfera 3 ---
  const [colunasX3, setColunasX3] = useState<Set<string>>(new Set());
  // regras de interação descobertas na esfera 2 (identificadas pelo nome da
  // regra) que o usuário quer usar como variável 0/1 na regressão manual --
  // materializadas dentro do próprio backend (ver rodar_regressao_manual),
  // não aqui no cliente.
  const [regrasX3, setRegrasX3] = useState<Set<string>>(new Set());
  const [rodandoEsfera3, setRodandoEsfera3] = useState(false);
  const [resultadoEsfera3, setResultadoEsfera3] = useState<ResultadoRegressaoManual | null>(null);
  // comparação "prova de valor": stepwise real do Pedro_Wise com vs. sem as
  // regras selecionadas como candidata -- usa as mesmas colunasX3/regrasX3
  // já escolhidas acima.
  const [rodandoComparacao, setRodandoComparacao] = useState(false);
  const [resultadoComparacao, setResultadoComparacao] = useState<ResultadoComparacaoPedroWise | null>(null);

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
    setResultadoEsfera3(null);
    setResultadoComparacao(null);
    setFonteEsfera2("bruta");
    setColunaSplit("");
    setValoresDevSplit(new Set());
    setValoresTesteSplit(new Set());
    setRegrasX3(new Set());
    setColunasCategoricasMarcadas(new Set());
    setErro(null);
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

  // Um valor só pode ser treino OU teste, nunca os dois -- marcar um lado
  // desmarca o outro automaticamente.
  function aoAlternarValorSplit(valor: string, destino: "dev" | "teste") {
    if (destino === "dev") {
      setValoresDevSplit((atual) => {
        const novo = new Set(atual);
        if (novo.has(valor)) novo.delete(valor);
        else novo.add(valor);
        return novo;
      });
      setValoresTesteSplit((atual) => {
        const novo = new Set(atual);
        novo.delete(valor);
        return novo;
      });
    } else {
      setValoresTesteSplit((atual) => {
        const novo = new Set(atual);
        if (novo.has(valor)) novo.delete(valor);
        else novo.add(valor);
        return novo;
      });
      setValoresDevSplit((atual) => {
        const novo = new Set(atual);
        novo.delete(valor);
        return novo;
      });
    }
  }

  function construirParamsSplit(usaRodarDireto: boolean) {
    if (usaRodarDireto || metodoSplit !== "coluna") return {};
    return {
      metodo_split: "coluna" as const,
      coluna_split: colunaSplit,
      valores_dev: [...valoresDevSplit],
      valores_teste: [...valoresTesteSplit],
    };
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
    const parametrosBase = {
      profundidade_maxima: profundidadeMaxima,
      n_arvores: nArvores,
      min_suporte: minSuporte,
      max_suporte: maxSuporte,
      max_regras: maxRegras,
      permitir_cruzamento_entre_bases: permitirCruzamento,
      proporcao_variaveis_por_split: proporcao,
      colunas_categoricas: [...colunasCategoricasMarcadas],
    };
    const usaRodarDireto = fonteEsfera2 === "bruta" && base.tipo === "flat";
    const paramsSplit = construirParamsSplit(usaRodarDireto);
    try {
      let r: ResultadoFeatureLab;
      if (fonteEsfera2 === "esfera1") {
        // resultadoEsfera1.tabela já veio de agregar_base com a coluna
        // resposta renomeada pra "y" -- mandar colunaY (nome original) de
        // novo aqui faria descobrirEmTabela procurar uma coluna que não
        // existe mais na tabela já processada.
        if (!resultadoEsfera1) throw new Error("Rode a esfera 1 primeiro, ou troque a fonte pra 'colunas cruas'.");
        r = await descobrirEmTabela({
          tabela: resultadoEsfera1.tabela,
          colunas_x: [...colunasX],
          ...parametrosBase,
          coluna_y: "y",
          ...paramsSplit,
        });
      } else if (usaRodarDireto) {
        r = await rodarDireto({ dataset: base.nome, colunas_x: [...colunasX], ...parametrosBase, coluna_y: colunaY });
      } else {
        // mesma coisa: carregarBaseBruta já renomeia coluna_y -> "y" no backend.
        const bruta = await carregarBaseBruta(base.nome, base.tipo, colunaY);
        r = await descobrirEmTabela({
          tabela: bruta.tabela,
          colunas_x: [...colunasX],
          ...parametrosBase,
          coluna_y: "y",
          ...paramsSplit,
        });
      }
      setResultado(r);
    } catch (e) {
      setErro(String(e));
    } finally {
      setRodandoEsfera2(false);
    }
  }

  async function aoRodarEsfera3() {
    if (!base) return;
    if (colunasX3.size === 0 && regrasX3.size === 0) {
      setErro("Selecione ao menos uma coluna ou regra.");
      return;
    }
    if (fonteEsfera2 === "esfera1" && !resultadoEsfera1) {
      setErro("Rode a esfera 1 primeiro, ou troque a fonte pra 'colunas da base' na aba Esfera 2.");
      return;
    }

    setRodandoEsfera3(true);
    setErro(null);
    try {
      // as duas fontes (agregar_base e carregarBaseBruta) já renomeiam a
      // coluna resposta pra "y" no backend -- nunca colunaY (nome original)
      // aqui, mesma causa do bug corrigido em aoRodarEsfera2.
      const tabela =
        fonteEsfera2 === "esfera1" && resultadoEsfera1
          ? resultadoEsfera1.tabela
          : (await carregarBaseBruta(base.nome, base.tipo, colunaY)).tabela;
      // regras (se houver) são materializadas dentro do próprio backend,
      // na mesma chamada -- split + WOE de categórica + materialização de
      // regra precisam acontecer juntos (ver rodar_regressao_manual),
      // senão uma regra que referencie uma coluna WOE (ex.: Thallium_woe)
      // não encontra essa coluna, que só existe depois do split+WOE.
      const regrasSelecionadas = resultado ? resultado.regras.filter((r) => regrasX3.has(r.regra)) : [];
      const r = await rodarRegressaoManual({
        tabela,
        colunas_x: [...colunasX3],
        coluna_y: "y",
        regras: regrasSelecionadas.map((rg) => ({ condicoes: rg.condicoes })),
        colunas_categoricas: [...colunasCategoricasMarcadas],
        ...construirParamsSplit(false),
      });
      setResultadoEsfera3(r);
    } catch (e) {
      setErro(String(e));
    } finally {
      setRodandoEsfera3(false);
    }
  }

  async function aoRodarComparacao() {
    if (!base) return;
    if (colunasX3.size === 0) {
      setErro("Selecione ao menos uma coluna base pra comparar.");
      return;
    }
    if (fonteEsfera2 === "esfera1" && !resultadoEsfera1) {
      setErro("Rode a esfera 1 primeiro, ou troque a fonte pra 'colunas da base' na aba Esfera 2.");
      return;
    }

    setRodandoComparacao(true);
    setErro(null);
    try {
      const tabela =
        fonteEsfera2 === "esfera1" && resultadoEsfera1
          ? resultadoEsfera1.tabela
          : (await carregarBaseBruta(base.nome, base.tipo, colunaY)).tabela;
      const regrasSelecionadas = resultado ? resultado.regras.filter((r) => regrasX3.has(r.regra)) : [];
      const r = await compararComPedroWise({
        tabela,
        colunas_base: [...colunasX3],
        regras: regrasSelecionadas.map((rg) => ({ condicoes: rg.condicoes })),
        coluna_y: "y",
        colunas_categoricas: [...colunasCategoricasMarcadas],
        ...construirParamsSplit(false),
      });
      setResultadoComparacao(r);
    } catch (e) {
      setErro(String(e));
    } finally {
      setRodandoComparacao(false);
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
    setResultadoEsfera3(null);
    setResultadoComparacao(null);
    setFonteEsfera2("bruta");
    setColunasX(new Set());
    setColunasX3(new Set());
    setRegrasX3(new Set());
    setColunasCategoricasMarcadas(new Set());
    setProporcaoVariaveis("");
    setMetodoSplit("aleatorio");
    setColunaSplit("");
    setValoresDevSplit(new Set());
    setValoresTesteSplit(new Set());
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
  // colunas de texto (não-numéricas) da base -- viram candidata também, mas
  // sempre entram WOE-codificadas automaticamente no backend (não têm outro
  // jeito de virar corte `<=`/`>` no extrator de regra), diferente das
  // numéricas marcadas manualmente em `colunasCategoricasMarcadas` abaixo.
  const colunasTextoBase = colunasBase.filter((c) => c !== colunaY && !colunasNumericasBase.includes(c));
  const colunasParaEsfera2 =
    fonteEsfera2 === "esfera1" ? (resultadoEsfera1?.colunas_geradas ?? []) : [...colunasNumericasBase, ...colunasTextoBase];
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
        metodoSplit={metodoSplit}
        aoMudarMetodoSplit={setMetodoSplit}
        colunaSplit={colunaSplit}
        aoMudarColunaSplit={setColunaSplit}
        valoresDev={valoresDevSplit}
        valoresTeste={valoresTesteSplit}
        aoAlternarValorSplit={aoAlternarValorSplit}
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
                  <p className="mb-1.5 text-[11px] text-slate-500">
                    colunas candidatas{" "}
                    {colunasTextoBase.length > 0 && fonteEsfera2 === "bruta" && (
                      <span className="text-amber-500">
                        (texto, borda tracejada, vira WOE automaticamente)
                      </span>
                    )}
                  </p>
                  <div className="flex max-h-40 flex-wrap gap-2 overflow-y-auto">
                    {colunasParaEsfera2.map((c) => {
                      const ehTexto = fonteEsfera2 === "bruta" && colunasTextoBase.includes(c);
                      return (
                        <label
                          key={c}
                          title={ehTexto ? "coluna de texto -- WOE-codificada automaticamente" : undefined}
                          className={`flex cursor-pointer items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs ${
                            ehTexto
                              ? "border-dashed border-amber-700 bg-amber-950/20 text-amber-200"
                              : "border-slate-700 bg-slate-800/60 text-slate-300"
                          }`}
                        >
                          <input
                            type="checkbox"
                            checked={colunasX.has(c)}
                            onChange={() => alternar(colunasX, c, setColunasX)}
                            className="h-3.5 w-3.5 rounded border-slate-600 bg-slate-800 text-emerald-500 focus:ring-emerald-500"
                          />
                          {c}
                        </label>
                      );
                    })}
                  </div>
                </div>

                {fonteEsfera2 === "bruta" && [...colunasX].some((c) => !colunasTextoBase.includes(c)) && (
                  <div className="mb-4">
                    <p className="mb-1.5 text-[11px] text-slate-500">
                      tratar como categórica (WOE) — pra código numérico sem ordem real, ex.: um campo tipo
                      &ldquo;Thallium&rdquo; onde 3/6/7 são categorias, não uma escala
                    </p>
                    <div className="flex max-h-32 flex-wrap gap-2 overflow-y-auto">
                      {[...colunasX]
                        .filter((c) => !colunasTextoBase.includes(c))
                        .map((c) => (
                          <label
                            key={c}
                            className="flex cursor-pointer items-center gap-1.5 rounded-full border border-amber-800 bg-amber-950/10 px-2.5 py-1 text-xs text-amber-200"
                          >
                            <input
                              type="checkbox"
                              checked={colunasCategoricasMarcadas.has(c)}
                              onChange={() => alternar(colunasCategoricasMarcadas, c, setColunasCategoricasMarcadas)}
                              className="h-3.5 w-3.5 rounded border-amber-600 bg-slate-800 text-amber-500 focus:ring-amber-500"
                            />
                            {c}
                          </label>
                        ))}
                    </div>
                  </div>
                )}

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
                  <p className="mt-3 text-xs text-slate-500">
                    Split treino/teste configurado na barra lateral ({metodoSplit === "aleatorio" ? "aleatório" : `coluna "${colunaSplit || "?"}"`}).
                  </p>
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

            <div className={aba === "esfera3" ? "" : "hidden"}>
              <div className="rounded-xl border border-slate-700 bg-slate-900/70 p-5">
                <h2 className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-400">
                  Regressão logística manual
                </h2>
                <p className="mb-4 text-xs text-slate-500">
                  Monta um modelo com as variáveis que você escolher (mesma fonte configurada na aba
                  Esfera 2 — colunas da base ou saída da esfera 1) e mede KS/AUC de verdade, com o mesmo
                  núcleo do Pedro_Wise.
                </p>

                <div className="mb-4">
                  <div className="mb-1.5 flex items-center justify-between">
                    <p className="text-[11px] text-slate-500">variáveis do modelo</p>
                    <div className="flex gap-2 text-[11px]">
                      <button
                        onClick={() => setColunasX3(new Set(colunasParaEsfera2))}
                        className="text-slate-400 underline-offset-2 hover:text-emerald-400 hover:underline"
                      >
                        selecionar todas
                      </button>
                      <button
                        onClick={() => setColunasX3(new Set())}
                        className="text-slate-400 underline-offset-2 hover:text-red-400 hover:underline"
                      >
                        limpar
                      </button>
                    </div>
                  </div>
                  <div className="flex max-h-48 flex-wrap gap-2 overflow-y-auto">
                    {colunasParaEsfera2.map((c) => (
                      <label
                        key={c}
                        className="flex cursor-pointer items-center gap-1.5 rounded-full border border-slate-700 bg-slate-800/60 px-2.5 py-1 text-xs text-slate-300"
                      >
                        <input
                          type="checkbox"
                          checked={colunasX3.has(c)}
                          onChange={() => alternar(colunasX3, c, setColunasX3)}
                          className="h-3.5 w-3.5 rounded border-slate-600 bg-slate-800 text-emerald-500 focus:ring-emerald-500"
                        />
                        {c}
                      </label>
                    ))}
                  </div>
                </div>

                {resultado && resultado.regras.length > 0 && (
                  <div className="mb-4">
                    <div className="mb-1.5 flex items-center justify-between">
                      <p className="text-[11px] text-slate-500">
                        regras de interação descobertas na esfera 2 (viram coluna 0/1)
                      </p>
                      <div className="flex gap-2 text-[11px]">
                        <button
                          onClick={() => setRegrasX3(new Set(resultado.regras.map((r) => r.regra)))}
                          className="text-slate-400 underline-offset-2 hover:text-emerald-400 hover:underline"
                        >
                          selecionar todas
                        </button>
                        <button
                          onClick={() => setRegrasX3(new Set())}
                          className="text-slate-400 underline-offset-2 hover:text-red-400 hover:underline"
                        >
                          limpar
                        </button>
                      </div>
                    </div>
                    <div className="flex max-h-48 flex-wrap gap-2 overflow-y-auto">
                      {resultado.regras.map((r) => (
                        <label
                          key={r.regra}
                          title={`IV teste ${r.iv_teste.toFixed(3)}`}
                          className="flex cursor-pointer items-center gap-1.5 rounded-full border border-violet-800 bg-violet-950/30 px-2.5 py-1 text-xs text-violet-200"
                        >
                          <input
                            type="checkbox"
                            checked={regrasX3.has(r.regra)}
                            onChange={() => alternar(regrasX3, r.regra, setRegrasX3)}
                            className="h-3.5 w-3.5 rounded border-violet-600 bg-slate-800 text-violet-500 focus:ring-violet-500"
                          />
                          {r.regra}
                        </label>
                      ))}
                    </div>
                  </div>
                )}

                <div className="flex flex-wrap gap-3">
                  <button
                    onClick={aoRodarEsfera3}
                    disabled={rodandoEsfera3}
                    className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {rodandoEsfera3 ? "Rodando…" : "Rodar esfera 3"}
                  </button>
                  <button
                    onClick={aoRodarComparacao}
                    disabled={rodandoComparacao}
                    title="Roda a seleção stepwise real do Pedro_Wise com e sem as regras marcadas acima, pra comparar o KS do modelo final de cada lado"
                    className="rounded-lg border border-violet-700 px-4 py-2 text-sm font-medium text-violet-300 transition hover:bg-violet-950/40 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {rodandoComparacao ? "Comparando…" : "Comparar com Pedro_Wise (com/sem regras)"}
                  </button>
                </div>
              </div>

              {resultadoComparacao && (
                <div className="mt-6 rounded-xl border border-violet-800 bg-violet-950/10 p-5">
                  <h2 className="mb-1 text-xs font-semibold uppercase tracking-wider text-violet-300">
                    Prova de valor: stepwise Pedro_Wise com vs. sem regras
                  </h2>
                  <p className="mb-4 text-xs text-slate-500">
                    Mesmo motor de seleção automática (forward/backward, níveis 1/2/2.5) da aba principal,
                    rodado duas vezes: uma só com as colunas base marcadas, outra com essas colunas + as
                    regras marcadas também como candidata. Se o KS &ldquo;com regras&rdquo; não superar o
                    &ldquo;sem regras&rdquo;, as regras não estão agregando valor nesse dataset.
                  </p>
                  <div className="grid gap-4 sm:grid-cols-2">
                    {(
                      [
                        { rotulo: "sem regras", r: resultadoComparacao.sem_regras, cor: "text-slate-300" },
                        { rotulo: "com regras", r: resultadoComparacao.com_regras, cor: "text-violet-300" },
                      ] as const
                    ).map(({ rotulo, r, cor }) => (
                      <div key={rotulo} className="rounded-lg border border-slate-700 bg-slate-900/60 p-4">
                        <p className={`mb-2 text-[11px] font-medium uppercase tracking-wider ${cor}`}>{rotulo}</p>
                        <div className="mb-3 grid grid-cols-3 gap-2">
                          <Metrica rotulo="KS teste" valor={r.ks_teste.toFixed(3)} />
                          <Metrica rotulo="KS dev" valor={r.ks_dev.toFixed(3)} />
                          <Metrica rotulo="AUC teste" valor={r.auc_teste.toFixed(3)} />
                        </div>
                        <p className="mb-1 text-[11px] text-slate-500">
                          {r.n_variaveis} variável(is) selecionada(s)
                        </p>
                        <div className="flex flex-wrap gap-1">
                          {r.variaveis.map((v) => (
                            <span
                              key={v}
                              className={`rounded-full border px-2 py-0.5 text-[11px] ${
                                v.includes("_regra")
                                  ? "border-violet-700 bg-violet-950/40 text-violet-200"
                                  : "border-slate-700 bg-slate-800/60 text-slate-300"
                              }`}
                            >
                              {v}
                            </span>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                  <p className="mt-4 text-sm">
                    ΔKS teste (com − sem regras):{" "}
                    <span
                      className={`font-semibold tabular-nums ${
                        resultadoComparacao.com_regras.ks_teste > resultadoComparacao.sem_regras.ks_teste
                          ? "text-emerald-400"
                          : "text-red-400"
                      }`}
                    >
                      {(resultadoComparacao.com_regras.ks_teste - resultadoComparacao.sem_regras.ks_teste).toFixed(3)}
                    </span>
                  </p>
                </div>
              )}

              {resultadoEsfera3 && (
                <div className="mt-6 rounded-xl border border-slate-700 bg-slate-900/70 p-5">
                  <h2 className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-400">Resultado</h2>
                  <div className="mb-4 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
                    <Metrica rotulo="KS dev" valor={resultadoEsfera3.ks_dev.toFixed(3)} />
                    <Metrica rotulo="KS teste" valor={resultadoEsfera3.ks_teste.toFixed(3)} />
                    <Metrica rotulo="AUC teste" valor={resultadoEsfera3.auc_teste.toFixed(3)} />
                    <Metrica rotulo="dev / teste" valor={`${resultadoEsfera3.n_dev} / ${resultadoEsfera3.n_teste}`} />
                    <Metrica
                      rotulo="taxa evento dev"
                      valor={`${(resultadoEsfera3.taxa_evento_dev * 100).toFixed(1)}%`}
                    />
                    <Metrica
                      rotulo="taxa evento teste"
                      valor={`${(resultadoEsfera3.taxa_evento_teste * 100).toFixed(1)}%`}
                    />
                  </div>

                  <div className="grid gap-4 lg:grid-cols-2">
                    <div>
                      <p className="mb-1.5 text-[11px] text-slate-500">coeficientes</p>
                      <div className="max-h-[36rem] overflow-y-auto rounded-lg border border-slate-700">
                        <table className="w-full text-sm">
                          <thead className="sticky top-0 bg-slate-800/90 text-slate-400">
                            <tr>
                              <th className="px-3 py-1.5 text-left font-medium">variável</th>
                              <th className="px-3 py-1.5 text-right font-medium">coeficiente</th>
                              <th className="px-3 py-1.5 text-right font-medium">erro padrão</th>
                              <th className="px-3 py-1.5 text-right font-medium">p-valor</th>
                            </tr>
                          </thead>
                          <tbody>
                            {Object.entries(resultadoEsfera3.coeficientes).map(([nome, coef], i) => {
                              const stats = resultadoEsfera3.estatisticas[nome];
                              return (
                                <tr key={nome} className={i % 2 === 0 ? "bg-slate-900/40" : "bg-slate-900/70"}>
                                  <td className="px-3 py-2 font-mono text-slate-300">{nome}</td>
                                  <td className="px-3 py-2 text-right tabular-nums text-slate-300">
                                    {coef.toFixed(4)}
                                  </td>
                                  <td className="px-3 py-2 text-right tabular-nums text-slate-500">
                                    {stats ? stats.erro_padrao.toFixed(4) : "—"}
                                  </td>
                                  <td
                                    className={`px-3 py-2 text-right tabular-nums ${
                                      stats && stats.p_valor < 0.05 ? "text-emerald-400" : "text-slate-500"
                                    }`}
                                  >
                                    {stats ? stats.p_valor.toFixed(4) : "—"}
                                  </td>
                                </tr>
                              );
                            })}
                          </tbody>
                        </table>
                      </div>
                    </div>

                    <div>
                      <p className="mb-1.5 text-[11px] text-slate-500">curva KS (teste)</p>
                      <div className="rounded-lg border border-slate-700 bg-slate-900/40 p-3">
                        <GraficoKS tabela={resultadoEsfera3.tabela_decis} />
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </>
        )}
      </main>
    </div>
  );
}
