"use client";

import { useState } from "react";
import {
  buscarValoresDistintos,
  prepararDataset,
  sugerirCorte,
  uploadDataset,
  type ColunaDetectada,
  type ConfigSplit,
  type RespostaUpload,
} from "../lib/api";

interface Props {
  aoPreparar: (nomeDataset: string) => void;
}

type ModoSplit = ConfigSplit["modo"];

const RotuloTipo: Record<ColunaDetectada["tipo"], string> = {
  numerico: "numérico",
  data: "data",
  categorico: "categórico",
};

export default function PainelUpload({ aoPreparar }: Props) {
  const [aberto, setAberto] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const [preparando, setPreparando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [upload, setUpload] = useState<RespostaUpload | null>(null);

  const [nomeDataset, setNomeDataset] = useState("");
  const [colunaResposta, setColunaResposta] = useState("");
  const [modo, setModo] = useState<ModoSplit>("aleatorio");

  // modo "amostra"
  const [colunaAmostra, setColunaAmostra] = useState("");
  const [valoresDisponiveis, setValoresDisponiveis] = useState<string[]>([]);
  const [valoresDev, setValoresDev] = useState<Set<string>>(new Set());
  const [valoresTeste, setValoresTeste] = useState<Set<string>>(new Set());

  // modo "oot"
  const [colunaData, setColunaData] = useState("");
  const [corte, setCorte] = useState("");
  const [proporcaoTesteOot, setProporcaoTesteOot] = useState(0.3);

  // modo "aleatorio"
  const [proporcaoTesteAleatorio, setProporcaoTesteAleatorio] = useState(0.3);
  const [semente, setSemente] = useState(42);

  async function aoEscolherArquivo(arquivo: File) {
    setEnviando(true);
    setErro(null);
    try {
      const resp = await uploadDataset(arquivo);
      setUpload(resp);
      setNomeDataset(arquivo.name.replace(/\.csv$/i, ""));
      const candidataResposta = resp.colunas.find(
        (c) => c.tipo === "numerico" && c.n_distintos === 2,
      );
      setColunaResposta(candidataResposta?.nome ?? "");
      const primeiraCategorica = resp.colunas.find((c) => c.tipo === "categorico");
      const primeiraData = resp.colunas.find((c) => c.tipo === "data");
      setColunaAmostra(primeiraCategorica?.nome ?? "");
      setColunaData(primeiraData?.nome ?? "");
      setModo(primeiraData ? "oot" : primeiraCategorica ? "amostra" : "aleatorio");
    } catch (e) {
      setErro(String(e));
    } finally {
      setEnviando(false);
    }
  }

  async function aoSelecionarColunaAmostra(coluna: string) {
    setColunaAmostra(coluna);
    setValoresDev(new Set());
    setValoresTeste(new Set());
    if (!upload || !coluna) return;
    try {
      const valores = await buscarValoresDistintos(upload.upload_id, coluna);
      setValoresDisponiveis(valores.map((v) => v.valor));
    } catch (e) {
      setErro(String(e));
    }
  }

  async function aoSugerirCorte() {
    if (!upload || !colunaData) return;
    const coluna = upload.colunas.find((c) => c.nome === colunaData);
    if (!coluna?.formato_data) return;
    try {
      const sugerido = await sugerirCorte(upload.upload_id, colunaData, coluna.formato_data, proporcaoTesteOot);
      setCorte(sugerido);
    } catch (e) {
      setErro(String(e));
    }
  }

  function alternarValor(conjunto: Set<string>, valor: string): Set<string> {
    const novo = new Set(conjunto);
    if (novo.has(valor)) novo.delete(valor);
    else novo.add(valor);
    return novo;
  }

  function construirSplit(): ConfigSplit | null {
    if (modo === "amostra") {
      if (valoresDev.size === 0 || valoresTeste.size === 0) return null;
      return {
        modo: "amostra",
        coluna: colunaAmostra,
        valores_dev: [...valoresDev],
        valores_teste: [...valoresTeste],
      };
    }
    if (modo === "oot") {
      const coluna = upload?.colunas.find((c) => c.nome === colunaData);
      if (!coluna?.formato_data || !corte) return null;
      return { modo: "oot", coluna: colunaData, formato: coluna.formato_data, corte };
    }
    return { modo: "aleatorio", proporcao_teste: proporcaoTesteAleatorio, semente };
  }

  async function aoPrepararDataset() {
    if (!upload || !colunaResposta || !nomeDataset) return;
    const split = construirSplit();
    if (!split) {
      setErro("Configuração de split incompleta.");
      return;
    }
    setPreparando(true);
    setErro(null);
    try {
      const resultado = await prepararDataset({
        upload_id: upload.upload_id,
        nome_dataset: nomeDataset,
        coluna_resposta: colunaResposta,
        split,
      });
      aoPreparar(resultado.nome_dataset);
      setAberto(false);
      setUpload(null);
    } catch (e) {
      setErro(String(e));
    } finally {
      setPreparando(false);
    }
  }

  if (!aberto) {
    return (
      <button
        onClick={() => setAberto(true)}
        className="w-full rounded-lg border border-dashed border-slate-700/50 px-3 py-2 text-xs font-medium text-slate-400 transition hover:border-emerald-700 hover:text-emerald-400"
      >
        + Novo dataset (upload CSV)
      </button>
    );
  }

  return (
    <div className="flex flex-col gap-3 rounded-lg border border-slate-700/50 bg-slate-900/40 p-3">
      <div className="flex items-center justify-between">
        <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-400">Novo dataset</h2>
        <button onClick={() => setAberto(false)} className="text-xs text-slate-500 hover:text-slate-300">
          fechar
        </button>
      </div>

      {!upload && (
        <label className="flex cursor-pointer flex-col items-center justify-center gap-1 rounded-lg border border-dashed border-slate-700/50 px-3 py-6 text-center text-xs text-slate-500 hover:border-emerald-700 hover:text-emerald-400">
          {enviando ? "Enviando…" : "Clique para escolher um arquivo .csv"}
          <input
            type="file"
            accept=".csv"
            className="hidden"
            disabled={enviando}
            onChange={(e) => {
              const arquivo = e.target.files?.[0];
              if (arquivo) void aoEscolherArquivo(arquivo);
            }}
          />
        </label>
      )}

      {upload && (
        <>
          <p className="text-xs text-slate-500">
            {upload.n_linhas} linhas · {upload.colunas.length} colunas detectadas
          </p>

          <div className="max-h-32 overflow-y-auto rounded-lg border border-slate-800/50">
            <table className="w-full text-left text-[11px]">
              <tbody>
                {upload.colunas.map((c) => (
                  <tr key={c.nome} className="border-b border-slate-800/60 last:border-0">
                    <td className="px-2 py-1 font-mono text-slate-300">{c.nome}</td>
                    <td className="px-2 py-1 text-slate-500">
                      {RotuloTipo[c.tipo]}
                      {c.formato_data ? ` (${c.formato_data})` : ""}
                    </td>
                    <td className="px-2 py-1 text-slate-600">{c.n_distintos} valores</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div>
            <label className="mb-1 block text-[11px] text-slate-500">Nome do dataset</label>
            <input
              value={nomeDataset}
              onChange={(e) => setNomeDataset(e.target.value)}
              className="w-full rounded-lg bg-slate-800/60 border border-slate-700/50 px-2 py-1.5 text-sm text-slate-100 focus:outline-none focus:ring-2 focus:ring-emerald-500"
            />
          </div>

          <div>
            <label className="mb-1 block text-[11px] text-slate-500">Coluna resposta (y)</label>
            <select
              value={colunaResposta}
              onChange={(e) => setColunaResposta(e.target.value)}
              className="w-full rounded-lg bg-slate-800/60 border border-slate-700/50 px-2 py-1.5 text-sm text-slate-100 focus:outline-none focus:ring-2 focus:ring-emerald-500"
            >
              <option value="">selecione…</option>
              {upload.colunas.map((c) => (
                <option key={c.nome} value={c.nome}>
                  {c.nome}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="mb-1 block text-[11px] text-slate-500">Divisão dev/teste</label>
            <div className="flex flex-col gap-1.5">
              <label className="flex items-center gap-2 text-xs text-slate-200 cursor-pointer">
                <input
                  type="radio"
                  name="modo-split"
                  checked={modo === "amostra"}
                  onChange={() => setModo("amostra")}
                />
                Coluna de amostra já existe na base
              </label>
              <label className="flex items-center gap-2 text-xs text-slate-200 cursor-pointer">
                <input
                  type="radio"
                  name="modo-split"
                  checked={modo === "oot"}
                  onChange={() => setModo("oot")}
                />
                Out-of-time (por data)
              </label>
              <label className="flex items-center gap-2 text-xs text-slate-200 cursor-pointer">
                <input
                  type="radio"
                  name="modo-split"
                  checked={modo === "aleatorio"}
                  onChange={() => setModo("aleatorio")}
                />
                Aleatório
              </label>
            </div>
          </div>

          {modo === "amostra" && (
            <div className="flex flex-col gap-2 rounded-lg border border-slate-800/50 p-2">
              <select
                value={colunaAmostra}
                onChange={(e) => void aoSelecionarColunaAmostra(e.target.value)}
                className="w-full rounded-lg bg-slate-800/60 border border-slate-700/50 px-2 py-1.5 text-xs text-slate-100"
              >
                <option value="">coluna de amostra…</option>
                {upload.colunas.map((c) => (
                  <option key={c.nome} value={c.nome}>
                    {c.nome}
                  </option>
                ))}
              </select>
              {valoresDisponiveis.length > 0 && (
                <div className="grid grid-cols-2 gap-2 text-[11px]">
                  <div>
                    <p className="mb-1 text-slate-500">dev</p>
                    <div className="flex flex-col gap-0.5 max-h-24 overflow-y-auto">
                      {valoresDisponiveis.map((v) => (
                        <label key={v} className="flex items-center gap-1.5 text-slate-300 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={valoresDev.has(v)}
                            onChange={() => setValoresDev((s) => alternarValor(s, v))}
                          />
                          {v}
                        </label>
                      ))}
                    </div>
                  </div>
                  <div>
                    <p className="mb-1 text-slate-500">teste</p>
                    <div className="flex flex-col gap-0.5 max-h-24 overflow-y-auto">
                      {valoresDisponiveis.map((v) => (
                        <label key={v} className="flex items-center gap-1.5 text-slate-300 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={valoresTeste.has(v)}
                            onChange={() => setValoresTeste((s) => alternarValor(s, v))}
                          />
                          {v}
                        </label>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {modo === "oot" && (
            <div className="flex flex-col gap-2 rounded-lg border border-slate-800/50 p-2">
              <select
                value={colunaData}
                onChange={(e) => {
                  setColunaData(e.target.value);
                  setCorte("");
                }}
                className="w-full rounded-lg bg-slate-800/60 border border-slate-700/50 px-2 py-1.5 text-xs text-slate-100"
              >
                <option value="">coluna de data…</option>
                {upload.colunas
                  .filter((c) => c.tipo === "data")
                  .map((c) => (
                    <option key={c.nome} value={c.nome}>
                      {c.nome} ({c.formato_data})
                    </option>
                  ))}
              </select>
              <div className="flex items-center gap-2">
                <input
                  type="number"
                  min={0.05}
                  max={0.95}
                  step={0.05}
                  value={proporcaoTesteOot}
                  onChange={(e) => setProporcaoTesteOot(Number(e.target.value))}
                  className="w-20 rounded-lg bg-slate-800/60 border border-slate-700/50 px-2 py-1 text-xs text-slate-100"
                />
                <button
                  onClick={() => void aoSugerirCorte()}
                  disabled={!colunaData}
                  className="rounded-lg border border-slate-700/50 px-2 py-1 text-[11px] text-slate-300 hover:border-emerald-700 hover:text-emerald-400 disabled:opacity-40"
                >
                  sugerir corte
                </button>
              </div>
              <input
                type="text"
                placeholder="corte (AAAA-MM-DD) — antes = dev, a partir daqui = teste"
                value={corte}
                onChange={(e) => setCorte(e.target.value)}
                className="w-full rounded-lg bg-slate-800/60 border border-slate-700/50 px-2 py-1.5 text-xs text-slate-100"
              />
            </div>
          )}

          {modo === "aleatorio" && (
            <div className="flex items-center gap-2 rounded-lg border border-slate-800/50 p-2">
              <div className="flex-1">
                <label className="mb-1 block text-[11px] text-slate-500">% teste</label>
                <input
                  type="number"
                  min={0.05}
                  max={0.95}
                  step={0.05}
                  value={proporcaoTesteAleatorio}
                  onChange={(e) => setProporcaoTesteAleatorio(Number(e.target.value))}
                  className="w-full rounded-lg bg-slate-800/60 border border-slate-700/50 px-2 py-1 text-xs text-slate-100"
                />
              </div>
              <div className="flex-1">
                <label className="mb-1 block text-[11px] text-slate-500">semente</label>
                <input
                  type="number"
                  value={semente}
                  onChange={(e) => setSemente(Number(e.target.value))}
                  className="w-full rounded-lg bg-slate-800/60 border border-slate-700/50 px-2 py-1 text-xs text-slate-100"
                />
              </div>
            </div>
          )}

          <button
            onClick={() => void aoPrepararDataset()}
            disabled={preparando || !colunaResposta || !nomeDataset}
            className="w-full rounded-lg bg-emerald-600 px-3 py-2 text-xs font-semibold text-white transition hover:bg-emerald-500 disabled:cursor-not-allowed disabled:bg-slate-700 disabled:text-slate-400"
          >
            {preparando ? "Preparando…" : "Preparar dataset"}
          </button>
        </>
      )}

      {erro && <p className="text-xs text-red-400">{erro}</p>}
    </div>
  );
}
